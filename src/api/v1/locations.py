# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Location API endpoints for geocoding autocomplete."""
import httpx
from fastapi import APIRouter, HTTPException, Query

from src.schemas.location import LocationSuggestion

router = APIRouter(prefix="/locations", tags=["locations"])

# OpenStreetMap Nominatim API
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "TravelManager/0.2 (contact@example.com)"


@router.get("/autocomplete", response_model=list[LocationSuggestion])
async def autocomplete_location(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(5, ge=1, le=10, description="Maximum results"),
) -> list[LocationSuggestion]:
    """
    Search for locations using OpenStreetMap Nominatim.

    Returns city, country, coordinates for location autocomplete.
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
                    "featuretype": "city",
                },
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept-Language": "en",
                },
                timeout=10.0,
            )

            if resp.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail="Geocoding service unavailable",
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
            raise HTTPException(
                status_code=502,
                detail=f"Geocoding service error: {e}",
            ) from e
