# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Location API endpoints for geocoding autocomplete."""

import logging

import httpx
from fastapi import APIRouter, HTTPException, Query

from src.schemas.location import LocationSuggestion

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/locations", tags=["locations"])

# OpenStreetMap Nominatim API
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "HomeOfficeAssistant/0.2.0 (https://github.com/rknall/homeoffice-assistant)"


@router.get("/autocomplete", response_model=list[LocationSuggestion])
async def autocomplete_location(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(5, ge=1, le=10, description="Maximum results"),
    lang: str = Query("de,en", description="Preferred languages for results"),
) -> list[LocationSuggestion]:
    """Search for locations using OpenStreetMap Nominatim.

    Returns city, country, coordinates for location autocomplete.
    Supports German city names by default.
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                NOMINATIM_URL,
                params={
                    "q": q,
                    "format": "json",
                    "addressdetails": 1,
                    "limit": limit,
                },
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept-Language": lang,
                },
                timeout=10.0,
            )

            if resp.status_code != 200:
                logger.error(
                    f"Nominatim returned status {resp.status_code}: {resp.text[:200]}"
                )
                raise HTTPException(
                    status_code=502,
                    detail=f"Geocoding service unavailable (status {resp.status_code})",
                )

            results = resp.json()
            suggestions = []

            for result in results:
                address = result.get("address", {})

                # Extract city name (try multiple fields)
                city = (
                    address.get("city")
                    or address.get("town")
                    or address.get("village")
                    or address.get("municipality")
                    or address.get("state")
                )

                country = address.get("country", "")
                country_code = address.get("country_code", "").upper()

                if not country:
                    continue

                suggestions.append(
                    LocationSuggestion(
                        city=city,
                        country=country,
                        country_code=country_code,
                        latitude=float(result["lat"]),
                        longitude=float(result["lon"]),
                        display_name=result.get("display_name", ""),
                    )
                )

            return suggestions

        except httpx.HTTPError as e:
            logger.error(f"Nominatim HTTP error: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Geocoding service error: {e}",
            ) from e
        except Exception as e:
            logger.error(f"Nominatim unexpected error: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Geocoding service error: {e}",
            ) from e
