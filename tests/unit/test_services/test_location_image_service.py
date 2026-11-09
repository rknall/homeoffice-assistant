# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for location_image_service."""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.integrations.base import ImageSearchProvider
from src.models import LocationImage, SystemSettings
from src.models.enums import IntegrationType
from src.schemas.integration import IntegrationConfigCreate
from src.services import integration_service, location_image_service
from src.utils.time import utc_now


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
    now = utc_now()
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


PHOTO = {
    "id": "abc",
    "urls": {"regular": "image", "small": "thumb"},
    "user": {
        "name": "John",
        "username": "john",
        "portfolio_url": "https://example.com/john",
    },
}


def _provider(results):
    provider = MagicMock(spec=ImageSearchProvider)
    provider.close = AsyncMock()
    provider.search_images = AsyncMock(return_value={"results": results})
    return provider


def _unsplash_config(db_session, user_id, active=True):
    config = integration_service.create_integration_config(
        db_session,
        IntegrationConfigCreate(
            integration_type=IntegrationType.UNSPLASH,
            name="unsplash",
            config={"access_key": "key"},
        ),
        user_id,
    )
    config.is_active = active
    db_session.commit()
    return config


@pytest.mark.asyncio
async def test_fetch_from_unsplash_maps_first_result():
    provider = _provider([PHOTO])

    data = await location_image_service.fetch_from_unsplash(
        provider, "Vienna", "Austria"
    )

    assert data["unsplash_id"] == "abc"
    assert data["photographer_url"] == "https://example.com/john"
    query = provider.search_images.call_args.args[0]
    assert query == "Vienna Austria landmark skyline"


@pytest.mark.asyncio
async def test_fetch_from_unsplash_no_result_or_error():
    assert (
        await location_image_service.fetch_from_unsplash(_provider([]), None, "Austria")
        is None
    )
    failing = _provider([])
    failing.search_images = AsyncMock(side_effect=RuntimeError("boom"))
    assert (
        await location_image_service.fetch_from_unsplash(failing, None, "Austria")
        is None
    )


@pytest.mark.asyncio
async def test_get_location_image_uses_active_integration(
    monkeypatch, db_session, test_user
):
    _unsplash_config(db_session, test_user.id)
    provider = _provider([PHOTO])
    monkeypatch.setattr(
        integration_service, "create_provider_instance", lambda config: provider
    )

    image = await location_image_service.get_location_image(
        db_session, "Vienna", "Austria"
    )
    assert image.unsplash_id == "abc"
    provider.close.assert_awaited()

    # subsequent call returns the cached result without another search
    cached = await location_image_service.get_location_image(
        db_session, "Vienna", "Austria"
    )
    assert cached.id == image.id
    assert provider.search_images.await_count == 1


@pytest.mark.asyncio
async def test_get_location_image_without_integration_reads_no_setting(
    monkeypatch, db_session, test_user
):
    # A plaintext key in system_settings is ignored
    db_session.add(SystemSettings(key="unsplash_api_key", value="plain"))
    db_session.commit()
    calls = []
    monkeypatch.setattr(
        integration_service,
        "create_provider_instance",
        lambda config: calls.append(config),
    )

    assert (
        await location_image_service.get_location_image(db_session, "Vienna", "Austria")
        is None
    )
    assert calls == []

    # An inactive integration counts as none
    _unsplash_config(db_session, test_user.id, active=False)
    assert (
        await location_image_service.get_location_image(db_session, "Vienna", "Austria")
        is None
    )
    assert calls == []


def test_clear_expired_cache(db_session):
    now = utc_now()
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
    now = utc_now()
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


def test_attribution_html_escapes_photographer_name(db_session):
    now = utc_now()
    image = LocationImage(
        city="Vienna",
        country="Austria",
        unsplash_id="esc",
        image_url="image",
        thumbnail_url="thumb",
        photographer_name='<b>"Eve"</b>',
        photographer_url="https://unsplash.com/eve",
        fetched_at=now,
        expires_at=now + timedelta(days=1),
    )
    result = location_image_service.get_attribution_html(image)
    assert "<b>" not in result
    assert "&lt;b&gt;&quot;Eve&quot;&lt;/b&gt;" in result
