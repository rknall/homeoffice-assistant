# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Email template API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.models import User
from src.schemas.company_contact import TemplateContactValidation
from src.schemas.email_template import (
    EmailTemplateCreate,
    EmailTemplateResponse,
    EmailTemplateUpdate,
    TemplatePreviewRequest,
    TemplatePreviewResponse,
    TemplateReason,
)
from src.services import company_service, email_template_service, event_service
from src.services.company_contact_service import get_contacts

router = APIRouter()


@router.get("", response_model=list[EmailTemplateResponse])
def list_templates(
    reason: str | None = None,
    company_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EmailTemplateResponse]:
    """List all email templates.

    Optional filters:
    - reason: Filter by template reason (e.g., "expense_report")
    - company_id: Filter to show templates for a specific company (includes globals)
    """
    templates = email_template_service.get_templates(
        db, reason=reason, company_id=company_id
    )
    return [
        EmailTemplateResponse(**email_template_service.template_to_response_dict(t))
        for t in templates
    ]


@router.get("/global", response_model=list[EmailTemplateResponse])
def list_global_templates(
    reason: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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


@router.get("/variables/{reason}", response_model=TemplateReason)
def get_reason_variables(
    reason: str,
    current_user: User = Depends(get_current_user),
) -> TemplateReason:
    """Get available variables for a specific template reason."""
    reason_info = email_template_service.get_reason_variables(reason)
    if not reason_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown template reason: {reason}",
        )
    return reason_info


@router.get("/default-content/{reason}")
def get_default_content(
    reason: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get the default template content for a reason (for prefilling new templates)."""
    default_content = email_template_service.get_default_template_content(reason)
    if not default_content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No default content for reason: {reason}",
        )
    return default_content


@router.post("/preview", response_model=TemplatePreviewResponse)
def preview_template(
    data: TemplatePreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplatePreviewResponse:
    """Preview a template with sample or real event data.

    If event_id is provided, uses real event data. Otherwise uses sample data.
    """
    if data.event_id:
        # Use real event data
        event = event_service.get_event(db, data.event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found",
            )

        company = event.company
        expenses = event.expenses

        context = email_template_service.build_expense_report_context(
            event=event,
            company=company,
            expenses=expenses,
            user=current_user,
        )
    else:
        # Use sample data
        context = email_template_service.get_sample_context(data.reason)

    # Create a temporary template-like object for rendering
    class TempTemplate:
        def __init__(self, subject: str, body_html: str, body_text: str) -> None:
            self.subject = subject
            self.body_html = body_html
            self.body_text = body_text

    temp = TempTemplate(data.subject, data.body_html, data.body_text)
    subject, body_html, body_text = email_template_service.render_template(
        temp, context
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

    # Prevent deleting the last global template
    if email_template_service.is_last_global_template(db, template):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the last global template. One must exist.",
        )

    email_template_service.delete_template(db, template)


@router.get(
    "/{template_id}/validate-contacts/{company_id}",
    response_model=TemplateContactValidation,
)
def validate_template_contacts(
    template_id: uuid.UUID,
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplateContactValidation:
    """Validate that a company has the required contact types for a template.

    Returns validation status with:
    - is_valid: True if all required contact types have at least one matching contact
    - missing_types: List of contact types that have no matching contacts
    - available_contacts: List of contacts that match the template's contact types
    - message: Human-readable validation message
    """
    template = email_template_service.get_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email template not found",
        )

    company = company_service.get_company(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    # Check if company has any contacts
    contacts = get_contacts(db, company_id)
    if not contacts:
        template_types = email_template_service.get_template_contact_types(template)
        if template_types:
            return TemplateContactValidation(
                is_valid=False,
                missing_types=template_types,
                available_contacts=[],
                message="No contacts configured. Please add contacts first.",
            )
        return TemplateContactValidation(
            is_valid=True,
            missing_types=[],
            available_contacts=[],
            message="No contact types required for this template.",
        )

    is_valid, missing_types, available_contacts = (
        email_template_service.validate_template_contacts(db, template, company_id)
    )

    if is_valid:
        contact_count = len(available_contacts)
        message = f"All required contact types have matches ({contact_count} found)."
    else:
        missing_names = [ct.value for ct in missing_types]
        message = f"Missing contacts for: {', '.join(missing_names)}."

    return TemplateContactValidation(
        is_valid=is_valid,
        missing_types=missing_types,
        available_contacts=available_contacts,
        message=message,
    )
