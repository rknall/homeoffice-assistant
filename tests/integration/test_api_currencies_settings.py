# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Characterization of the currency list and the settings endpoints."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from src.models import User
from src.services.currency_service import Currency, CurrencyServiceError
from tests.conftest import LoginHelper, UserFactory

SUPPORTED = "src.services.currency_service.CurrencyService.get_supported_currencies"


def test_currencies_returns_supported_list(authenticated_client: TestClient) -> None:
    """The endpoint returns the provider's currencies as code and name."""
    supported = [Currency(code="EUR", name="Euro"), Currency(code="USD", name="Dollar")]
    with patch(SUPPORTED, new=AsyncMock(return_value=supported)):
        response = authenticated_client.get("/api/v1/currencies")

    assert response.status_code == 200
    assert response.json() == [
        {"code": "EUR", "name": "Euro"},
        {"code": "USD", "name": "Dollar"},
    ]


def test_currencies_provider_failure_is_503(authenticated_client: TestClient) -> None:
    """A provider failure becomes a 503 with a category, not the raw text."""
    error = CurrencyServiceError("boom host.internal")
    error.__cause__ = httpx.ConnectError("boom host.internal")
    with patch(SUPPORTED, new=AsyncMock(side_effect=error)):
        response = authenticated_client.get("/api/v1/currencies")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Currency service unavailable: server unreachable"
    )
    assert "host.internal" not in response.text


def test_currencies_requires_login(client: TestClient) -> None:
    """An anonymous caller is rejected."""
    assert client.get("/api/v1/currencies").status_code == 401


def test_locale_defaults(authenticated_client: TestClient) -> None:
    """Locale reads need login only and have defaults."""
    default = authenticated_client.get("/api/v1/settings/locale")
    assert default.status_code == 200
    assert default.json() == {
        "date_format": "YYYY-MM-DD",
        "time_format": "24h",
        "timezone": "UTC",
    }


def test_admin_updates_locale_partially(admin_client: TestClient) -> None:
    """A partial update changes only the given fields."""
    response = admin_client.put(
        "/api/v1/settings/locale", json={"date_format": "DD.MM.YYYY"}
    )

    assert response.status_code == 200
    assert response.json()["date_format"] == "DD.MM.YYYY"
    assert response.json()["time_format"] == "24h"
    assert admin_client.get("/api/v1/settings/locale").json()["date_format"] == (
        "DD.MM.YYYY"
    )


def test_locale_rejects_unknown_format(admin_client: TestClient) -> None:
    """A date format outside the allowed set is a 422."""
    response = admin_client.put(
        "/api/v1/settings/locale", json={"date_format": "YY/DD"}
    )

    assert response.status_code == 422


def test_member_cannot_write_settings(authenticated_client: TestClient) -> None:
    """A Member may read but not write locale and currency settings."""
    locale = authenticated_client.put(
        "/api/v1/settings/locale", json={"time_format": "12h"}
    )
    currency = authenticated_client.put(
        "/api/v1/settings/currency", json={"base_currency": "USD"}
    )

    assert locale.status_code == 403
    assert currency.status_code == 403


def test_currency_default_and_update(admin_client: TestClient) -> None:
    """The base currency defaults to EUR and an update is read back."""
    assert admin_client.get("/api/v1/settings/currency").json() == {
        "base_currency": "EUR"
    }

    updated = admin_client.put(
        "/api/v1/settings/currency", json={"base_currency": "USD"}
    )

    assert updated.status_code == 200
    assert updated.json() == {"base_currency": "USD"}
    assert admin_client.get("/api/v1/settings/currency").json() == {
        "base_currency": "USD"
    }


@pytest.mark.parametrize("value", ["US", "USDX", "U5D"])
def test_currency_rejects_malformed_code(admin_client: TestClient, value: str) -> None:
    """A base currency that is not three letters is a 422."""
    response = admin_client.put(
        "/api/v1/settings/currency", json={"base_currency": value}
    )

    assert response.status_code == 422


def test_company_scoped_user_reads_settings(
    client: TestClient, login: LoginHelper, company_viewer_user: User
) -> None:
    """Every page needs these reads, so a company-only user may read them."""
    viewer = login(client, company_viewer_user)

    assert viewer.get("/api/v1/settings/locale").status_code == 200
    assert viewer.get("/api/v1/settings/currency").status_code == 200


def test_settings_require_login(client: TestClient) -> None:
    """An anonymous caller is rejected."""
    assert client.get("/api/v1/settings/locale").status_code == 401
    assert client.get("/api/v1/settings/currency").status_code == 401
    assert (
        client.put(
            "/api/v1/settings/currency", json={"base_currency": "USD"}
        ).status_code
        == 401
    )


def test_user_without_role_cannot_write(
    client: TestClient, login: LoginHelper, user_factory: UserFactory
) -> None:
    """A user without roles gets 403 on a write, not 401."""
    user = user_factory("norole", roles=())
    response = login(client, user).put(
        "/api/v1/settings/currency", json={"base_currency": "USD"}
    )

    assert response.status_code == 403
