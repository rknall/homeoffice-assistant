# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Location image service for fetching eyecandy images from Unsplash."""

import html
import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from src.integrations.base import ImageSearchProvider
from src.models import LocationImage
from src.models.enums import IntegrationType
from src.services.integration_service import (
    NoActiveIntegrationError,
    ProviderUnavailableError,
    open_active_provider,
)
from src.utils.time import utc_now

# Cache TTL in days
CACHE_TTL_DAYS = 7


def get_cached_image(
    db: Session, city: str | None, country: str
) -> LocationImage | None:
    """Get cached location image if it exists and hasn't expired."""
    now = utc_now()

    query = db.query(LocationImage).filter(
        and_(
            LocationImage.country == country,
            LocationImage.expires_at > now,
        )
    )

    if city:
        query = query.filter(LocationImage.city == city)
    else:
        query = query.filter(LocationImage.city.is_(None))

    return query.first()


async def fetch_from_unsplash(
    provider: ImageSearchProvider, city: str | None, country: str
) -> dict[str, Any] | None:
    """Fetch a location image through the Unsplash provider.

    Args:
        provider: The opened image search provider.
        city: Optional city name.
        country: Country name.

    Returns:
        The image data to cache, or None if there is no result or the search fails.
    """
    query_parts = [city, country, "landmark skyline"]
    search_query = " ".join(part for part in query_parts if part)
    try:
        data = await provider.search_images(search_query, per_page=1)
    except Exception:
        return None
    results = data.get("results", [])
    if not results:
        return None
    photo = results[0]
    return {
        "unsplash_id": photo["id"],
        "image_url": photo["urls"]["regular"],
        "thumbnail_url": photo["urls"]["small"],
        "photographer_name": photo["user"]["name"],
        "photographer_url": photo["user"].get("portfolio_url")
        or f"https://unsplash.com/@{photo['user']['username']}",
    }


def cache_image(
    db: Session,
    city: str | None,
    country: str,
    image_data: dict[str, Any],
) -> LocationImage:
    """Cache location image in database."""
    now = utc_now()

    # Check if there's an existing cache entry to update
    existing = (
        db.query(LocationImage)
        .filter(
            and_(
                LocationImage.country == country,
                LocationImage.city == city if city else LocationImage.city.is_(None),
            )
        )
        .first()
    )

    if existing:
        existing.unsplash_id = image_data["unsplash_id"]
        existing.image_url = image_data["image_url"]
        existing.thumbnail_url = image_data["thumbnail_url"]
        existing.photographer_name = image_data.get("photographer_name")
        existing.photographer_url = image_data.get("photographer_url")
        existing.fetched_at = now
        existing.expires_at = now + timedelta(days=CACHE_TTL_DAYS)
        db.commit()
        db.refresh(existing)
        return existing

    # Create new cache entry
    location_image = LocationImage(
        id=uuid.uuid4(),
        city=city,
        country=country,
        unsplash_id=image_data["unsplash_id"],
        image_url=image_data["image_url"],
        thumbnail_url=image_data["thumbnail_url"],
        photographer_name=image_data.get("photographer_name"),
        photographer_url=image_data.get("photographer_url"),
        fetched_at=now,
        expires_at=now + timedelta(days=CACHE_TTL_DAYS),
    )
    db.add(location_image)
    db.commit()
    db.refresh(location_image)
    return location_image


async def get_location_image(
    db: Session, city: str | None, country: str
) -> LocationImage | None:
    """Get location image for a city/country.

    First checks cache, then fetches through the active Unsplash integration.
    Returns None if no active Unsplash integration exists or the fetch fails.
    """
    try:
        async with open_active_provider(db, IntegrationType.UNSPLASH) as provider:
            cached = get_cached_image(db, city, country)
            if cached:
                return cached
            image_data = await fetch_from_unsplash(provider, city, country)
    except NoActiveIntegrationError, ProviderUnavailableError:
        return None  # Graceful fallback
    if not image_data:
        return None

    return cache_image(db, city, country, image_data)


def clear_expired_cache(db: Session) -> int:
    """Clear expired cache entries. Returns number of entries deleted."""
    now = utc_now()
    result = db.query(LocationImage).filter(LocationImage.expires_at < now).delete()
    db.commit()
    return result


def get_attribution_html(image: LocationImage) -> str:
    """Generate Unsplash attribution HTML (required by their API guidelines)."""
    utm = "homeoffice_assistant"
    if image.photographer_name and image.photographer_url:
        photo_url = html.escape(
            f"{image.photographer_url}?utm_source={utm}&utm_medium=referral"
        )
        unsplash_url = html.escape(
            f"https://unsplash.com?utm_source={utm}&utm_medium=referral"
        )
        name = html.escape(image.photographer_name)
        return (
            f'Photo by <a href="{photo_url}">{name}</a> on '
            f'<a href="{unsplash_url}">Unsplash</a>'
        )
    return 'Photo from <a href="https://unsplash.com">Unsplash</a>'
