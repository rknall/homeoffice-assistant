# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for the location autocomplete endpoint."""

import httpx
import pytest

URL = "/api/v1/locations/autocomplete"


@pytest.fixture
def mock_nominatim(monkeypatch):
    """Patch the Nominatim HTTP call; returns a setter for the response."""
    state = {"response": None, "error": None}

    async def fake_get(self, url, **kwargs):
        if state["error"]:
            raise state["error"]
        return state["response"]

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    return state


def _response(status: int, payload) -> httpx.Response:
    return httpx.Response(
        status, json=payload, request=httpx.Request("GET", "https://example.test")
    )


def test_requires_auth(client):
    assert client.get(URL, params={"q": "Berlin"}).status_code == 401


def test_http_error_returns_502(authenticated_client, mock_nominatim):
    mock_nominatim["error"] = httpx.ConnectError("boom")
    resp = authenticated_client.get(URL, params={"q": "Berlin"})
    assert resp.status_code == 502


def test_upstream_error_status_returns_502(authenticated_client, mock_nominatim):
    mock_nominatim["response"] = _response(500, {})
    resp = authenticated_client.get(URL, params={"q": "Berlin"})
    assert resp.status_code == 502


def test_success_returns_suggestions(authenticated_client, mock_nominatim):
    mock_nominatim["response"] = _response(
        200,
        [
            {
                "lat": "52.52",
                "lon": "13.40",
                "display_name": "Berlin, Germany",
                "address": {
                    "city": "Berlin",
                    "country": "Germany",
                    "country_code": "de",
                },
            },
            {"lat": "1", "lon": "2", "address": {}},
        ],
    )
    resp = authenticated_client.get(URL, params={"q": "Berlin"})
    assert resp.status_code == 200
    assert resp.json() == [
        {
            "city": "Berlin",
            "country": "Germany",
            "country_code": "DE",
            "latitude": 52.52,
            "longitude": 13.4,
            "display_name": "Berlin, Germany",
        }
    ]
