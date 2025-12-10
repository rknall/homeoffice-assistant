# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for location_image_service."""

from datetime import datetime, timedelta

import pytest

from src.models import LocationImage, SystemSettings
from src.services import location_image_service


def test_unsplash_api_key_helpers(db_session):
    assert location_image_service.get_unsplash_api_key(db_session) is None
    location_image_service.set_unsplash_api_key(db_session, "key")
    assert location_image_service.get_unsplash_api_key(db_session) == "key"


def test_cache_image_create_and_update(db_session):
    data = {
        "unsplash_id": "abc",
        "image_url": "https://example.com/image.jpg",
        "thumbnail_url": "https://example.com/thumb.jpg",
        "photographer_name": "John",
        "photographer_url": "https://example.com/john",
    }
    cached = location_image_service.cache_image(db_session, "Vienna", "Austria", data)
    assert cached.unsplash_id == "abc"

    data["unsplash_id"] = "def"
    updated = location_image_service.cache_image(db_session, "Vienna", "Austria", data)
    assert updated.unsplash_id == "def"


def test_get_cached_image_respects_city_and_expiry(db_session):
    now = datetime.utcnow()
    image = LocationImage(
        city="Vienna",
        country="Austria",
        unsplash_id="id1",
        image_url="https://example.com/image.jpg",
        thumbnail_url="https://example.com/thumb.jpg",
        fetched_at=now,
        expires_at=now + timedelta(days=1),
    )
    db_session.add(image)
    db_session.commit()

    result = location_image_service.get_cached_image(db_session, "Vienna", "Austria")
    assert result == image


@pytest.mark.asyncio
async def test_fetch_from_unsplash(monkeypatch):
    class DummyResponse:
        status_code = 200

        def json(self):
            return {
                "results": [
                    {
                        "id": "abc",
                        "urls": {"regular": "image", "small": "thumb"},
                        "user": {"name": "John", "links": {"html": "profile"}},
                    }
                ]
            }

    class DummyClient:
        def __init__(self, response):
            self.response = response

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, *args, **kwargs):
            return self.response

    monkeypatch.setattr(
        location_image_service.httpx,
        "AsyncClient",
        lambda: DummyClient(DummyResponse()),
    )

    data = await location_image_service.fetch_from_unsplash("key", "Vienna", "Austria")
    assert data["unsplash_id"] == "abc"


@pytest.mark.asyncio
async def test_get_location_image_flows(monkeypatch, db_session):
    location_image_service.set_unsplash_api_key(db_session, "key")
    fetched_data = {
        "unsplash_id": "abc",
        "image_url": "image",
        "thumbnail_url": "thumb",
        "photographer_name": "John",
        "photographer_url": "profile",
    }

    async def fake_fetch(api_key, city, country):
        return fetched_data

    monkeypatch.setattr(
        location_image_service,
        "fetch_from_unsplash",
        fake_fetch,
    )

    image = await location_image_service.get_location_image(db_session, "Vienna", "Austria")
    assert image.unsplash_id == "abc"

    # subsequent call should return cached result
    cached = await location_image_service.get_location_image(db_session, "Vienna", "Austria")
    assert cached.id == image.id

    # remove API key -> graceful fallback
    db_session.query(SystemSettings).delete()
    db_session.commit()
    assert await location_image_service.get_location_image(db_session, "Vienna", "Austria") is None


def test_clear_expired_cache(db_session):
    now = datetime.utcnow()
    image = LocationImage(
        city=None,
        country="Austria",
        unsplash_id="old",
        image_url="image",
        thumbnail_url="thumb",
        fetched_at=now - timedelta(days=10),
        expires_at=now - timedelta(days=1),
    )
    db_session.add(image)
    db_session.commit()

    deleted = location_image_service.clear_expired_cache(db_session)
    assert deleted == 1


def test_get_attribution_html(db_session):
    now = datetime.utcnow()
    image = LocationImage(
        city="Vienna",
        country="Austria",
        unsplash_id="abc",
        image_url="image",
        thumbnail_url="thumb",
        photographer_name="John",
        photographer_url="https://unsplash.com/john",
        fetched_at=now,
        expires_at=now + timedelta(days=1),
    )
    html = location_image_service.get_attribution_html(image)
    assert "Unsplash" in html
