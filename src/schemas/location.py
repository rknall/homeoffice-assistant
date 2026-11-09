# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Location schemas for geocoding and images."""

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
