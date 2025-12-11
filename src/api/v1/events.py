# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Event API endpoints."""

import contextlib
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.integrations.base import DocumentProvider
from src.models import User
from src.models.enums import EventStatus
from src.schemas.event import (
    EventCreate,
    EventDetailResponse,
    EventResponse,
    EventUpdate,
)
from src.schemas.integration import DocumentResponse
from src.services import company_service, event_service, integration_service

router = APIRouter()


@router.get("", response_model=list[EventDetailResponse])
def list_events(
    company_id: uuid.UUID | None = None,
    event_status: EventStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EventDetailResponse]:
    """List events for the current user with company info."""
    events = event_service.get_events(
        db,
        user_id=current_user.id,
        company_id=company_id,
        status=event_status,
        include_company=True,
    )
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

    # Try to add event as custom field choice in Paperless (async, non-blocking)
    with contextlib.suppress(Exception):
        await event_service.sync_event_to_paperless_custom_field(db, event)

    return EventResponse.model_validate(event)


@router.get("/{event_id}", response_model=EventDetailResponse)
def get_event(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EventDetailResponse:
    """Get an event by ID."""
    event = event_service.get_event_for_user(
        db, event_id, current_user.id, include_company=True
    )
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
    event_id: uuid.UUID,
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
    if (
        data.status
        and data.status != event.status
        and not event_service.can_transition_status(event.status, data.status)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid: {event.status.value} -> {data.status.value}",
        )

    event = event_service.update_event(db, event, data)

    # Sync custom field if name changed
    if data.name:
        with contextlib.suppress(Exception):
            await event_service.sync_event_to_paperless_custom_field(db, event)

    return EventResponse.model_validate(event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: uuid.UUID,
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


@router.post("/{event_id}/sync-paperless")
async def sync_event_to_paperless(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Manually sync event to Paperless custom field."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    success = await event_service.sync_event_to_paperless_custom_field(db, event)
    if success:
        return {"success": True, "message": "Event synced to Paperless custom field"}
    return {
        "success": False,
        "message": "Sync failed - check Paperless integration config",
    }


@router.get("/{event_id}/documents", response_model=list[DocumentResponse])
async def get_event_documents(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DocumentResponse]:
    """Get documents from Paperless associated with this event."""
    event = event_service.get_event_for_user(
        db, event_id, current_user.id, include_company=True
    )
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    # Get active Paperless integration
    paperless_config = integration_service.get_active_document_provider(db)
    if not paperless_config:
        return []  # No Paperless integration configured

    provider = integration_service.create_provider_instance(paperless_config)
    if not provider or not isinstance(provider, DocumentProvider):
        return []

    try:
        # Get the custom field ID for filtering
        decrypted_config = integration_service.get_decrypted_config(paperless_config)
        custom_field_name = decrypted_config.get("custom_field_name", "Trip")
        custom_field = await provider.get_custom_field_by_name(custom_field_name)
        custom_field_id = custom_field["id"] if custom_field else None

        # Get company storage path
        storage_path_id = (
            event.company.paperless_storage_path_id if event.company else None
        )

        # Get documents matching event criteria
        documents = await provider.get_documents_for_event(
            storage_path_id=storage_path_id,
            custom_field_id=custom_field_id,
            custom_field_value=event.paperless_custom_field_value,
        )
        return [DocumentResponse(**doc) for doc in documents]
    finally:
        await provider.close()


@router.delete(
    "/{event_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_event_document(
    event_id: str,
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a document from Paperless.

    Warning: This permanently deletes the document!
    """
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    # Get active Paperless integration
    paperless_config = integration_service.get_active_document_provider(db)
    if not paperless_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Paperless integration configured",
        )

    provider = integration_service.create_provider_instance(paperless_config)
    if not provider or not isinstance(provider, DocumentProvider):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create Paperless provider",
        )

    try:
        success = await provider.delete_document(document_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete document from Paperless",
            )
    finally:
        await provider.close()


@router.get("/{event_id}/documents/{document_id}/preview")
async def get_document_preview(
    event_id: str,
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Get document content for preview from Paperless."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    # Get active Paperless integration
    paperless_config = integration_service.get_active_document_provider(db)
    if not paperless_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Paperless integration configured",
        )

    provider = integration_service.create_provider_instance(paperless_config)
    if not provider or not isinstance(provider, DocumentProvider):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create Paperless provider",
        )

    try:
        content, filename, content_type = await provider.download_document(document_id)
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download document: {e!s}",
        ) from e
    finally:
        await provider.close()
