# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Characterization of the Immich photo routes with a mocked provider."""

import datetime
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models import Company, Event, User
from src.models.enums import CompanyType, IntegrationType
from src.services import integration_service
from tests.conftest import LoginHelper, UserFactory

EVENTS = "/api/v1/events"
ASSET = {
    "id": "asset-1",
    "originalFileName": "IMG_1.jpg",
    "exifInfo": {
        "dateTimeOriginal": "2025-03-11T10:00:00",
        "latitude": 48.2,
        "longitude": 16.4,
        "city": "Vienna",
        "country": "Austria",
    },
    "_distance_km": 1.5,
}
UNRELATED = {
    "id": "elsewhere",
    "exifInfo": {
        "dateTimeOriginal": "2019-07-01T12:00:00",
        "latitude": -33.9,
        "longitude": 151.2,
    },
}


class FakeImmich:
    """Stands in for ImmichProvider and records calls."""

    search_radius_km = 50

    def __init__(self, fail_thumbnail: bool = False) -> None:
        self.closed = False
        self.calls: list[str] = []
        self.fail_thumbnail = fail_thumbnail

    async def search_by_location_and_date(self, **kwargs: Any) -> list[dict]:
        self.calls.append("location")
        return [ASSET]

    async def search_by_date_only(self, **kwargs: Any) -> list[dict]:
        self.calls.append("date")
        return [ASSET]

    async def get_asset_info(self, asset_id: str) -> dict:
        self.calls.append(f"info:{asset_id}")
        return ASSET if asset_id == ASSET["id"] else {**UNRELATED, "id": asset_id}

    async def get_asset_thumbnail(self, asset_id: str) -> tuple[bytes, str]:
        if self.fail_thumbnail:
            raise httpx.ConnectError("immich down")
        return b"jpeg-bytes", "image/jpeg"

    async def close(self) -> None:
        self.closed = True


def _use_provider(monkeypatch: pytest.MonkeyPatch, provider: FakeImmich) -> None:
    """Make open_active_provider yield the fake for Immich and close it."""

    @asynccontextmanager
    async def open_active_provider(
        db: Session, integration_type: IntegrationType
    ) -> AsyncIterator[FakeImmich]:
        assert integration_type == IntegrationType.IMMICH
        try:
            yield provider
        finally:
            await provider.close()

    monkeypatch.setattr(
        integration_service, "open_active_provider", open_active_provider
    )


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeImmich:
    provider = FakeImmich()
    _use_provider(monkeypatch, provider)
    return provider


def _event(db: Session, user: User, **fields: Any) -> Event:
    company = Company(name="Acme", type=CompanyType.EMPLOYER)
    db.add(company)
    db.flush()
    values: dict[str, Any] = {
        "user_id": user.id,
        "company_id": company.id,
        "name": "Trip",
        "start_date": datetime.date(2025, 3, 10),
        "end_date": datetime.date(2025, 3, 14),
        "latitude": 48.2,
        "longitude": 16.4,
    }
    values.update(fields)
    event = Event(**values)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@pytest.fixture
def event(db_session: Session, test_user: User) -> Event:
    return _event(db_session, test_user)


def test_photos_search_maps_assets(
    authenticated_client: TestClient, event: Event, fake: FakeImmich
) -> None:
    response = authenticated_client.get(f"{EVENTS}/{event.id}/photos")

    assert response.status_code == 200
    (photo,) = response.json()
    assert photo["id"] == "asset-1"
    assert photo["original_filename"] == "IMG_1.jpg"
    assert photo["city"] == "Vienna"
    assert photo["distance_km"] == 1.5
    assert photo["is_linked"] is False
    assert photo["thumbnail_url"] == (f"{EVENTS}/{event.id}/photos/asset-1/thumbnail")
    assert fake.closed is True


def test_photos_without_location_is_empty(
    authenticated_client: TestClient,
    db_session: Session,
    test_user: User,
    fake: FakeImmich,
) -> None:
    event = _event(db_session, test_user, latitude=None, longitude=None)

    response = authenticated_client.get(f"{EVENTS}/{event.id}/photos")

    assert response.json() == []
    assert fake.calls == []


def test_photos_without_integration_is_400(
    authenticated_client: TestClient, event: Event
) -> None:
    response = authenticated_client.get(f"{EVENTS}/{event.id}/photos")

    assert response.status_code == 400
    assert "not configured" in response.json()["detail"]


def test_photos_by_date_only_for_past_events(
    authenticated_client: TestClient,
    db_session: Session,
    test_user: User,
    event: Event,
    fake: FakeImmich,
) -> None:
    future = _event(
        db_session,
        test_user,
        start_date=datetime.date.today() + datetime.timedelta(days=5),
        end_date=datetime.date.today() + datetime.timedelta(days=6),
    )

    past = authenticated_client.get(f"{EVENTS}/{event.id}/photos/by-date")
    soon = authenticated_client.get(f"{EVENTS}/{future.id}/photos/by-date")

    assert past.status_code == 200
    assert past.json()[0]["distance_km"] is None
    assert fake.calls == ["date"]
    assert soon.status_code == 400


def test_photos_by_date_without_integration_is_400(
    authenticated_client: TestClient, event: Event
) -> None:
    response = authenticated_client.get(f"{EVENTS}/{event.id}/photos/by-date")

    assert response.status_code == 400


