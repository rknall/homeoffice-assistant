# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Event service."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from src.integrations.base import DocumentProvider
from src.models import Event, Expense, Todo
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
    """Get events with optional filters.

    Note: Status is computed from dates, not stored. When filtering by status,
    we translate to date-based conditions:
    - UPCOMING: start_date > today
    - ACTIVE: start_date <= today <= end_date
    - PAST: end_date < today
    """
    query = db.query(Event)
    if include_company:
        query = query.options(joinedload(Event.company))
    if user_id:
        query = query.filter(Event.user_id == user_id)
    if company_id:
        query = query.filter(Event.company_id == company_id)

    # Filter by computed status using date conditions
    if status:
        today = date.today()
        if status == EventStatus.UPCOMING:
            query = query.filter(Event.start_date > today)
        elif status == EventStatus.ACTIVE:
            query = query.filter(Event.start_date <= today, Event.end_date >= today)
        elif status == EventStatus.PAST:
            query = query.filter(Event.end_date < today)

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
    """Create a new event.

    Note: status is computed from dates, not stored.
    """
    event = Event(
        user_id=user_id,
        company_id=data.company_id,
        name=data.name,
        description=data.description,
        start_date=data.start_date,
        end_date=data.end_date,
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
    """Update an existing event.

    Note: status is computed from dates, not stored.
    """
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


def get_event_summaries(
    db: Session,
    event_ids: list[uuid.UUID],
) -> dict[uuid.UUID, dict]:
    """Get expense and todo summaries for multiple events.

    Returns a dict mapping event_id to summary dict with:
    - expense_count: number of expenses
    - expense_total: sum of expense amounts
    - todo_count: total number of todos
    - todo_incomplete_count: number of incomplete todos
    """
    if not event_ids:
        return {}

    # Get expense summaries
    expense_results = (
        db.query(
            Expense.event_id,
            func.count(Expense.id).label("count"),
            func.sum(Expense.amount).label("total"),
        )
        .filter(Expense.event_id.in_(event_ids))
        .group_by(Expense.event_id)
        .all()
    )

    expense_map = {
        r.event_id: {"expense_count": r.count, "expense_total": r.total or Decimal(0)}
        for r in expense_results
    }

    # Get total todo counts
    todo_results = (
        db.query(
            Todo.event_id,
            func.count(Todo.id).label("total"),
        )
        .filter(Todo.event_id.in_(event_ids))
        .group_by(Todo.event_id)
        .all()
    )

    todo_map = {r.event_id: r.total or 0 for r in todo_results}

    # Get incomplete todo counts separately
    incomplete_results = (
        db.query(
            Todo.event_id,
            func.count(Todo.id).label("incomplete"),
        )
        .filter(Todo.event_id.in_(event_ids))
        .filter(Todo.completed.is_(False))
        .group_by(Todo.event_id)
        .all()
    )

    incomplete_map = {r.event_id: r.incomplete or 0 for r in incomplete_results}

    # Build result dict
    result = {}
    for event_id in event_ids:
        expense_data = expense_map.get(event_id, {})
        result[event_id] = {
            "expense_count": expense_data.get("expense_count", 0),
            "expense_total": expense_data.get("expense_total", Decimal(0)),
            "todo_count": todo_map.get(event_id, 0),
            "todo_incomplete_count": incomplete_map.get(event_id, 0),
        }

    return result
