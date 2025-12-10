# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Company contact service."""

import json

from sqlalchemy.orm import Session

from src.models import CompanyContact
from src.models.enums import ContactType
from src.schemas.company_contact import (
    CompanyContactCreate,
    CompanyContactResponse,
    CompanyContactUpdate,
)


def get_contacts(db: Session, company_id: str) -> list[CompanyContact]:
    """Get all contacts for a company."""
    return (
        db.query(CompanyContact)
        .filter(CompanyContact.company_id == company_id)
        .order_by(CompanyContact.is_main_contact.desc(), CompanyContact.name)
        .all()
    )


def get_contact(db: Session, contact_id: str) -> CompanyContact | None:
    """Get a single contact by ID."""
    return db.query(CompanyContact).filter(CompanyContact.id == contact_id).first()


def get_contact_by_company(
    db: Session, company_id: str, contact_id: str
) -> CompanyContact | None:
    """Get a contact by ID, ensuring it belongs to the specified company."""
    return (
        db.query(CompanyContact)
        .filter(
            CompanyContact.id == contact_id,
            CompanyContact.company_id == company_id,
        )
        .first()
    )


def create_contact(
    db: Session, company_id: str, data: CompanyContactCreate
) -> CompanyContact:
    """Create a new contact for a company.

    If this is the first contact for the company, it automatically becomes
    the main contact. If is_main_contact is True, it unsets any existing
    main contact.
    """
    # Check if this will be the first contact - make it main automatically
    existing_contacts = get_contacts(db, company_id)
    is_first_contact = len(existing_contacts) == 0

    # If requesting to be main contact, unset existing main
    if data.is_main_contact and not is_first_contact:
        _unset_main_contact(db, company_id)

    contact = CompanyContact(
        company_id=company_id,
        name=data.name,
        email=data.email,
        phone=data.phone,
        title=data.title,
        department=data.department,
        notes=data.notes,
        contact_types=json.dumps([ct.value for ct in data.contact_types]),
        is_main_contact=is_first_contact or data.is_main_contact,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def update_contact(
    db: Session, contact: CompanyContact, data: CompanyContactUpdate
) -> CompanyContact:
    """Update an existing contact."""
    if data.name is not None:
        contact.name = data.name
    if data.email is not None:
        contact.email = data.email
    if data.phone is not None:
        contact.phone = data.phone
    if data.title is not None:
        contact.title = data.title
    if data.department is not None:
        contact.department = data.department
    if data.notes is not None:
        contact.notes = data.notes
    if data.contact_types is not None:
        contact.contact_types = json.dumps([ct.value for ct in data.contact_types])
    if data.is_main_contact is True:
        # Unset other main contacts first
        _unset_main_contact(db, contact.company_id)
        contact.is_main_contact = True
    elif data.is_main_contact is False:
        # Only allow unsetting if there are other contacts
        other_contacts = (
            db.query(CompanyContact)
            .filter(
                CompanyContact.company_id == contact.company_id,
                CompanyContact.id != contact.id,
            )
            .count()
        )
        if other_contacts > 0:
            # Set another contact as main
            first_other = (
                db.query(CompanyContact)
                .filter(
                    CompanyContact.company_id == contact.company_id,
                    CompanyContact.id != contact.id,
                )
                .first()
            )
            if first_other:
                first_other.is_main_contact = True
            contact.is_main_contact = False

    db.commit()
    db.refresh(contact)
    return contact


def delete_contact(db: Session, contact: CompanyContact) -> None:
    """Delete a contact.

    If the deleted contact was the main contact and other contacts exist,
    the first remaining contact becomes the main contact.
    """
    was_main = contact.is_main_contact
    company_id = contact.company_id

    db.delete(contact)
    db.flush()  # ensure deletion is applied before checking remaining contacts

    if was_main:
        # Find another contact to make main
        first_remaining = (
            db.query(CompanyContact)
            .filter(CompanyContact.company_id == company_id)
            .first()
        )
        if first_remaining:
            first_remaining.is_main_contact = True

    db.commit()


def get_main_contact(db: Session, company_id: str) -> CompanyContact | None:
    """Get the main contact for a company."""
    return (
        db.query(CompanyContact)
        .filter(
            CompanyContact.company_id == company_id,
            CompanyContact.is_main_contact == True,  # noqa: E712
        )
        .first()
    )


def set_main_contact(db: Session, contact: CompanyContact) -> CompanyContact:
    """Set a contact as the main contact, unsetting any existing main contact."""
    _unset_main_contact(db, contact.company_id)
    contact.is_main_contact = True
    db.commit()
    db.refresh(contact)
    return contact


def get_contacts_by_type(
    db: Session, company_id: str, contact_types: list[ContactType]
) -> list[CompanyContact]:
    """Get contacts matching any of the specified types.

    Contacts are returned if they have at least one of the specified types.
    """
    all_contacts = get_contacts(db, company_id)
    type_values = [ct.value for ct in contact_types]

    matching_contacts = []
    for contact in all_contacts:
        contact_type_values = json.loads(contact.contact_types)
        if any(ct in type_values for ct in contact_type_values):
            matching_contacts.append(contact)

    return matching_contacts


def validate_contact_types_exist(
    db: Session, company_id: str, required_types: list[ContactType]
) -> tuple[bool, list[ContactType]]:
    """Check if company has contacts for all required types.

    Returns:
        Tuple of (is_valid, missing_types)
        - is_valid: True if contacts exist for all required types
        - missing_types: List of types that have no matching contacts
    """
    if not required_types:
        return True, []

    all_contacts = get_contacts(db, company_id)

    # Collect all types that have at least one contact
    covered_types = set()
    for contact in all_contacts:
        contact_type_values = json.loads(contact.contact_types)
        for ct in contact_type_values:
            covered_types.add(ct)

    # Check which required types are missing
    missing_types = []
    for required_type in required_types:
        if required_type.value not in covered_types:
            missing_types.append(required_type)

    return len(missing_types) == 0, missing_types


def _unset_main_contact(db: Session, company_id: str) -> None:
    """Unset the main contact flag for all contacts of a company."""
    db.query(CompanyContact).filter(
        CompanyContact.company_id == company_id,
        CompanyContact.is_main_contact == True,  # noqa: E712
    ).update({CompanyContact.is_main_contact: False})


def contact_to_response(contact: CompanyContact) -> CompanyContactResponse:
    """Convert a CompanyContact to a CompanyContactResponse."""
    contact_types_list = json.loads(contact.contact_types)
    return CompanyContactResponse(
        id=contact.id,
        company_id=contact.company_id,
        name=contact.name,
        email=contact.email,
        phone=contact.phone,
        title=contact.title,
        department=contact.department,
        notes=contact.notes,
        contact_types=[ContactType(ct) for ct in contact_types_list],
        is_main_contact=contact.is_main_contact,
        created_at=contact.created_at,
        updated_at=contact.updated_at,
    )
