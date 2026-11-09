# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Expense report send flow."""

import logging

from sqlalchemy.orm import Session

from src.integrations.base import EmailProvider
from src.integrations.failure import failure_category
from src.models import EmailTemplate, Event, User
from src.models.enums import IntegrationType
from src.schemas.report import SendReportRequest, SendReportResponse
from src.services import (
    company_contact_service,
    email_template_service,
    integration_service,
    settings_service,
    submission_service,
    todo_service,
)
from src.services.report_generator import create_report_generator
from src.utils.time import utc_now

logger = logging.getLogger(__name__)


def _failure(message: str) -> SendReportResponse:
    """Build a failed send response."""
    return SendReportResponse(success=False, message=message, recipients=[])


def _resolve_recipients(
    db: Session, event: Event, template: EmailTemplate, data: SendReportRequest
) -> list[str]:
    """Pick recipient emails: explicit, template contact types, main contact."""
    if data.recipient_emails:
        return [str(email) for email in data.recipient_emails]
    if not data.auto_select_contacts or event.company is None:
        return []

    recipients: list[str] = []
    template_types = email_template_service.get_template_contact_types(template)
    if template_types:
        contacts = company_contact_service.get_contacts_by_type(
            db, event.company.id, template_types
        )
        recipients = [c.email for c in contacts]
    if not recipients:
        main_contact = company_contact_service.get_main_contact(db, event.company.id)
        if main_contact:
            recipients = [main_contact.email]
    return recipients


async def _send_with_provider(
    db: Session,
    event: Event,
    user: User,
    data: SendReportRequest,
    provider: EmailProvider,
) -> SendReportResponse:
    """Build the report and send it through an open email provider."""
    try:
        if data.template_id:
            template = email_template_service.get_template(db, data.template_id)
            if not template:
                return _failure("Email template not found")
        else:
            template = email_template_service.get_default_template(
                db, event.company.id, "expense_report"
            )
            if not template:
                return _failure("No default email template found. Configure one first.")

        recipient_emails = _resolve_recipients(db, event, template, data)
        if not recipient_emails:
            return _failure("No recipients found. Add contacts or provide emails.")

        generator = await create_report_generator(db, event)
        try:
            zip_bytes, included_expenses = await generator.generate(
                event, data.expense_ids
            )
            filename = generator.get_filename(event)
        finally:
            if generator.paperless:
                await generator.paperless.close()

        if not included_expenses:
            return _failure("No open (non-reimbursed) expenses to report")

        # Context from the expenses actually included in the report (respects
        # expense_ids selection and is_private exclusion)
        context = email_template_service.build_expense_report_context(
            event=event,
            company=event.company,
            expenses=included_expenses,
            user=user,
            base_currency=settings_service.get_base_currency(db),
            date_format=settings_service.get_locale_settings(db)["date_format"],
        )
        subject, body_html, body_text = email_template_service.render_template(
            template, context
        )

        # Single email with multiple To addresses
        sent = await provider.send_email(
            to=recipient_emails,
            subject=subject,
            body=body_text,
            body_html=body_html,
            attachments=[(filename, zip_bytes, "application/zip")],
        )
        if not sent:
            return _failure("Failed to send email")

        if data.mark_as_submitted:
            submission_service.create_submission(
                db,
                event.id,
                [e.id for e in included_expenses],
                "email",
                data.notes,
                mark_as_submitted=True,
            )
        event.report_sent_at = utc_now()
        db.commit()
        todo_service.auto_complete_report_todos(db, event.id)

        return SendReportResponse(
            success=True,
            message=f"Expense report sent to {', '.join(recipient_emails)}",
            recipients=recipient_emails,
        )
    except Exception as e:
        db.rollback()
        logger.exception("Error sending report for event %s", event.id)
        return _failure(f"Error sending report: {failure_category(e)}")


async def send_report(
    db: Session,
    event: Event,
    user: User,
    data: SendReportRequest,
) -> SendReportResponse:
    """Generate the expense report and send it by email.

    The submission record and the SUBMITTED status are written only after the
    email was sent, so a failed send leaves the expenses untouched.

    Args:
        db: Database session.
        event: The event with its company loaded.
        user: The user sending the report.
        data: The send request.

    Returns:
        The send result; failures are reported in the response, not raised.
    """
    if not event.company:
        return _failure("Event has no associated company")

    try:
        async with integration_service.open_active_provider(
            db, IntegrationType.SMTP
        ) as provider:
            return await _send_with_provider(db, event, user, data, provider)
    except integration_service.ProviderError as e:
        return _failure(e.detail)
