# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Photo schemas for Immich integration."""

import datetime
import uuid

from pydantic import BaseModel


class PhotoAsset(BaseModel):
    """Photo asset from Immich with location metadata."""

    id: str
    original_filename: str | None = None
    thumbnail_url: str | None = None
    taken_at: datetime.datetime | None = None
    latitude: float | None = None
    longitude: float | None = None
    city: str | None = None
    country: str | None = None
    distance_km: float | None = None
    is_linked: bool = False  # Whether this photo is already linked to the event


class PhotoReferenceCreate(BaseModel):
    """Schema for adding a photo reference to an event."""

    immich_asset_id: str
    caption: str | None = None
    include_in_report: bool = False
    # Optional metadata (will be fetched from Immich if not provided)
    thumbnail_url: str | None = None
    taken_at: datetime.datetime | None = None
    latitude: float | None = None
    longitude: float | None = None


class PhotoReferenceUpdate(BaseModel):
    """Schema for updating a photo reference."""

    caption: str | None = None
    include_in_report: bool | None = None


class PhotoReferenceResponse(BaseModel):
    """Photo reference response schema."""

    id: uuid.UUID
    event_id: uuid.UUID
    immich_asset_id: str
    caption: str | None
    include_in_report: bool
    thumbnail_url: str | None
    taken_at: datetime.datetime | None
    latitude: float | None
    longitude: float | None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}
