# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for photo_service."""

import datetime
from typing import Any

import httpx
import pytest
from sqlalchemy.orm import Session

from src.models import Company, Event, PhotoReference, User
from src.models.enums import CompanyType
from src.schemas.photo import PhotoReferenceCreate, PhotoReferenceUpdate
from src.services import photo_service
from src.services.photo_service import PhotoSearchCriteria

VIENNA = (48.2, 16.4)
PAST = (datetime.date(2025, 3, 10), datetime.date(2025, 3, 14))


def _asset(asset_id: str, taken: str, lat: float, lon: float) -> dict[str, Any]:
    return {
        "id": asset_id,
        "originalFileName": f"{asset_id}.jpg",
        "exifInfo": {"dateTimeOriginal": taken, "latitude": lat, "longitude": lon},
    }


IN_VIENNA = _asset("vienna", "2025-03-11T10:00:00", 48.21, 16.37)
IN_SYDNEY = _asset("sydney", "2025-03-11T10:00:00", -33.9, 151.2)
LAST_YEAR = _asset("old", "2024-03-11T10:00:00", 48.21, 16.37)


class FakeImmich:
    """Records the searches it receives and serves known assets."""

    search_radius_km = 50

    def __init__(self, assets: list[dict[str, Any]]) -> None:
        self.assets = {asset["id"]: asset for asset in assets}
        self.searches: list[dict[str, Any]] = []
        self.info_calls: list[str] = []

    async def search_by_location_and_date(self, **kwargs: Any) -> list[dict]:
        self.searches.append({"kind": "location", **kwargs})
        return list(self.assets.values())

    async def search_by_date_only(self, **kwargs: Any) -> list[dict]:
        self.searches.append({"kind": "date", **kwargs})
        return list(self.assets.values())

    async def get_asset_info(self, asset_id: str) -> dict[str, Any]:
        self.info_calls.append(asset_id)
        if asset_id not in self.assets:
            request = httpx.Request("GET", f"http://immich/api/assets/{asset_id}")
            raise httpx.HTTPStatusError(
                "not found", request=request, response=httpx.Response(404)
            )
        return self.assets[asset_id]


@pytest.fixture
def user(test_user: User) -> User:
    return test_user


def _event(
    db: Session,
    user: User,
    dates: tuple[datetime.date, datetime.date] = PAST,
    location: tuple[float, float] | None = VIENNA,
) -> Event:
    company = Company(name="Acme", type=CompanyType.EMPLOYER)
    db.add(company)
    db.flush()
    lat, lon = location if location else (None, None)
    event = Event(
        user_id=user.id,
        company_id=company.id,
        name="Trip",
        start_date=dates[0],
        end_date=dates[1],
        latitude=lat,
        longitude=lon,
    )
    db.add(event)
    db.commit()
    return event


def _future() -> tuple[datetime.date, datetime.date]:
    start = datetime.date.today() + datetime.timedelta(days=10)
    return start, start + datetime.timedelta(days=2)


def test_criteria_cover_event_dates_with_a_day_of_slack(
    db_session: Session, user: User
) -> None:
    event = _event(db_session, user)

    criteria = photo_service.build_search_criteria(event, date_only=False)

    assert criteria == PhotoSearchCriteria(
        start=datetime.datetime(2025, 3, 10),
        end=datetime.datetime.combine(datetime.date(2025, 3, 15), datetime.time.max),
        latitude=48.2,
        longitude=16.4,
    )


def test_available_searches_depend_on_location_and_start(
    db_session: Session, user: User
) -> None:
    past_with_location = _event(db_session, user)
    past_without_location = _event(db_session, user, location=None)
    future_with_location = _event(db_session, user, dates=_future())
    future_without_location = _event(db_session, user, _future(), None)

    kinds = [
        [c.latitude is not None for c in photo_service.event_search_criteria(e)]
        for e in (
            past_with_location,
            past_without_location,
            future_with_location,
            future_without_location,
        )
    ]

    assert kinds == [[True, False], [False], [True], []]


