"""Event API endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.models import User
from src.models.enums import EventStatus
from src.schemas.event import EventCreate, EventDetailResponse, EventResponse, EventUpdate
from src.services import company_service, event_service

router = APIRouter()


@router.get("", response_model=list[EventResponse])
def list_events(
    company_id: Optional[str] = None,
    event_status: Optional[EventStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EventResponse]:
    """List events for the current user."""
    events = event_service.get_events(
        db,
        user_id=current_user.id,
        company_id=company_id,
        status=event_status,
    )
    return [EventResponse.model_validate(e) for e in events]


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    data: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EventResponse:
    """Create a new event."""
    # Verify company exists
    company = company_service.get_company(db, data.company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company not found",
        )

    event = event_service.create_event(db, data, current_user.id)

    # Try to create tag in Paperless (async, non-blocking)
    try:
        await event_service.sync_event_tag_to_paperless(db, event)
    except Exception:
        # Log but don't fail if Paperless is unavailable
        pass

    return EventResponse.model_validate(event)


@router.get("/{event_id}", response_model=EventDetailResponse)
def get_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EventDetailResponse:
    """Get an event by ID."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    response = EventDetailResponse.model_validate(event)
    response.company_name = event.company.name if event.company else None
    return response


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: str,
    data: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EventResponse:
    """Update an event."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    # Verify company if changing
    if data.company_id and data.company_id != event.company_id:
        company = company_service.get_company(db, data.company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company not found",
            )

    # Validate status transition
    if data.status and data.status != event.status:
        if not event_service.can_transition_status(event.status, data.status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition from {event.status.value} to {data.status.value}",
            )

    event = event_service.update_event(db, event, data)

    # Sync tag if name changed
    if data.name:
        try:
            await event_service.sync_event_tag_to_paperless(db, event)
        except Exception:
            pass

    return EventResponse.model_validate(event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete an event."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    event_service.delete_event(db, event)


@router.post("/{event_id}/sync-tags")
async def sync_event_tags(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Manually sync tags to external systems for an event."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    result = await event_service.sync_event_tag_to_paperless(db, event)
    if result:
        return {"success": True, "tag": result}
    return {"success": False, "message": "No Paperless integration configured"}
