# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Company contact API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.models import User
from src.models.enums import ContactType
from src.schemas.company_contact import (
    CompanyContactCreate,
    CompanyContactResponse,
    CompanyContactUpdate,
)
from src.services import company_contact_service, company_service

router = APIRouter()


@router.get(
    "/{company_id}/contacts",
    response_model=list[CompanyContactResponse],
)
def list_company_contacts(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CompanyContactResponse]:
    """List all contacts for a company."""
    company = company_service.get_company(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    contacts = company_contact_service.get_contacts(db, company_id)
    return [company_contact_service.contact_to_response(c) for c in contacts]


@router.get(
    "/{company_id}/contacts/{contact_id}",
    response_model=CompanyContactResponse,
)
def get_company_contact(
    company_id: uuid.UUID,
    contact_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyContactResponse:
    """Get a specific contact."""
    company = company_service.get_company(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    contact = company_contact_service.get_contact_by_company(db, company_id, contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    return company_contact_service.contact_to_response(contact)


@router.post(
    "/{company_id}/contacts",
    response_model=CompanyContactResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_company_contact(
    company_id: uuid.UUID,
    data: CompanyContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyContactResponse:
    """Create a new contact for a company.

    If this is the first contact for the company, it automatically becomes
    the main contact.
    """
    company = company_service.get_company(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    contact = company_contact_service.create_contact(db, company_id, data)
    return company_contact_service.contact_to_response(contact)


@router.put(
    "/{company_id}/contacts/{contact_id}",
    response_model=CompanyContactResponse,
)
def update_company_contact(
    company_id: uuid.UUID,
    contact_id: uuid.UUID,
    data: CompanyContactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyContactResponse:
    """Update a contact."""
    company = company_service.get_company(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    contact = company_contact_service.get_contact_by_company(db, company_id, contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    contact = company_contact_service.update_contact(db, contact, data)
    return company_contact_service.contact_to_response(contact)


@router.delete(
    "/{company_id}/contacts/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_company_contact(
    company_id: uuid.UUID,
    contact_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a contact.

    If the deleted contact was the main contact and other contacts exist,
    the first remaining contact becomes the main contact.
    """
    company = company_service.get_company(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    contact = company_contact_service.get_contact_by_company(db, company_id, contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    company_contact_service.delete_contact(db, contact)


@router.post(
    "/{company_id}/contacts/{contact_id}/set-main",
    response_model=CompanyContactResponse,
)
def set_main_contact(
    company_id: uuid.UUID,
    contact_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyContactResponse:
    """Set a contact as the main contact."""
    company = company_service.get_company(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    contact = company_contact_service.get_contact_by_company(db, company_id, contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    contact = company_contact_service.set_main_contact(db, contact)
    return company_contact_service.contact_to_response(contact)


@router.get(
    "/{company_id}/contacts/by-type/{contact_type}",
    response_model=list[CompanyContactResponse],
)
def get_contacts_by_type(
    company_id: uuid.UUID,
    contact_type: ContactType,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CompanyContactResponse]:
    """Get contacts by type."""
    company = company_service.get_company(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    contacts = company_contact_service.get_contacts_by_type(
        db, company_id, [contact_type]
    )
    return [company_contact_service.contact_to_response(c) for c in contacts]
