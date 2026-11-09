# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Contact API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import require_event_permission
from src.database import get_db
from src.models import Contact, Event
from src.schemas.contact import ContactCreate, ContactResponse, ContactUpdate
from src.services import contact_service

router = APIRouter()


def _get_contact_or_404(db: Session, contact_id: uuid.UUID, event: Event) -> Contact:
    """Load a contact of the event or raise 404."""
    contact = contact_service.get_contact_for_event(db, contact_id, event.id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )
    return contact


@router.get("/{event_id}/contacts", response_model=list[ContactResponse])
def list_contacts(
    event: Event = Depends(require_event_permission("event.read")),
) -> list[ContactResponse]:
    """List contacts for an event."""
    return [ContactResponse.model_validate(c) for c in event.contacts]


@router.post(
    "/{event_id}/contacts",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_contact(
    data: ContactCreate,
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("event.write")),
) -> ContactResponse:
    """Create a new contact for an event."""
    contact = contact_service.create_contact(db, event.id, data)
    return ContactResponse.model_validate(contact)


@router.get("/{event_id}/contacts/{contact_id}", response_model=ContactResponse)
def get_contact(
    contact_id: uuid.UUID,
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("event.read")),
) -> ContactResponse:
    """Get a specific contact."""
    return ContactResponse.model_validate(_get_contact_or_404(db, contact_id, event))


@router.put("/{event_id}/contacts/{contact_id}", response_model=ContactResponse)
def update_contact(
    contact_id: uuid.UUID,
    data: ContactUpdate,
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("event.write")),
) -> ContactResponse:
    """Update a contact."""
    contact = _get_contact_or_404(db, contact_id, event)
    updated = contact_service.update_contact(db, contact, data)
    return ContactResponse.model_validate(updated)


@router.delete(
    "/{event_id}/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_contact(
    contact_id: uuid.UUID,
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("event.write")),
) -> None:
    """Delete a contact."""
    contact_service.delete_contact(db, _get_contact_or_404(db, contact_id, event))
