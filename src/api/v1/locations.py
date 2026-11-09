# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Location API endpoints for geocoding autocomplete."""

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.deps import get_current_user
from src.integrations import nominatim
from src.models import User
from src.schemas.location import LocationSuggestion

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("/autocomplete", response_model=list[LocationSuggestion])
async def autocomplete_location(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(5, ge=1, le=10, description="Maximum results"),
    lang: str = Query("de,en", description="Preferred languages for results"),
    _current_user: User = Depends(get_current_user),
) -> list[LocationSuggestion]:
    """Search for locations using OpenStreetMap Nominatim.

    Returns city, country, coordinates for location autocomplete.
    Supports German city names by default.
    """
    try:
        return await nominatim.search_locations(q, limit, lang)
    except httpx.HTTPError as e:
        logger.error("Nominatim HTTP error: %s", e)
        raise HTTPException(
            status_code=502, detail="Geocoding service unavailable"
        ) from e
