# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Location image service for fetching eyecandy images from Unsplash."""

import uuid
from datetime import datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import and_
from sqlalchemy.orm import Session

from src.models import LocationImage, SystemSettings

# Cache TTL in days
CACHE_TTL_DAYS = 7

# Unsplash API base URL
UNSPLASH_API_URL = "https://api.unsplash.com"


def get_unsplash_api_key(db: Session) -> str | None:
    """Get Unsplash API key from system settings."""
    setting = (
        db.query(SystemSettings)
        .filter(SystemSettings.key == "unsplash_api_key")
        .first()
    )
    return setting.value if setting else None


def set_unsplash_api_key(db: Session, api_key: str) -> None:
    """Set Unsplash API key in system settings."""
    setting = (
        db.query(SystemSettings)
        .filter(SystemSettings.key == "unsplash_api_key")
        .first()
    )

    if setting:
        setting.value = api_key
    else:
        setting = SystemSettings(key="unsplash_api_key", value=api_key)
        db.add(setting)

    db.commit()


def get_cached_image(
    db: Session, city: str | None, country: str
) -> LocationImage | None:
    """Get cached location image if it exists and hasn't expired."""
    now = datetime.utcnow()

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
    api_key: str, city: str | None, country: str
) -> dict[str, Any] | None:
    """Fetch location image from Unsplash API."""
    # Build search query
    query_parts = []
    if city:
        query_parts.append(city)
    query_parts.append(country)
    query_parts.append("landmark skyline")
    search_query = " ".join(query_parts)

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{UNSPLASH_API_URL}/search/photos",
                headers={
                    "Authorization": f"Client-ID {api_key}",
                    "Accept-Version": "v1",
                },
                params={
                    "query": search_query,
                    "orientation": "landscape",
                    "per_page": 1,
                },
                timeout=10.0,
            )

            if resp.status_code != 200:
                return None

            data = resp.json()
            results = data.get("results", [])

            if not results:
                return None

            photo = results[0]
            return {
                "unsplash_id": photo["id"],
                "image_url": photo["urls"]["regular"],
                "thumbnail_url": photo["urls"]["small"],
                "photographer_name": photo["user"]["name"],
                "photographer_url": photo["user"]["links"]["html"],
            }
        except Exception:
            return None


def cache_image(
    db: Session,
    city: str | None,
    country: str,
    image_data: dict[str, Any],
) -> LocationImage:
    """Cache location image in database."""
    now = datetime.utcnow()

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

    First checks cache, then fetches from Unsplash if needed.
    Returns None if no API key is configured or fetch fails.
    """
    # Check if Unsplash API key is configured
    api_key = get_unsplash_api_key(db)
    if not api_key:
        return None  # Graceful fallback

    # Check cache
    cached = get_cached_image(db, city, country)
    if cached:
        return cached

    # Fetch from Unsplash
    image_data = await fetch_from_unsplash(api_key, city, country)
    if not image_data:
        return None

    # Cache and return
    return cache_image(db, city, country, image_data)


def clear_expired_cache(db: Session) -> int:
    """Clear expired cache entries. Returns number of entries deleted."""
    now = datetime.utcnow()
    result = db.query(LocationImage).filter(LocationImage.expires_at < now).delete()
    db.commit()
    return result


def get_attribution_html(image: LocationImage) -> str:
    """Generate Unsplash attribution HTML (required by their API guidelines)."""
    utm = "homeoffice_assistant"
    if image.photographer_name and image.photographer_url:
        photo_url = f"{image.photographer_url}?utm_source={utm}&utm_medium=referral"
        unsplash_url = f"https://unsplash.com?utm_source={utm}&utm_medium=referral"
        return (
            f'Photo by <a href="{photo_url}">{image.photographer_name}</a> on '
            f'<a href="{unsplash_url}">Unsplash</a>'
        )
    return 'Photo from <a href="https://unsplash.com">Unsplash</a>'