async def test_search_uses_the_criteria_and_flags_linked_assets(
    db_session: Session, user: User
) -> None:
    event = _event(db_session, user)
    db_session.add(PhotoReference(event_id=event.id, immich_asset_id="vienna"))
    db_session.commit()
    provider = FakeImmich([IN_VIENNA])
    location = photo_service.build_search_criteria(event, date_only=False)
    by_date = photo_service.build_search_criteria(event, date_only=True)
    assert location is not None
    assert by_date is not None

    (photo,) = await photo_service.search_photos(db_session, event, provider, location)
    await photo_service.search_photos(db_session, event, provider, by_date)

    assert photo.id == "vienna"
    assert photo.is_linked is True
    assert photo.thumbnail_url == f"/api/v1/events/{event.id}/photos/vienna/thumbnail"
    assert provider.searches == [
        {
            "kind": "location",
            "latitude": location.latitude,
            "longitude": location.longitude,
            "start_date": location.start,
            "end_date": location.end,
        },
        {"kind": "date", "start_date": by_date.start, "end_date": by_date.end},
    ]


@pytest.mark.parametrize(
    ("asset_id", "dates", "location", "expected"),
    [
        ("vienna", PAST, VIENNA, True),
        ("sydney", PAST, VIENNA, True),  # past event: the date search finds it
        ("old", PAST, VIENNA, False),
        ("sydney", PAST, None, True),
        ("missing", PAST, VIENNA, False),
    ],
)
async def test_asset_belongs_to_past_event_by_search_criteria(
    db_session: Session,
    user: User,
    asset_id: str,
    dates: tuple[datetime.date, datetime.date],
    location: tuple[float, float] | None,
    expected: bool,
) -> None:
    event = _event(db_session, user, dates, location)
    provider = FakeImmich([IN_VIENNA, IN_SYDNEY, LAST_YEAR])

    assert (
        await photo_service.asset_belongs_to_event(
            db_session, event, asset_id, provider
        )
        is expected
    )


async def test_future_event_accepts_only_assets_near_its_location(
    db_session: Session, user: User
) -> None:
    start, end = _future()
    event = _event(db_session, user, (start, end))
    taken = f"{start.isoformat()}T09:00:00Z"
    near = _asset("near", taken, 48.21, 16.37)
    far = _asset("far", taken, -33.9, 151.2)
    provider = FakeImmich([near, far])

    assert await photo_service.asset_belongs_to_event(
        db_session, event, "near", provider
    )
    assert not await photo_service.asset_belongs_to_event(
        db_session, event, "far", provider
    )


async def test_linked_asset_belongs_without_immich_lookup(
    db_session: Session, user: User
) -> None:
    event = _event(db_session, user, _future(), None)
    db_session.add(PhotoReference(event_id=event.id, immich_asset_id="kept"))
    db_session.commit()
    provider = FakeImmich([])

    assert await photo_service.asset_belongs_to_event(
        db_session, event, "kept", provider
    )
    assert provider.info_calls == []


def test_reference_create_update_and_delete(db_session: Session, user: User) -> None:
    event = _event(db_session, user)

    reference = photo_service.add_photo_reference(
        db_session,
        event,
        PhotoReferenceCreate(immich_asset_id="vienna", caption="Dome", latitude=48.2),
    )
    photo_service.update_photo_reference(
        db_session, reference, PhotoReferenceUpdate(include_in_report=True)
    )

    stored = photo_service.get_photo_reference(db_session, event, reference.id)
    assert stored is not None
    assert (stored.caption, stored.include_in_report, stored.latitude) == (
        "Dome",
        True,
        48.2,
    )
    assert photo_service.list_photo_references(db_session, event) == [stored]

    photo_service.delete_photo_reference(db_session, stored)

    assert photo_service.list_photo_references(db_session, event) == []


def test_duplicate_reference_is_rejected(db_session: Session, user: User) -> None:
    event = _event(db_session, user)
    data = PhotoReferenceCreate(immich_asset_id="vienna")
    photo_service.add_photo_reference(db_session, event, data)

    with pytest.raises(photo_service.PhotoAlreadyLinkedError):
        photo_service.add_photo_reference(db_session, event, data)


def test_reference_of_another_event_is_not_found(
    db_session: Session, user: User
) -> None:
    event = _event(db_session, user)
    other = _event(db_session, user)
    reference = photo_service.add_photo_reference(
        db_session, event, PhotoReferenceCreate(immich_asset_id="vienna")
    )

    assert photo_service.get_photo_reference(db_session, other, reference.id) is None
