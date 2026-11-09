# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Email template service for CRUD and rendering operations."""

import html
import json
import re
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from src.models import Company, EmailTemplate, Event, Expense, User
from src.models.enums import ContactType
from src.schemas.email_template import (
    EmailTemplateCreate,
    EmailTemplateUpdate,
    TemplateReason,
)
from src.services.email_template_constants import (
    DEFAULT_EXPENSE_REPORT_TEMPLATE,
    SAMPLE_DATES,
    TEMPLATE_REASONS,
)
from src.services.settings_service import DEFAULT_DATE_FORMAT


def format_date(value: date, date_format: str | None = None) -> str:
    """Format a date with a locale date format such as ``DD.MM.YYYY``.

    Args:
        value: Date to format.
        date_format: Locale setting value; the locale default when None.
    """
    pattern = date_format or DEFAULT_DATE_FORMAT
    for token, directive in (("YYYY", "%Y"), ("MM", "%m"), ("DD", "%d")):
        pattern = pattern.replace(token, directive)
    return value.strftime(pattern)


def get_templates(
    db: Session,
    reason: str | None = None,
    company_id: uuid.UUID | None = None,
) -> list[EmailTemplate]:
    """Get all templates, optionally filtered by reason and/or company."""
    query = db.query(EmailTemplate)

    if reason:
        query = query.filter(EmailTemplate.reason == reason)

    if company_id:
        # Get both global templates and company-specific templates
        query = query.filter(
            or_(
                EmailTemplate.company_id.is_(None),
                EmailTemplate.company_id == company_id,
            )
        )

    return query.order_by(EmailTemplate.name).all()


def get_global_templates(db: Session, reason: str | None = None) -> list[EmailTemplate]:
    """Get only global templates (company_id is NULL)."""
    query = db.query(EmailTemplate).filter(EmailTemplate.company_id.is_(None))

    if reason:
        query = query.filter(EmailTemplate.reason == reason)

    return query.order_by(EmailTemplate.name).all()


def get_templates_for_company(
    db: Session,
    company_id: uuid.UUID,
    reason: str,
) -> list[EmailTemplate]:
    """Get templates applicable to a company (company-specific + global)."""
    return (
        db.query(EmailTemplate)
        .filter(
            and_(
                EmailTemplate.reason == reason,
                or_(
                    EmailTemplate.company_id.is_(None),
                    EmailTemplate.company_id == company_id,
                ),
            )
        )
        .order_by(
            EmailTemplate.company_id.desc(), EmailTemplate.name
        )  # Company-specific first
        .all()
    )


def get_template(db: Session, template_id: uuid.UUID) -> EmailTemplate | None:
    """Get a template by ID."""
    return db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()


def get_default_template(
    db: Session,
    company_id: uuid.UUID | None,
    reason: str,
) -> EmailTemplate | None:
    """Get the default template for a reason.

    Priority:
    1. Company-specific default (if company_id provided)
    2. Global default
    """
    if company_id:
        # Try company-specific default first
        company_default = (
            db.query(EmailTemplate)
            .filter(
                and_(
                    EmailTemplate.reason == reason,
                    EmailTemplate.company_id == company_id,
                    EmailTemplate.is_default.is_(True),
                )
            )
            .first()
        )
        if company_default:
            return company_default

    # Fall back to global default
    return (
        db.query(EmailTemplate)
        .filter(
            and_(
                EmailTemplate.reason == reason,
                EmailTemplate.company_id.is_(None),
                EmailTemplate.is_default.is_(True),
            )
        )
        .first()
    )


