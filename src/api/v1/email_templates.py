# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Email template API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import (
    ensure_permission,
    get_current_user,
    require_permission,
)
from src.database import get_db
from src.models import User
from src.schemas.email_template import (
    DefaultTemplateContent,
    EmailTemplateCreate,
    EmailTemplateResponse,
    EmailTemplateUpdate,
    TemplatePreviewRequest,
    TemplatePreviewResponse,
    TemplateReason,
)
from src.services import (
    company_service,
    email_template_service,
    event_service,
    rbac_service,
    settings_service,
)
from src.services.report_generator import select_report_expenses

router = APIRouter()

# Company templates are governed by the company codes of their company,
# global templates (company_id None) by the system settings codes.
view_templates = require_permission("company.view", company_id_param="company_id")
read_global_templates = require_permission("system.settings.read")


def _template_code(company_id: uuid.UUID | None, *, write: bool) -> str:
    """Pick the permission code that governs templates of this scope.

    Args:
        company_id: The template's company, or None for a global template.
        write: True for create, update and delete.

    Returns:
        The permission code to check for the scope and access.
    """
    if company_id is None:
        return "system.settings.write" if write else "system.settings.read"
    return "company.manage" if write else "company.view"


@router.get("", response_model=list[EmailTemplateResponse])
def list_templates(
    reason: str | None = None,
    company_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(view_templates),
) -> list[EmailTemplateResponse]:
    """List the email templates the user may view.

    Optional filters:
    - reason: Filter by template reason (e.g., "expense_report")
    - company_id: Filter to show templates for a specific company (includes globals)

    Without a company filter, company templates are limited to the companies
    the user may view.
    """
    templates = email_template_service.get_templates(
        db, reason=reason, company_id=company_id
    )
    if company_id is None:
        allowed = rbac_service.companies_with_permission(
            db, current_user, "company.view"
        )
        if allowed is not None:
            templates = [
                t for t in templates if t.company_id is None or t.company_id in allowed
            ]
    return [
        EmailTemplateResponse(**email_template_service.template_to_response_dict(t))
        for t in templates
    ]


@router.get("/global", response_model=list[EmailTemplateResponse])
def list_global_templates(
    reason: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(read_global_templates),
) -> list[EmailTemplateResponse]:
    """List only global templates (not company-specific)."""
    templates = email_template_service.get_global_templates(db, reason=reason)
    return [
        EmailTemplateResponse(**email_template_service.template_to_response_dict(t))
        for t in templates
    ]


@router.get("/reasons", response_model=list[TemplateReason])
def list_reasons(
    current_user: User = Depends(get_current_user),
) -> list[TemplateReason]:
    """List all available template reasons with their variables."""
    return email_template_service.get_reasons()


@router.get("/default-content/{reason}", response_model=DefaultTemplateContent)
def get_default_content(
    reason: str,
    current_user: User = Depends(get_current_user),
) -> DefaultTemplateContent:
    """Get the default template content for a reason (for prefilling new templates)."""
    default_content = email_template_service.get_default_template_content(reason)
    if not default_content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No default content for reason: {reason}",
        )
    return DefaultTemplateContent(**default_content)


@router.post("/preview", response_model=TemplatePreviewResponse)
def preview_template(
    data: TemplatePreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplatePreviewResponse:
    """Preview a template with sample or real event data.

    If event_id is provided, uses real event data. Otherwise uses sample data.
    """
    date_format = settings_service.get_locale_settings(db)["date_format"]
    if data.event_id:
        # Use real event data
        event = event_service.get_event_for_user(
            db, data.event_id, current_user.id, include_company=True
        )
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found",
            )
        ensure_permission(db, current_user, "event.read", event.company_id)

        # Same selection as the report itself, so the preview totals match
        expenses = select_report_expenses(db, event, data.expense_ids)

        context = email_template_service.build_expense_report_context(
            event=event,
            company=event.company,
            expenses=expenses,
            user=current_user,
            base_currency=settings_service.get_base_currency(db),
            date_format=date_format,
        )
    else:
        # Use sample data
        context = email_template_service.get_sample_context(data.reason, date_format)

    subject, body_html, body_text = email_template_service.render_strings(
        data.subject, data.body_html, data.body_text, context
    )

    return TemplatePreviewResponse(
        subject=subject,
        body_html=body_html,
        body_text=body_text,
    )


@router.post(
    "", response_model=EmailTemplateResponse, status_code=status.HTTP_201_CREATED
)
def create_template(
    data: EmailTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailTemplateResponse:
    """Create a new email template."""
    ensure_permission(
        db, current_user, _template_code(data.company_id, write=True), data.company_id
    )
    # Validate company exists if company_id provided
    if data.company_id:
        company = company_service.get_company(db, data.company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found",
            )

    # Validate reason
    if not email_template_service.get_reason_variables(data.reason):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid template reason: {data.reason}",
        )

    template = email_template_service.create_template(db, data)
    return EmailTemplateResponse(
        **email_template_service.template_to_response_dict(template)
    )


@router.get("/{template_id}", response_model=EmailTemplateResponse)
def get_template(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailTemplateResponse:
    """Get a template by ID."""
    template = email_template_service.get_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email template not found",
        )
    ensure_permission(
        db,
        current_user,
        _template_code(template.company_id, write=False),
        template.company_id,
    )
    return EmailTemplateResponse(
        **email_template_service.template_to_response_dict(template)
    )


@router.put("/{template_id}", response_model=EmailTemplateResponse)
def update_template(
    template_id: uuid.UUID,
    data: EmailTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailTemplateResponse:
    """Update an email template."""
    template = email_template_service.get_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email template not found",
        )
    ensure_permission(
        db,
        current_user,
        _template_code(template.company_id, write=True),
        template.company_id,
    )

    # Validate reason if being updated
    if data.reason and not email_template_service.get_reason_variables(data.reason):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid template reason: {data.reason}",
        )

    template = email_template_service.update_template(db, template, data)
    return EmailTemplateResponse(
        **email_template_service.template_to_response_dict(template)
    )


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete an email template."""
    template = email_template_service.get_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email template not found",
        )
    ensure_permission(
        db,
        current_user,
        _template_code(template.company_id, write=True),
        template.company_id,
    )

    # Prevent deleting the last global template
    if email_template_service.is_last_global_template(db, template):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the last global template. One must exist.",
        )

    email_template_service.delete_template(db, template)
