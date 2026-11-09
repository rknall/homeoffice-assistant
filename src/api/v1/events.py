# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Event API endpoints."""

import contextlib
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import (
    ensure_permission,
    get_current_user,
    require_event_permission,
    require_permission,
)
from src.database import get_db
from src.models import Event, User
from src.models.enums import EventStatus
from src.schemas.event import (
    EventCountResponse,
    EventCreate,
    EventDetailResponse,
    EventResponse,
    EventUpdate,
    EventWithSummary,
)
from src.services import (
    company_service,
    event_service,
    rbac_service,
)

router = APIRouter()

# Event routes check the event.* codes for the event's company. List and
# count read the optional company_id filter; without it, holding event.read in
# any company passes and the results are limited to the permitted companies.
read_events = require_permission("event.read", company_id_param="company_id")
write_events = require_permission("event.write", company_id_param="company_id")
read_event = require_event_permission("event.read")
write_event = require_event_permission("event.write")
delete_event_permission = require_event_permission("event.delete")


@router.get("/count", response_model=EventCountResponse)
def count_events(
    company_id: uuid.UUID | None = None,
    event_status: EventStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(read_events),
) -> EventCountResponse:
    """Count events for the current user with optional filters.

    More efficient than listing all events when only the count is needed.
    Without a company filter only events of permitted companies count.
    """
    allowed = (
        None
        if company_id is not None
        else rbac_service.companies_with_permission(db, current_user, "event.read")
    )
    scopes = [company_id] if allowed is None else sorted(allowed)
    count = sum(
        event_service.count_events(
            db,
            user_id=current_user.id,
            company_id=scope,
            status=event_status,
        )
        for scope in scopes
    )
    return EventCountResponse(count=count)


@router.get("", response_model=list[EventDetailResponse])
def list_events(
    company_id: uuid.UUID | None = None,
    event_status: EventStatus | None = None,
    include_summary: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(read_events),
) -> list[EventDetailResponse] | list[EventWithSummary]:
    """List events for the current user with company info.

    Without a company filter only events of permitted companies are listed.
    """
    events = event_service.get_events(
        db,
        user_id=current_user.id,
        company_id=company_id,
        status=event_status,
        include_company=True,
    )
    if company_id is None:
        allowed = rbac_service.companies_with_permission(db, current_user, "event.read")
        if allowed is not None:
            events = [e for e in events if e.company_id in allowed]

    if include_summary:
        # Get summaries for all events in one query
        summaries = event_service.get_event_summaries(db, [e.id for e in events])
        result = []
        for e in events:
            response = EventWithSummary.model_validate(e)
            response.company_name = e.company.name if e.company else None
            summary = summaries.get(e.id, {})
            response.expense_count = summary.get("expense_count", 0)
            response.expense_total = float(summary.get("expense_total", 0))
            response.todo_count = summary.get("todo_count", 0)
            response.todo_incomplete_count = summary.get("todo_incomplete_count", 0)
            result.append(response)
        return result

    result = []
    for e in events:
        response = EventDetailResponse.model_validate(e)
        response.company_name = e.company.name if e.company else None
        result.append(response)
    return result


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    data: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(write_events),
) -> EventResponse:
    """Create a new event."""
    ensure_permission(db, current_user, "event.write", data.company_id)
    # Verify company exists
    company = company_service.get_company(db, data.company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company not found",
        )

    event = event_service.create_event(db, data, current_user.id)

    # Try to add event as custom field choice in Paperless (async, non-blocking)
    with contextlib.suppress(Exception):
        await event_service.sync_event_to_paperless_custom_field(db, event)

    return EventResponse.model_validate(event)


@router.get("/{event_id}", response_model=EventDetailResponse)
def get_event(
    event: Event = Depends(read_event),
) -> EventDetailResponse:
    """Get an event by ID."""
    response = EventDetailResponse.model_validate(event)
    response.company_name = event.company.name if event.company else None
    return response


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    data: EventUpdate,
    db: Session = Depends(get_db),
    event: Event = Depends(write_event),
    current_user: User = Depends(get_current_user),
) -> EventResponse:
    """Update an event."""
    # Moving the event needs write access in the target company as well
    if data.company_id and data.company_id != event.company_id:
        ensure_permission(db, current_user, "event.write", data.company_id)
        company = company_service.get_company(db, data.company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company not found",
            )

    event = event_service.update_event(db, event, data)

    # Sync custom field if name changed
    if data.name:
        with contextlib.suppress(Exception):
            await event_service.sync_event_to_paperless_custom_field(db, event)

    return EventResponse.model_validate(event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    db: Session = Depends(get_db),
    event: Event = Depends(delete_event_permission),
) -> None:
    """Delete an event."""
    event_service.delete_event(db, event)
