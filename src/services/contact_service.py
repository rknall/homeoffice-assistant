# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Contact service for managing contacts met at an event."""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Session

from src.models import Contact
from src.schemas.contact import ContactCreate, ContactUpdate


def get_contact_for_event(
    db: Session, contact_id: uuid.UUID, event_id: uuid.UUID
) -> Contact | None:
    """Get a contact that belongs to a specific event.

    Args:
        db: Database session.
        contact_id: Contact UUID.
        event_id: Event UUID the contact must belong to.

    Returns:
        The contact, or None when it does not exist on that event.
    """
    return db.scalar(
        sa.select(Contact).where(Contact.id == contact_id, Contact.event_id == event_id)
    )


def create_contact(db: Session, event_id: uuid.UUID, data: ContactCreate) -> Contact:
    """Create a contact on an event.

    Args:
        db: Database session.
        event_id: Event UUID.
        data: Contact fields.

    Returns:
        The created contact.
    """
    contact = Contact(event_id=event_id, **data.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def update_contact(db: Session, contact: Contact, data: ContactUpdate) -> Contact:
    """Apply the fields set in ``data`` to a contact.

    Args:
        db: Database session.
        contact: Contact to update.
        data: Fields to change; unset fields are left as they are.

    Returns:
        The updated contact.
    """
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    db.commit()
    db.refresh(contact)
    return contact


def delete_contact(db: Session, contact: Contact) -> None:
    """Delete a contact.

    Args:
        db: Database session.
        contact: Contact to delete.
    """
    db.delete(contact)
    db.commit()
