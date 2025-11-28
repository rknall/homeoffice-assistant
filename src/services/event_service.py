"""Event service."""
from typing import Optional

from sqlalchemy.orm import Session

from src.integrations.base import DocumentProvider
from src.models import Event
from src.models.enums import EventStatus
from src.schemas.event import EventCreate, EventUpdate
from src.services import integration_service


def get_events(
    db: Session,
    user_id: Optional[str] = None,
    company_id: Optional[str] = None,
    status: Optional[EventStatus] = None,
) -> list[Event]:
    """Get events with optional filters."""
    query = db.query(Event)
    if user_id:
        query = query.filter(Event.user_id == user_id)
    if company_id:
        query = query.filter(Event.company_id == company_id)
    if status:
        query = query.filter(Event.status == status)
    return query.order_by(Event.start_date.desc()).all()


def get_event(db: Session, event_id: str) -> Optional[Event]:
    """Get an event by ID."""
    return db.query(Event).filter(Event.id == event_id).first()


def get_event_for_user(db: Session, event_id: str, user_id: str) -> Optional[Event]:
    """Get an event by ID that belongs to a specific user."""
    return (
        db.query(Event)
        .filter(Event.id == event_id, Event.user_id == user_id)
        .first()
    )


def create_event(db: Session, data: EventCreate, user_id: str) -> Event:
    """Create a new event."""
    event = Event(
        user_id=user_id,
        company_id=data.company_id,
        name=data.name,
        description=data.description,
        start_date=data.start_date,
        end_date=data.end_date,
        status=data.status,
        external_tag=data.name,  # Use event name as the external tag
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def update_event(db: Session, event: Event, data: EventUpdate) -> Event:
    """Update an existing event."""
    if data.name is not None:
        event.name = data.name
        event.external_tag = data.name  # Update external tag too
    if data.description is not None:
        event.description = data.description
    if data.company_id is not None:
        event.company_id = data.company_id
    if data.start_date is not None:
        event.start_date = data.start_date
    if data.end_date is not None:
        event.end_date = data.end_date
    if data.status is not None:
        event.status = data.status

    db.commit()
    db.refresh(event)
    return event


def delete_event(db: Session, event: Event) -> None:
    """Delete an event."""
    db.delete(event)
    db.commit()


async def sync_event_tag_to_paperless(db: Session, event: Event) -> Optional[dict]:
    """Create or get the tag for this event in Paperless-ngx."""
    paperless_config = integration_service.get_active_document_provider(db)
    if not paperless_config:
        return None

    provider = integration_service.create_provider_instance(paperless_config)
    if not provider or not isinstance(provider, DocumentProvider):
        return None

    try:
        # Check if tag exists
        existing_tag = await provider.get_tag_by_name(event.external_tag or event.name)
        if existing_tag:
            return existing_tag

        # Create new tag
        return await provider.create_tag(event.external_tag or event.name)
    finally:
        await provider.close()


def can_transition_status(current: EventStatus, new: EventStatus) -> bool:
    """Check if a status transition is valid."""
    valid_transitions = {
        EventStatus.DRAFT: [EventStatus.PREPARATION],
        EventStatus.PREPARATION: [EventStatus.ACTIVE, EventStatus.DRAFT],
        EventStatus.ACTIVE: [EventStatus.COMPLETED],
        EventStatus.COMPLETED: [EventStatus.ARCHIVED, EventStatus.ACTIVE],
        EventStatus.ARCHIVED: [],
    }
    return new in valid_transitions.get(current, [])
