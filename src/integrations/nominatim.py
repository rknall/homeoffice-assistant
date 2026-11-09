# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""OpenStreetMap Nominatim geocoding client."""

import httpx

from src.schemas.location import LocationSuggestion
from src.version import APP_VERSION

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = (
    f"HomeOfficeAssistant/{APP_VERSION} "
    "(https://github.com/rknall/homeoffice-assistant)"
)


async def search_locations(q: str, limit: int, lang: str) -> list[LocationSuggestion]:
    """Search locations via Nominatim.

    Args:
        q: Search query.
        limit: Maximum number of results.
        lang: Preferred result languages (Accept-Language value).

    Returns:
        Location suggestions; entries without a country are skipped.

    Raises:
        httpx.HTTPError: On transport errors or a non-2xx response.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            NOMINATIM_URL,
            params={"q": q, "format": "json", "addressdetails": 1, "limit": limit},
            headers={"User-Agent": USER_AGENT, "Accept-Language": lang},
            timeout=10.0,
        )
        resp.raise_for_status()
        results = resp.json()

    suggestions: list[LocationSuggestion] = []
    for result in results:
        address = result.get("address", {})
        country = address.get("country", "")
        if not country:
            continue
        city = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
            or address.get("state")
        )
        suggestions.append(
            LocationSuggestion(
                city=city,
                country=country,
                country_code=address.get("country_code", "").upper(),
                latitude=float(result["lat"]),
                longitude=float(result["lon"]),
                display_name=result.get("display_name", ""),
            )
        )
    return suggestions
