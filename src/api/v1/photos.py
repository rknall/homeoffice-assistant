# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Photo API endpoints for Immich integration."""

import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from src.api.deps import require_event_permission
from src.api.provider_errors import provider_errors
from src.database import get_db
from src.integrations.immich import ImmichProvider
from src.models import Event, PhotoReference
from src.models.enums import IntegrationType
from src.schemas.location import LocationImageResponse
from src.schemas.photo import (
    PhotoAsset,
    PhotoReferenceCreate,
    PhotoReferenceResponse,
    PhotoReferenceUpdate,
)
from src.services import integration_service, location_image_service, photo_service
from src.services.integration_service import NoActiveIntegrationError

router = APIRouter()
logger = logging.getLogger(__name__)

read_event = require_event_permission("event.read")
write_event = require_event_permission("event.write")


@asynccontextmanager
async def _open_immich(db: Session) -> AsyncIterator[ImmichProvider]:
    """Open the active Immich provider, reporting open errors as HTTP errors.

    The photo gallery hides the "not configured" message, so a missing Immich
    integration keeps that wording.
    """
    with provider_errors():
        try:
            async with integration_service.open_active_provider(
                db, IntegrationType.IMMICH
            ) as provider:
                yield provider
        except NoActiveIntegrationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Immich integration not configured",
            ) from e


def _get_reference_or_404(
    db: Session, event: Event, photo_id: uuid.UUID
) -> PhotoReference:
    """Return a photo reference of the event or raise 404."""
    reference = photo_service.get_photo_reference(db, event, photo_id)
    if reference is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo reference not found",
        )
    return reference


@router.get("/{event_id}/photos", response_model=list[PhotoAsset])
async def get_event_photos(
    db: Session = Depends(get_db),
    event: Event = Depends(read_event),
) -> list[PhotoAsset]:
    """Get photos from Immich matching event location and dates.

    Returns an empty list when the event has no location.
    """
    criteria = photo_service.build_search_criteria(event, date_only=False)
    if criteria is None:
        return []
    async with _open_immich(db) as provider:
        return await photo_service.search_photos(db, event, provider, criteria)


@router.get("/{event_id}/photos/by-date", response_model=list[PhotoAsset])
async def get_event_photos_by_date(
    db: Session = Depends(get_db),
    event: Event = Depends(read_event),
) -> list[PhotoAsset]:
    """Get photos from Immich matching the event date range only.

    This is a manual search option when location-based search doesn't find
    results. Only available for events that have started.
    """
    criteria = photo_service.build_search_criteria(event, date_only=True)
    if criteria is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date-based search is only available for past events",
        )
    async with _open_immich(db) as provider:
        return await photo_service.search_photos(db, event, provider, criteria)


@router.get(
    "/{event_id}/photos/references", response_model=list[PhotoReferenceResponse]
)
async def get_photo_references(
    db: Session = Depends(get_db),
    event: Event = Depends(read_event),
) -> list[PhotoReference]:
    """Get saved photo references for an event."""
    return photo_service.list_photo_references(db, event)


@router.post("/{event_id}/photos", response_model=PhotoReferenceResponse)
async def add_photo_reference(
    photo: PhotoReferenceCreate,
    db: Session = Depends(get_db),
    event: Event = Depends(write_event),
) -> PhotoReference:
    """Add a photo reference to an event."""
    try:
        return photo_service.add_photo_reference(db, event, photo)
    except photo_service.PhotoAlreadyLinkedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.put("/{event_id}/photos/{photo_id}", response_model=PhotoReferenceResponse)
async def update_photo_reference(
    photo_id: uuid.UUID,
    update: PhotoReferenceUpdate,
    db: Session = Depends(get_db),
    event: Event = Depends(write_event),
) -> PhotoReference:
    """Update a photo reference caption or include_in_report flag."""
    reference = _get_reference_or_404(db, event, photo_id)
    return photo_service.update_photo_reference(db, reference, update)


@router.delete("/{event_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo_reference(
    photo_id: uuid.UUID,
    db: Session = Depends(get_db),
    event: Event = Depends(write_event),
) -> None:
    """Remove a photo reference from an event."""
    reference = _get_reference_or_404(db, event, photo_id)
    photo_service.delete_photo_reference(db, reference)


@router.get("/{event_id}/photos/{asset_id}/thumbnail")
async def proxy_photo_thumbnail(
    asset_id: str,
    db: Session = Depends(get_db),
    event: Event = Depends(read_event),
) -> Response:
    """Proxy a thumbnail from Immich.

    Browsers can't send API key headers on img tags, so we proxy through the
    backend. Only assets linked to the event or found by its photo searches
    are served; any other asset id is reported as not found.
    """
    async with _open_immich(db) as provider:
        if not await photo_service.asset_belongs_to_event(
            db, event, asset_id, provider
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found"
            )
        try:
            content, content_type = await provider.get_asset_thumbnail(asset_id)
        except httpx.HTTPError as e:
            logger.error("Failed to fetch thumbnail %s: %s", asset_id, e)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch thumbnail",
            ) from e
    return Response(content=content, media_type=content_type)


@router.get("/{event_id}/location-image", response_model=LocationImageResponse | None)
async def get_event_location_image(
    db: Session = Depends(get_db),
    event: Event = Depends(read_event),
) -> LocationImageResponse | None:
    """Get eyecandy image for event location.

    Returns None if no Unsplash API key is configured or location not set.
    """
    # Need at least country
    if not event.country:
        return None

    image = await location_image_service.get_location_image(
        db, event.city, event.country
    )

    if not image:
        return None

    return LocationImageResponse(
        image_url=image.image_url,
        thumbnail_url=image.thumbnail_url,
        photographer_name=image.photographer_name,
        photographer_url=image.photographer_url,
        attribution_html=location_image_service.get_attribution_html(image),
    )
