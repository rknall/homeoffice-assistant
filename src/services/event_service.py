# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Event service."""

import uuid

from sqlalchemy.orm import Session, joinedload

from src.integrations.base import DocumentProvider
from src.models import Event
from src.models.enums import EventStatus
from src.plugins.events import AppEvent, event_bus
from src.schemas.event import EventCreate, EventUpdate
from src.services import integration_service


def get_events(
    db: Session,
    user_id: uuid.UUID | None = None,
    company_id: uuid.UUID | None = None,
    status: EventStatus | None = None,
    include_company: bool = False,
) -> list[Event]:
    """Get events with optional filters."""
    query = db.query(Event)
    if include_company:
        query = query.options(joinedload(Event.company))
    if user_id:
        query = query.filter(Event.user_id == user_id)
    if company_id:
        query = query.filter(Event.company_id == company_id)
    if status:
        query = query.filter(Event.status == status)
    return query.order_by(Event.start_date.desc(), Event.end_date.desc()).all()


def get_event(db: Session, event_id: uuid.UUID) -> Event | None:
    """Get an event by ID."""
    return db.query(Event).filter(Event.id == event_id).first()


def get_event_for_user(
    db: Session,
    event_id: uuid.UUID,
    user_id: uuid.UUID,
    include_company: bool = False,
) -> Event | None:
    """Get an event by ID that belongs to a specific user."""
    query = db.query(Event)
    if include_company:
        query = query.options(joinedload(Event.company))
    return query.filter(Event.id == event_id, Event.user_id == user_id).first()


def create_event(db: Session, data: EventCreate, user_id: uuid.UUID) -> Event:
    """Create a new event."""
    event = Event(
        user_id=user_id,
        company_id=data.company_id,
        name=data.name,
        description=data.description,
        start_date=data.start_date,
        end_date=data.end_date,
        status=data.status,
        external_tag=data.name,  # Keep for backward compat
        # Use provided custom field value if set, otherwise default to name
        paperless_custom_field_value=data.paperless_custom_field_value or data.name,
        # Location fields
        city=data.city,
        country=data.country,
        country_code=data.country_code,
        latitude=data.latitude,
        longitude=data.longitude,
        # Cover image fields
        cover_image_url=data.cover_image_url,
        cover_thumbnail_url=data.cover_thumbnail_url,
        cover_photographer_name=data.cover_photographer_name,
        cover_photographer_url=data.cover_photographer_url,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    # Publish event created
    event_bus.publish_sync(
        AppEvent.EVENT_CREATED,
        {
            "event_id": str(event.id),
            "user_id": str(event.user_id),
            "company_id": str(event.company_id) if event.company_id else None,
            "name": event.name,
        },
    )

    return event


def update_event(db: Session, event: Event, data: EventUpdate) -> Event:
    """Update an existing event."""
    if data.name is not None:
        event.name = data.name
        event.external_tag = data.name  # Keep for backward compat
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
    # Handle paperless_custom_field_value - use explicit value if provided
    if data.paperless_custom_field_value is not None:
        event.paperless_custom_field_value = data.paperless_custom_field_value

    # Location fields - update regardless of None to allow clearing
    update_data = data.model_dump(exclude_unset=True)
    if "city" in update_data:
        event.city = data.city
    if "country" in update_data:
        event.country = data.country
    if "country_code" in update_data:
        event.country_code = data.country_code
    if "latitude" in update_data:
        event.latitude = data.latitude
    if "longitude" in update_data:
        event.longitude = data.longitude

    # Cover image fields
    if "cover_image_url" in update_data:
        event.cover_image_url = data.cover_image_url
    if "cover_thumbnail_url" in update_data:
        event.cover_thumbnail_url = data.cover_thumbnail_url
    if "cover_photographer_name" in update_data:
        event.cover_photographer_name = data.cover_photographer_name
    if "cover_photographer_url" in update_data:
        event.cover_photographer_url = data.cover_photographer_url

    db.commit()
    db.refresh(event)

    # Publish event updated
    event_bus.publish_sync(
        AppEvent.EVENT_UPDATED,
        {
            "event_id": str(event.id),
            "user_id": str(event.user_id),
            "name": event.name,
        },
    )

    return event


def delete_event(db: Session, event: Event) -> None:
    """Delete an event."""
    event_id = str(event.id)
    user_id = str(event.user_id)
    name = event.name
    db.delete(event)
    db.commit()

    # Publish event deleted
    event_bus.publish_sync(
        AppEvent.EVENT_DELETED,
        {"event_id": event_id, "user_id": user_id, "name": name},
    )


async def sync_event_tag_to_paperless(db: Session, event: Event) -> dict | None:
    """Legacy: Create or get the tag for this event in Paperless-ngx."""
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


async def sync_event_to_paperless_custom_field(db: Session, event: Event) -> bool:
    """Add event name as a choice to the configured custom field in Paperless-ngx.

    Returns True if the choice was added or already exists, False if sync failed.
    """
    paperless_config = integration_service.get_active_document_provider(db)
    if not paperless_config:
        return False

    provider = integration_service.create_provider_instance(paperless_config)
    if not provider or not isinstance(provider, DocumentProvider):
        return False

    try:
        # Get the custom field name from config
        config = integration_service.get_decrypted_config(paperless_config)
        custom_field_name = config.get("custom_field_name", "Trip")

        # Find the custom field by name
        custom_field = await provider.get_custom_field_by_name(custom_field_name)
        if not custom_field:
            # Custom field doesn't exist - user needs to create it in Paperless
            return False

        if custom_field.get("data_type") != "select":
            # Not a select type field
            return False

        # Get the value to sync
        value = event.paperless_custom_field_value or event.name

        # Check if choice already exists
        choice_exists = await provider.check_custom_field_choice_exists(
            custom_field["id"], value
        )
        if choice_exists:
            return True

        # Add the new choice
        await provider.add_custom_field_choice(custom_field["id"], value)
        return True
    except Exception:
        return False
    finally:
        await provider.close()


def can_transition_status(current: EventStatus, new: EventStatus) -> bool:
    """Check if a status transition is valid."""
    valid_transitions = {
        EventStatus.PLANNING: [EventStatus.ACTIVE],
        EventStatus.ACTIVE: [EventStatus.PAST, EventStatus.PLANNING],
        EventStatus.PAST: [EventStatus.ACTIVE],  # Allow reactivation
    }
    return new in valid_transitions.get(current, [])