def create_template(db: Session, data: EmailTemplateCreate) -> EmailTemplate:
    """Create a new email template."""
    # If this is set as default, unset other defaults for the same reason/scope
    if data.is_default:
        _unset_other_defaults(db, data.reason, data.company_id)

    template = EmailTemplate(
        name=data.name,
        reason=data.reason,
        company_id=data.company_id,
        subject=data.subject,
        body_html=data.body_html,
        body_text=data.body_text,
        is_default=data.is_default,
        contact_types=json.dumps([ct.value for ct in data.contact_types]),
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def update_template(
    db: Session,
    template: EmailTemplate,
    data: EmailTemplateUpdate,
) -> EmailTemplate:
    """Update an existing email template."""
    # If setting as default, unset other defaults
    if data.is_default is True:
        _unset_other_defaults(
            db, template.reason, template.company_id, exclude_id=template.id
        )

    if data.name is not None:
        template.name = data.name
    if data.reason is not None:
        template.reason = data.reason
    if data.subject is not None:
        template.subject = data.subject
    if data.body_html is not None:
        template.body_html = data.body_html
    if data.body_text is not None:
        template.body_text = data.body_text
    if data.is_default is not None:
        template.is_default = data.is_default
    if data.contact_types is not None:
        template.contact_types = json.dumps([ct.value for ct in data.contact_types])

    db.commit()
    db.refresh(template)
    return template


def delete_template(db: Session, template: EmailTemplate) -> None:
    """Delete an email template."""
    db.delete(template)
    db.commit()


def count_global_templates(db: Session) -> int:
    """Count the number of global templates."""
    return db.query(EmailTemplate).filter(EmailTemplate.company_id.is_(None)).count()


def is_last_global_template(db: Session, template: EmailTemplate) -> bool:
    """Check if this is the last global template."""
    if template.company_id is not None:
        return False  # Company-specific templates can always be deleted
    return count_global_templates(db) <= 1


def _unset_other_defaults(
    db: Session,
    reason: str,
    company_id: uuid.UUID | None,
    exclude_id: uuid.UUID | None = None,
) -> None:
    """Unset is_default for other templates in the same scope."""
    query = db.query(EmailTemplate).filter(
        and_(
            EmailTemplate.reason == reason,
            EmailTemplate.is_default.is_(True),
        )
    )

    if company_id:
        query = query.filter(EmailTemplate.company_id == company_id)
    else:
        query = query.filter(EmailTemplate.company_id.is_(None))

    if exclude_id:
        query = query.filter(EmailTemplate.id != exclude_id)

    for template in query.all():
        template.is_default = False


def get_reasons() -> list[TemplateReason]:
    """Get all available template reasons with their variables."""
    return list(TEMPLATE_REASONS.values())


def get_reason_variables(reason: str) -> TemplateReason | None:
    """Get variables for a specific reason."""
    return TEMPLATE_REASONS.get(reason)


def get_default_template_content(reason: str) -> dict | None:
    """Get default template content for prefilling new templates."""
    if reason == "expense_report":
        return DEFAULT_EXPENSE_REPORT_TEMPLATE
    return None


def render_template(
    template: EmailTemplate,
    context: dict,
) -> tuple[str, str, str]:
    """Render a template with variable substitution.

    Returns (subject, body_html, body_text).
    """
    return render_strings(
        template.subject, template.body_html, template.body_text, context
    )


def render_strings(
    subject: str,
    body_html: str,
    body_text: str,
    context: dict,
) -> tuple[str, str, str]:
    """Render template parts given as plain strings.

    Returns (subject, body_html, body_text).
    """
    return (
        _substitute_variables(subject, context),
        _substitute_variables(body_html, context, escape=True),
        _substitute_variables(body_text, context),
    )


def _substitute_variables(text: str, context: dict, escape: bool = False) -> str:
    """Substitute {{variable}} placeholders with context values.

    Args:
        text: Template text containing placeholders.
        context: Nested dictionary of values.
        escape: HTML-escape every substituted value (for HTML bodies).
    """
    # Match {{variable.path}} patterns
    pattern = r"\{\{([a-z_]+(?:\.[a-z_]+)*)\}\}"

    def replacer(match: re.Match) -> str:
        path = match.group(1)
        parts = path.split(".")
        value = context
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return match.group(0)  # Keep original if not found
        result = str(value) if value is not None else ""
        return html.escape(result) if escape else result

    return re.sub(pattern, replacer, text)


def build_expense_report_context(
    event: Event,
    company: Company,
    expenses: list[Expense],
    user: User,
    base_currency: str = "EUR",
    date_format: str | None = None,
) -> dict:
    """Build context dictionary for expense_report templates.

    Totals use converted amounts (daily-rate conversion to the system base
    currency), matching the attached Excel report.
    """
    total = sum(e.effective_amount for e in expenses) or Decimal("0")
    currency = base_currency

    # Format dates
    start_date = format_date(event.start_date, date_format) if event.start_date else ""
    end_date = format_date(event.end_date, date_format) if event.end_date else ""

    # Get main contact name if available
    main_contact = next((c for c in company.contacts if c.is_main_contact), None)
    recipient_name = main_contact.name if main_contact else company.name

    return {
        "event": {
            "name": event.name,
            "start_date": start_date,
            "end_date": end_date,
            "description": event.description or "",
        },
        "company": {
            "name": company.name,
            "recipient_name": recipient_name,
        },
        "expense": {
            "total_amount": f"{total:.2f} {currency}",
            "count": str(len(expenses)),
            "currency": currency,
        },
        "sender": {
            "name": user.username,
            "email": user.email or "",
        },
    }


def get_sample_context(reason: str, date_format: str | None = None) -> dict:
    """Generate sample context for preview from the variables' examples.

    Date variables are formatted with ``date_format`` (the locale setting).
    """
    reason_info = TEMPLATE_REASONS.get(reason)
    if reason_info is None:
        return {}
    context: dict = {}
    for info in reason_info.variables:
        *parents, key = info.variable.strip("{}").split(".")
        node = context
        for part in parents:
            node = node.setdefault(part, {})
        sample_date = SAMPLE_DATES.get(info.variable)
        node[key] = (
            format_date(sample_date, date_format) if sample_date else info.example
        )
    return context


def ensure_default_template_exists(db: Session) -> EmailTemplate:
    """Ensure a default expense_report template exists. Create if missing.

    This should be called during setup to ensure the system always has
    at least one template.
    """
    existing = get_default_template(db, None, "expense_report")
    if existing:
        return existing

    # Create the default template
    template = EmailTemplate(
        name=DEFAULT_EXPENSE_REPORT_TEMPLATE["name"],
        reason=DEFAULT_EXPENSE_REPORT_TEMPLATE["reason"],
        company_id=None,  # Global template
        subject=DEFAULT_EXPENSE_REPORT_TEMPLATE["subject"],
        body_html=DEFAULT_EXPENSE_REPORT_TEMPLATE["body_html"],
        body_text=DEFAULT_EXPENSE_REPORT_TEMPLATE["body_text"],
        is_default=True,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def get_template_contact_types(template: EmailTemplate) -> list[ContactType]:
    """Get the contact types for a template as a list of ContactType enums."""
    contact_types_json = template.contact_types or "[]"
    contact_type_values = json.loads(contact_types_json)
    return [ContactType(ct) for ct in contact_type_values]


def template_to_response_dict(template: EmailTemplate) -> dict:
    """Convert an EmailTemplate to a response dictionary with parsed contact_types."""
    contact_types = get_template_contact_types(template)
    return {
        "id": template.id,
        "name": template.name,
        "reason": template.reason,
        "company_id": template.company_id,
        "subject": template.subject,
        "body_html": template.body_html,
        "body_text": template.body_text,
        "is_default": template.is_default,
        "contact_types": contact_types,
        "created_at": template.created_at,
        "updated_at": template.updated_at,
    }
