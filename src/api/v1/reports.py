"""Report API endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.integrations.base import EmailProvider
from src.models import User
from src.models.enums import IntegrationType
from src.services import email_template_service, event_service, integration_service
from src.services.report_generator import create_report_generator

router = APIRouter()


class SendReportRequest(BaseModel):
    """Schema for sending expense report via email."""

    recipient_email: Optional[str] = Field(
        None,
        description="Email address to send report to. If not provided, uses company expense recipient.",
    )
    template_id: Optional[str] = Field(
        None,
        description="Email template ID to use. If not provided, uses default template.",
    )


class SendReportResponse(BaseModel):
    """Schema for send report response."""

    success: bool
    message: str


@router.get("/{event_id}/expense-report/preview")
async def preview_expense_report(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get a preview of the expense report without generating files."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    generator = await create_report_generator(db, event)
    try:
        return generator.get_preview(event)
    finally:
        if generator.paperless:
            await generator.paperless.close()


@router.post("/{event_id}/expense-report/generate")
async def generate_expense_report(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Generate and download expense report as ZIP file."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    generator = await create_report_generator(db, event)
    try:
        zip_bytes = await generator.generate(event)
        filename = generator.get_filename(event)

        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    finally:
        if generator.paperless:
            await generator.paperless.close()


@router.post("/{event_id}/expense-report/send", response_model=SendReportResponse)
async def send_expense_report(
    event_id: str,
    data: SendReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SendReportResponse:
    """Generate and send expense report via email."""
    # Get the event
    event = event_service.get_event_for_user(
        db, event_id, current_user.id, include_company=True
    )
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    # Determine recipient email
    recipient_email = data.recipient_email
    if not recipient_email and event.company:
        recipient_email = event.company.expense_recipient_email

    if not recipient_email:
        return SendReportResponse(
            success=False,
            message="No recipient email provided and company has no expense recipient configured",
        )

    # Get active SMTP integration
    smtp_configs = integration_service.get_integration_configs(
        db, IntegrationType.SMTP
    )
    active_smtp = next((c for c in smtp_configs if c.is_active), None)
    if not active_smtp:
        return SendReportResponse(
            success=False,
            message="No active SMTP integration configured",
        )

    # Create email provider
    provider = integration_service.create_provider_instance(active_smtp)
    if not provider or not isinstance(provider, EmailProvider):
        return SendReportResponse(
            success=False,
            message="Failed to create email provider",
        )

    try:
        # Get email template
        if data.template_id:
            template = email_template_service.get_template(db, data.template_id)
            if not template:
                return SendReportResponse(
                    success=False,
                    message="Email template not found",
                )
        else:
            # Use default template for the company
            company_id = event.company.id if event.company else None
            template = email_template_service.get_default_template(
                db, company_id, "expense_report"
            )
            if not template:
                return SendReportResponse(
                    success=False,
                    message="No default email template found. Please configure a template.",
                )

        # Generate the report
        generator = await create_report_generator(db, event)
        try:
            zip_bytes = await generator.generate(event)
            filename = generator.get_filename(event)
        finally:
            if generator.paperless:
                await generator.paperless.close()

        # Build template context and render
        context = email_template_service.build_expense_report_context(
            event=event,
            company=event.company,
            expenses=event.expenses,
            user=current_user,
        )
        subject, body_html, body_text = email_template_service.render_template(
            template, context
        )

        success = await provider.send_email(
            to=[recipient_email],
            subject=subject,
            body=body_text,
            body_html=body_html,
            attachments=[(filename, zip_bytes, "application/zip")],
        )

        if success:
            return SendReportResponse(
                success=True,
                message=f"Expense report sent to {recipient_email}",
            )
        return SendReportResponse(
            success=False,
            message="Failed to send email",
        )
    except Exception as e:
        return SendReportResponse(
            success=False,
            message=f"Error sending report: {str(e)}",
        )
    finally:
        await provider.close()
