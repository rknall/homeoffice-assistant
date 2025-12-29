# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Report API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.integrations.base import EmailProvider
from src.models import User
from src.models.enums import IntegrationType
from src.services import (
    company_contact_service,
    email_template_service,
    event_service,
    integration_service,
    todo_service,
)
from src.services.report_generator import create_report_generator

router = APIRouter()


class SendReportRequest(BaseModel):
    """Schema for sending expense report via email."""

    recipient_emails: list[EmailStr] | None = Field(
        None,
        description="Email addresses to send report to. Uses contacts if not provided.",
    )
    template_id: uuid.UUID | None = Field(
        None,
        description="Email template ID to use. If not provided, uses default template.",
    )
    auto_select_contacts: bool = Field(
        True,
        description="Automatically select contacts based on template contact types.",
    )


class SendReportResponse(BaseModel):
    """Schema for send report response."""

    success: bool
    message: str
    recipients: list[str] = []


@router.get("/{event_id}/expense-report/preview")
async def preview_expense_report(
    event_id: uuid.UUID,
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
    event_id: uuid.UUID,
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

        # Auto-complete report-related todos
        todo_service.auto_complete_report_todos(db, event_id)

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
    event_id: uuid.UUID,
    data: SendReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SendReportResponse:
    """Generate and send expense report via email.

    Recipient selection:
    1. If recipient_emails is provided, use those
    2. If auto_select_contacts is True and template has contact_types, use matches
    3. Fall back to company's main contact if available
    """
    # Get the event
    event = event_service.get_event_for_user(
        db, event_id, current_user.id, include_company=True
    )
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    if not event.company:
        return SendReportResponse(
            success=False,
            message="Event has no associated company",
            recipients=[],
        )

    # Get active SMTP integration first
    smtp_configs = integration_service.get_integration_configs(db, IntegrationType.SMTP)
    active_smtp = next((c for c in smtp_configs if c.is_active), None)
    if not active_smtp:
        return SendReportResponse(
            success=False,
            message="No active SMTP integration configured",
            recipients=[],
        )

    # Create email provider
    provider = integration_service.create_provider_instance(active_smtp)
    if not provider or not isinstance(provider, EmailProvider):
        return SendReportResponse(
            success=False,
            message="Failed to create email provider",
            recipients=[],
        )

    try:
        # Get email template
        if data.template_id:
            template = email_template_service.get_template(db, data.template_id)
            if not template:
                return SendReportResponse(
                    success=False,
                    message="Email template not found",
                    recipients=[],
                )
        else:
            # Use default template for the company
            company_id = event.company.id
            template = email_template_service.get_default_template(
                db, company_id, "expense_report"
            )
            if not template:
                return SendReportResponse(
                    success=False,
                    message="No default email template found. Configure one first.",
                    recipients=[],
                )

        # Determine recipient emails
        recipient_emails: list[str] = []

        if data.recipient_emails:
            # Use explicitly provided emails
            recipient_emails = list(data.recipient_emails)
        elif data.auto_select_contacts:
            # Auto-select contacts based on template contact types
            template_types = email_template_service.get_template_contact_types(template)

            if template_types:
                # Get contacts matching template types
                matching_contacts = company_contact_service.get_contacts_by_type(
                    db, event.company.id, template_types
                )
                recipient_emails = [c.email for c in matching_contacts]

            if not recipient_emails:
                # Fall back to main contact
                main_contact = company_contact_service.get_main_contact(
                    db, event.company.id
                )
                if main_contact:
                    recipient_emails = [main_contact.email]

        if not recipient_emails:
            return SendReportResponse(
                success=False,
                message="No recipients found. Add contacts or provide emails.",
                recipients=[],
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

        # Send email to all recipients at once (single email with multiple To addresses)
        success = await provider.send_email(
            to=recipient_emails,
            subject=subject,
            body=body_text,
            body_html=body_html,
            attachments=[(filename, zip_bytes, "application/zip")],
        )

        if success:
            # Auto-complete report-related todos
            todo_service.auto_complete_report_todos(db, event_id)

            recipients_str = ", ".join(recipient_emails)
            return SendReportResponse(
                success=True,
                message=f"Expense report sent to {recipients_str}",
                recipients=recipient_emails,
            )
        return SendReportResponse(
            success=False,
            message="Failed to send email",
            recipients=[],
        )
    except Exception as e:
        return SendReportResponse(
            success=False,
            message=f"Error sending report: {e!s}",
            recipients=[],
        )
    finally:
        await provider.close()
