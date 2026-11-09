# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Characterization of the holiday calendar endpoints."""

import uuid
from typing import Any

from fastapi.testclient import TestClient

from src.models import User
from tests.conftest import LoginHelper

BASE = "/api/v1/holiday-calendars"


def _create(client: TestClient, **overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "country_code": "at",
        "subdivision": "w",
        "display_label": "AT-W",
    }
    data.update(overrides)
    response = client.post(BASE, json=data)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_uppercases_codes(authenticated_client: TestClient) -> None:
    """Country and subdivision codes are stored upper case."""
    calendar = _create(authenticated_client)

    assert calendar["country_code"] == "AT"
    assert calendar["subdivision"] == "W"
    assert calendar["display_label"] == "AT-W"


def test_crud_roundtrip(authenticated_client: TestClient) -> None:
    """A calendar can be listed, read, relabelled and deleted."""
    calendar = _create(authenticated_client)
    url = f"{BASE}/{calendar['id']}"

    assert [c["id"] for c in authenticated_client.get(BASE).json()] == [calendar["id"]]
    assert authenticated_client.get(url).json()["id"] == calendar["id"]
    updated = authenticated_client.put(url, json={"display_label": "Vienna"})
    assert updated.status_code == 200
    assert updated.json()["display_label"] == "Vienna"
    assert authenticated_client.delete(url).status_code == 204
    assert authenticated_client.get(url).status_code == 404


def test_unknown_id_is_not_found(authenticated_client: TestClient) -> None:
    """An unknown calendar id is a 404 for get, update and delete."""
    url = f"{BASE}/{uuid.uuid4()}"

    assert authenticated_client.get(url).status_code == 404
    assert authenticated_client.put(url, json={"display_label": "x"}).status_code == 404
    assert authenticated_client.delete(url).status_code == 404


def test_create_validation(authenticated_client: TestClient) -> None:
    """A country code that is not two letters or an empty label is a 422."""
    short = authenticated_client.post(
        BASE, json={"country_code": "A", "display_label": "x"}
    )
    blank = authenticated_client.post(
        BASE, json={"country_code": "AT", "display_label": ""}
    )

    assert short.status_code == 422
    assert blank.status_code == 422


def test_calendars_are_private_to_their_user(
    client: TestClient,
    login: LoginHelper,
    authenticated_client: TestClient,
    second_user: User,
) -> None:
    """Another user neither lists nor reads nor deletes the calendar."""
    calendar = _create(authenticated_client)
    other = login(client, second_user)
    url = f"{BASE}/{calendar['id']}"

    assert other.get(BASE).json() == []
    assert other.get(url).status_code == 404
    assert other.delete(url).status_code == 404


def test_countries_lists_austria_with_subdivisions(
    authenticated_client: TestClient,
) -> None:
    """The supported countries include Austria with its states."""
    response = authenticated_client.get(f"{BASE}/countries")

    assert response.status_code == 200
    countries = {c["code"]: c for c in response.json()["countries"]}
    assert "AT" in countries
    assert countries["AT"]["subdivisions"]


def test_preview_returns_holidays_of_the_year(
    authenticated_client: TestClient,
) -> None:
    """The preview lists the national holidays of the requested year."""
    response = authenticated_client.get(
        f"{BASE}/preview", params={"country_code": "at", "year": 2026}
    )

    assert response.status_code == 200
    dates = {h["date"] for h in response.json()}
    assert "2026-12-25" in dates
    assert "2026-01-01" in dates


def test_preview_validates_query(authenticated_client: TestClient) -> None:
    """A malformed country code or an out-of-range year is a 422."""
    assert (
        authenticated_client.get(
            f"{BASE}/preview", params={"country_code": "AUT"}
        ).status_code
        == 422
    )
    assert (
        authenticated_client.get(
            f"{BASE}/preview", params={"country_code": "AT", "year": 1800}
        ).status_code
        == 422
    )


def test_holidays_for_configured_calendars(
    authenticated_client: TestClient,
) -> None:
    """The range endpoint returns holidays of the user's calendars only."""
    params = {"start_date": "2026-12-20", "end_date": "2026-12-31"}
    assert authenticated_client.get(f"{BASE}/holidays", params=params).json() == {
        "holidays": []
    }

    _create(authenticated_client, subdivision=None, display_label="AT")
    response = authenticated_client.get(f"{BASE}/holidays", params=params)

    assert response.status_code == 200
    found = response.json()["holidays"]
    assert any(h["date"] == "2026-12-25" and h["display_label"] == "AT" for h in found)


def test_holidays_requires_date_range(authenticated_client: TestClient) -> None:
    """Missing start or end date is a 422."""
    response = authenticated_client.get(
        f"{BASE}/holidays", params={"start_date": "2026-01-01"}
    )

    assert response.status_code == 422


def test_requires_login(client: TestClient) -> None:
    """An anonymous caller is rejected."""
    assert client.get(BASE).status_code == 401
    assert client.get(f"{BASE}/countries").status_code == 401


def test_preview_unknown_country_or_subdivision_is_unprocessable(
    authenticated_client: TestClient,
) -> None:
    """An unknown country or subdivision is a 422, not an empty list."""
    unknown_country = authenticated_client.get(
        f"{BASE}/preview", params={"country_code": "XX"}
    )
    unknown_subdivision = authenticated_client.get(
        f"{BASE}/preview", params={"country_code": "AT", "subdivision": "ZZ"}
    )

    assert unknown_country.status_code == 422
    assert unknown_subdivision.status_code == 422


def test_create_unknown_country_or_subdivision_is_unprocessable(
    authenticated_client: TestClient,
) -> None:
    """A calendar for a region the library does not know is not stored."""
    unknown_country = authenticated_client.post(
        BASE, json={"country_code": "XX", "display_label": "XX"}
    )
    unknown_subdivision = authenticated_client.post(
        BASE,
        json={"country_code": "AT", "subdivision": "ZZ", "display_label": "AT-ZZ"},
    )

    assert unknown_country.status_code == 422
    assert unknown_subdivision.status_code == 422
    assert authenticated_client.get(BASE).json() == []
