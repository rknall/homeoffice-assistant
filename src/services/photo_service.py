# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Immich photo search and the photo references linked to events."""

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.integrations.immich import ImmichProvider, asset_distance_km
from src.models import Event, PhotoReference
from src.schemas.photo import PhotoAsset, PhotoReferenceCreate, PhotoReferenceUpdate


class PhotoAlreadyLinkedError(Exception):
    """The Immich asset is already linked to the event."""


@dataclass(frozen=True)
class PhotoSearchCriteria:
    """What an Immich search for an event's photos looks for.

    Attributes:
        start: Earliest capture time.
        end: Latest capture time.
        latitude: Centre of the location search, None for a date-only search.
        longitude: Centre of the location search, None for a date-only search.
    """

    start: datetime
    end: datetime
    latitude: float | None = None
    longitude: float | None = None


def build_search_criteria(
    event: Event, *, date_only: bool
) -> PhotoSearchCriteria | None:
    """Build the criteria of one of the event's photo searches.

    The location search needs the event's coordinates. The date-only search is
    a manual fallback that is only offered once the event has started.

    Args:
        event: The event whose photos are searched.
        date_only: True for the date-only search, False for the location search.

    Returns:
        The criteria, or None when that search is not available for the event.
    """
    start = datetime.combine(event.start_date, datetime.min.time())
    # One extra day so photos from the evening of the last day are included
    # whatever the time zone of the capture timestamps.
    end = datetime.combine(event.end_date, datetime.max.time()) + timedelta(days=1)
    if date_only:
        if event.start_date > date.today():
            return None
        return PhotoSearchCriteria(start=start, end=end)
    if not event.latitude or not event.longitude:
        return None
    return PhotoSearchCriteria(
        start=start, end=end, latitude=event.latitude, longitude=event.longitude
    )


def event_search_criteria(event: Event) -> list[PhotoSearchCriteria]:
    """Return the criteria of every photo search available for an event."""
    candidates = (
        build_search_criteria(event, date_only=False),
        build_search_criteria(event, date_only=True),
    )
    return [criteria for criteria in candidates if criteria is not None]


def _linked_asset_ids(db: Session, event: Event) -> set[str]:
    """Return the Immich asset ids already linked to an event."""
    return set(
        db.scalars(
            select(PhotoReference.immich_asset_id).where(
                PhotoReference.event_id == event.id
            )
        )
    )


async def search_photos(
    db: Session,
    event: Event,
    provider: ImmichProvider,
    criteria: PhotoSearchCriteria,
) -> list[PhotoAsset]:
    """Search Immich for an event's photos.

    Args:
        db: Database session.
        event: The event whose photos are searched.
        provider: An open Immich provider.
        criteria: The search to run, from `build_search_criteria`.

    Returns:
        The matching photos, flagged when already linked to the event.
    """
    by_location = criteria.latitude is not None and criteria.longitude is not None
    if by_location:
        assets = await provider.search_by_location_and_date(
            latitude=criteria.latitude,
            longitude=criteria.longitude,
            start_date=criteria.start,
            end_date=criteria.end,
        )
    else:
        assets = await provider.search_by_date_only(
            start_date=criteria.start, end_date=criteria.end
        )

    linked_ids = _linked_asset_ids(db, event)
    result = []
    for asset in assets:
        exif = asset.get("exifInfo") or {}
        result.append(
            PhotoAsset(
                id=asset["id"],
                original_filename=asset.get("originalFileName"),
                thumbnail_url=(
                    f"/api/v1/events/{event.id}/photos/{asset['id']}/thumbnail"
                ),
                taken_at=exif.get("dateTimeOriginal"),
                latitude=exif.get("latitude"),
                longitude=exif.get("longitude"),
                city=exif.get("city"),
                country=exif.get("country"),
                distance_km=asset.get("_distance_km") if by_location else None,
                is_linked=asset["id"] in linked_ids,
            )
        )
    return result


def _taken_at(asset: dict[str, Any]) -> datetime | None:
    """Return an asset's capture time without time zone, if known."""
    exif = asset.get("exifInfo") or {}
    raw = exif.get("dateTimeOriginal") or asset.get("fileCreatedAt")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).replace(tzinfo=None)
    except TypeError, ValueError:
        return None


def _matches(
    asset: dict[str, Any], criteria: PhotoSearchCriteria, radius_km: float
) -> bool:
    """Check whether an Immich asset is one a search with the criteria finds."""
    taken_at = _taken_at(asset)
    if taken_at is None or not criteria.start <= taken_at <= criteria.end:
        return False
    if criteria.latitude is None or criteria.longitude is None:
        return True
    distance = asset_distance_km(asset, criteria.latitude, criteria.longitude)
    return distance is not None and distance <= radius_km


async def asset_belongs_to_event(
    db: Session, event: Event, asset_id: str, provider: ImmichProvider
) -> bool:
    """Check that an Immich asset may be shown in the context of an event.

    An asset belongs to the event when it is linked to it, or when one of the
    event's photo searches would find it. Linked assets are checked first, so
    Immich is only asked when there is no link.

    Args:
        db: Database session.
        event: The event the asset must belong to.
        asset_id: The Immich asset id.
        provider: An open Immich provider.

    Returns:
        True when the asset is linked to or found by the event's searches.
    """
    if asset_id in _linked_asset_ids(db, event):
        return True
    all_criteria = event_search_criteria(event)
    if not all_criteria:
        return False
    try:
        asset = await provider.get_asset_info(asset_id)
    except httpx.HTTPError:
        return False
    return any(
        _matches(asset, criteria, provider.search_radius_km)
        for criteria in all_criteria
    )


def list_photo_references(db: Session, event: Event) -> list[PhotoReference]:
    """List an event's photo references, oldest capture first."""
    return list(
        db.scalars(
            select(PhotoReference)
            .where(PhotoReference.event_id == event.id)
            .order_by(PhotoReference.taken_at)
        )
    )


def get_photo_reference(
    db: Session, event: Event, reference_id: uuid.UUID
) -> PhotoReference | None:
    """Get one photo reference of an event."""
    return db.scalars(
        select(PhotoReference).where(
            PhotoReference.id == reference_id, PhotoReference.event_id == event.id
        )
    ).first()


def add_photo_reference(
    db: Session, event: Event, data: PhotoReferenceCreate
) -> PhotoReference:
    """Link an Immich asset to an event.

    Args:
        db: Database session.
        event: The event to link the photo to.
        data: The asset id and its metadata.

    Returns:
        The new photo reference.

    Raises:
        PhotoAlreadyLinkedError: If the asset is already linked to the event.
    """
    if data.immich_asset_id in _linked_asset_ids(db, event):
        raise PhotoAlreadyLinkedError("Photo already linked to event")
    reference = PhotoReference(event_id=event.id, **data.model_dump())
    db.add(reference)
    db.commit()
    db.refresh(reference)
    return reference


def update_photo_reference(
    db: Session, reference: PhotoReference, data: PhotoReferenceUpdate
) -> PhotoReference:
    """Update the caption or report flag of a photo reference."""
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(reference, field, value)
    db.commit()
    db.refresh(reference)
    return reference


def delete_photo_reference(db: Session, reference: PhotoReference) -> None:
    """Remove a photo reference."""
    db.delete(reference)
    db.commit()