def test_reference_lifecycle_and_linked_flag(
    authenticated_client: TestClient, event: Event, fake: FakeImmich
) -> None:
    base = f"{EVENTS}/{event.id}/photos"

    created = authenticated_client.post(
        base, json={"immich_asset_id": "asset-1", "caption": "Dome"}
    )
    assert created.status_code == 200
    ref = created.json()
    assert ref["caption"] == "Dome"
    assert ref["include_in_report"] is False

    assert authenticated_client.get(base).json()[0]["is_linked"] is True
    assert [r["id"] for r in authenticated_client.get(f"{base}/references").json()] == [
        ref["id"]
    ]

    updated = authenticated_client.put(
        f"{base}/{ref['id']}", json={"caption": "Cathedral", "include_in_report": True}
    )
    assert updated.status_code == 200
    assert updated.json()["caption"] == "Cathedral"
    assert updated.json()["include_in_report"] is True

    deleted = authenticated_client.delete(f"{base}/{ref['id']}")
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert authenticated_client.get(f"{base}/references").json() == []


def test_duplicate_reference_is_400(
    authenticated_client: TestClient, event: Event
) -> None:
    url = f"{EVENTS}/{event.id}/photos"
    body = {"immich_asset_id": "asset-1"}
    authenticated_client.post(url, json=body)

    assert authenticated_client.post(url, json=body).status_code == 400


def test_unknown_reference_is_404(
    authenticated_client: TestClient, event: Event
) -> None:
    url = f"{EVENTS}/{event.id}/photos/{uuid.uuid4()}"

    assert authenticated_client.put(url, json={"caption": "x"}).status_code == 404
    assert authenticated_client.delete(url).status_code == 404


def test_reference_of_another_event_is_404(
    authenticated_client: TestClient,
    db_session: Session,
    test_user: User,
    event: Event,
) -> None:
    other = _event(db_session, test_user, name="Other")
    ref = authenticated_client.post(
        f"{EVENTS}/{event.id}/photos", json={"immich_asset_id": "a"}
    ).json()

    response = authenticated_client.delete(f"{EVENTS}/{other.id}/photos/{ref['id']}")

    assert response.status_code == 404


def test_other_users_event_is_404(
    client: TestClient,
    user_factory: UserFactory,
    login: LoginHelper,
    event: Event,
    fake: FakeImmich,
) -> None:
    stranger = login(client, user_factory("stranger"))
    base = f"{EVENTS}/{event.id}/photos"

    assert stranger.get(base).status_code == 404
    assert stranger.post(base, json={"immich_asset_id": "a"}).status_code == 404
    assert stranger.get(f"{base}/asset-1/thumbnail").status_code == 404


def test_viewer_reads_but_cannot_write(
    client: TestClient,
    db_session: Session,
    company_viewer_user: User,
    viewer_company: Company,
    login: LoginHelper,
    fake: FakeImmich,
) -> None:
    event = _event(db_session, company_viewer_user, name="Viewer trip")
    event.company_id = viewer_company.id
    db_session.commit()
    viewer = login(client, company_viewer_user)
    base = f"{EVENTS}/{event.id}/photos"

    assert viewer.get(f"{base}/references").status_code == 200
    assert viewer.post(base, json={"immich_asset_id": "a"}).status_code == 403


def test_thumbnail_is_proxied(
    authenticated_client: TestClient, event: Event, fake: FakeImmich
) -> None:
    response = authenticated_client.get(f"{EVENTS}/{event.id}/photos/asset-1/thumbnail")

    assert response.status_code == 200
    assert response.content == b"jpeg-bytes"
    assert response.headers["content-type"] == "image/jpeg"
    assert fake.closed is True


def test_thumbnail_of_unrelated_asset_is_404(
    authenticated_client: TestClient, event: Event, fake: FakeImmich
) -> None:
    response = authenticated_client.get(
        f"{EVENTS}/{event.id}/photos/elsewhere/thumbnail"
    )

    assert response.status_code == 404
    assert fake.calls == ["info:elsewhere"]
    assert fake.closed is True


def test_thumbnail_of_linked_asset_is_200_without_immich_lookup(
    authenticated_client: TestClient, event: Event, fake: FakeImmich
) -> None:
    base = f"{EVENTS}/{event.id}/photos"
    authenticated_client.post(base, json={"immich_asset_id": "elsewhere"})

    response = authenticated_client.get(f"{base}/elsewhere/thumbnail")

    assert response.status_code == 200
    assert response.content == b"jpeg-bytes"
    assert fake.calls == []


def test_thumbnail_of_asset_linked_to_another_event_is_404(
    authenticated_client: TestClient,
    db_session: Session,
    test_user: User,
    event: Event,
    fake: FakeImmich,
) -> None:
    other = _event(db_session, test_user, name="Other")
    authenticated_client.post(
        f"{EVENTS}/{other.id}/photos", json={"immich_asset_id": "elsewhere"}
    )

    response = authenticated_client.get(
        f"{EVENTS}/{event.id}/photos/elsewhere/thumbnail"
    )

    assert response.status_code == 404


def test_thumbnail_failure_is_502(
    authenticated_client: TestClient,
    event: Event,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = FakeImmich(fail_thumbnail=True)
    _use_provider(monkeypatch, provider)

    response = authenticated_client.get(f"{EVENTS}/{event.id}/photos/asset-1/thumbnail")

    assert response.status_code == 502
    assert provider.closed is True


def test_thumbnail_without_integration_is_400(
    authenticated_client: TestClient, event: Event
) -> None:
    response = authenticated_client.get(f"{EVENTS}/{event.id}/photos/asset-1/thumbnail")

    assert response.status_code == 400


def test_location_image_without_country_is_null(
    authenticated_client: TestClient, event: Event
) -> None:
    response = authenticated_client.get(f"{EVENTS}/{event.id}/location-image")

    assert response.status_code == 200
    assert response.json() is None
