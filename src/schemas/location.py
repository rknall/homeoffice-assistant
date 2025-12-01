# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Location schemas for geocoding and images."""
import datetime

from pydantic import BaseModel


class LocationSuggestion(BaseModel):
    """Location suggestion from geocoding API."""

    city: str | None = None
    country: str
    country_code: str
    latitude: float
    longitude: float
    display_name: str


class LocationImageResponse(BaseModel):
    """Response for location eyecandy image."""

    image_url: str
    thumbnail_url: str
    photographer_name: str | None = None
    photographer_url: str | None = None
    # Unsplash requires attribution
    attribution_html: str | None = None


class LocationImageCacheResponse(BaseModel):
    """Full location image cache response."""

    id: str
    city: str | None
    country: str
    unsplash_id: str
    image_url: str
    thumbnail_url: str
    photographer_name: str | None
    photographer_url: str | None
    fetched_at: datetime.datetime
    expires_at: datetime.datetime

    model_config = {"from_attributes": True}
