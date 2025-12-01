# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Photo API endpoints for Immich integration."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.integrations import IntegrationRegistry
from src.integrations.immich import ImmichProvider
from src.models import Event, IntegrationConfig, PhotoReference, User
from src.models.enums import IntegrationType
from src.schemas.location import LocationImageResponse
from src.schemas.photo import (
    PhotoAsset,
    PhotoReferenceCreate,
    PhotoReferenceResponse,
    PhotoReferenceUpdate,
)
from src.services import location_image_service

router = APIRouter()


def get_immich_provider(db: Session) -> ImmichProvider | None:
    """Get active Immich provider if configured."""
    config = (
        db.query(IntegrationConfig)
        .filter(
            IntegrationConfig.integration_type == IntegrationType.IMMICH,
            IntegrationConfig.is_active.is_(True),
        )
        .first()
    )

    if not config:
        return None

    from src.encryption import decrypt_config

    decrypted = decrypt_config(config.config_encrypted)
    provider = IntegrationRegistry.create_provider("immich", decrypted)
    return provider  # type: ignore


@router.get("/{event_id}/photos", response_model=list[PhotoAsset])
async def get_event_photos(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PhotoAsset]:
    """
    Get photos from Immich matching event location and dates.

    Requires Immich integration to be configured and event to have location data.
    """
    # Get event
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Check if event has location
    if not event.latitude or not event.longitude:
        return []  # No location, can't search

    # Get Immich provider
    provider = get_immich_provider(db)
    if not provider:
        raise HTTPException(
            status_code=400,
            detail="Immich integration not configured",
        )

    try:
        # Search for photos
        # Extend date range by 1 day on each side to catch edge cases
        start_date = datetime.combine(event.start_date, datetime.min.time())
        end_date = datetime.combine(event.end_date, datetime.max.time()) + timedelta(days=1)

        assets = await provider.search_by_location_and_date(
            latitude=event.latitude,
            longitude=event.longitude,
            start_date=start_date,
            end_date=end_date,
        )

        # Get already-linked photo IDs
        linked_ids = {
            ref.immich_asset_id
            for ref in db.query(PhotoReference.immich_asset_id)
            .filter(PhotoReference.event_id == event_id)
            .all()
        }

        # Convert to response schema
        result = []
        for asset in assets:
            exif = asset.get("exifInfo", {})
            result.append(
                PhotoAsset(
                    id=asset["id"],
                    original_filename=asset.get("originalFileName"),
                    thumbnail_url=f"/api/v1/events/{event_id}/photos/{asset['id']}/thumbnail",
                    taken_at=exif.get("dateTimeOriginal"),
                    latitude=exif.get("latitude"),
                    longitude=exif.get("longitude"),
                    city=exif.get("city"),
                    country=exif.get("country"),
                    distance_km=asset.get("_distance_km"),
                    is_linked=asset["id"] in linked_ids,
                )
            )

        return result
    finally:
        await provider.close()


@router.get("/{event_id}/photos/references", response_model=list[PhotoReferenceResponse])
async def get_photo_references(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PhotoReferenceResponse]:
    """Get saved photo references for an event."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    references = (
        db.query(PhotoReference)
        .filter(PhotoReference.event_id == event_id)
        .order_by(PhotoReference.taken_at)
        .all()
    )

    return references


@router.post("/{event_id}/photos", response_model=PhotoReferenceResponse)
async def add_photo_reference(
    event_id: str,
    photo: PhotoReferenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PhotoReferenceResponse:
    """Add a photo reference to an event."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Check if already linked
    existing = (
        db.query(PhotoReference)
        .filter(
            PhotoReference.event_id == event_id,
            PhotoReference.immich_asset_id == photo.immich_asset_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Photo already linked to event")

    # Create reference
    reference = PhotoReference(
        event_id=event_id,
        immich_asset_id=photo.immich_asset_id,
        caption=photo.caption,
        include_in_report=photo.include_in_report,
        thumbnail_url=photo.thumbnail_url,
        taken_at=photo.taken_at,
        latitude=photo.latitude,
        longitude=photo.longitude,
    )
    db.add(reference)
    db.commit()
    db.refresh(reference)

    return reference


@router.put("/{event_id}/photos/{photo_id}", response_model=PhotoReferenceResponse)
async def update_photo_reference(
    event_id: str,
    photo_id: str,
    update: PhotoReferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PhotoReferenceResponse:
    """Update a photo reference caption or include_in_report flag."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    reference = (
        db.query(PhotoReference)
        .filter(PhotoReference.id == photo_id, PhotoReference.event_id == event_id)
        .first()
    )
    if not reference:
        raise HTTPException(status_code=404, detail="Photo reference not found")

    # Update fields
    if update.caption is not None:
        reference.caption = update.caption
    if update.include_in_report is not None:
        reference.include_in_report = update.include_in_report

    db.commit()
    db.refresh(reference)

    return reference


@router.delete("/{event_id}/photos/{photo_id}")
async def delete_photo_reference(
    event_id: str,
    photo_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Remove a photo reference from an event."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    reference = (
        db.query(PhotoReference)
        .filter(PhotoReference.id == photo_id, PhotoReference.event_id == event_id)
        .first()
    )
    if not reference:
        raise HTTPException(status_code=404, detail="Photo reference not found")

    db.delete(reference)
    db.commit()

    return {"message": "Photo reference deleted"}


@router.get("/{event_id}/photos/{asset_id}/thumbnail")
async def proxy_photo_thumbnail(
    event_id: str,
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Proxy thumbnail from Immich.

    Browsers can't send API key headers on img tags,
    so we proxy through the backend.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    provider = get_immich_provider(db)
    if not provider:
        raise HTTPException(
            status_code=400,
            detail="Immich integration not configured",
        )

    try:
        content, content_type = await provider.get_asset_thumbnail(asset_id)
        return Response(content=content, media_type=content_type)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch thumbnail: {e}") from e
    finally:
        await provider.close()


@router.get("/{event_id}/location-image", response_model=LocationImageResponse | None)
async def get_event_location_image(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LocationImageResponse | None:
    """
    Get eyecandy image for event location.

    Returns None if no Unsplash API key is configured or location not set.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

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
