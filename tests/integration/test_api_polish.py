# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""API polish: status codes, download headers, generic errors, currency codes."""

import datetime
import smtplib
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import unquote

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from src.api.v1._http import content_disposition
from src.integrations.base import EmailProvider
from src.models import Company, Event, User
from src.models.enums import CompanyType
from src.schemas.expense import ExpenseCreate

EVENTS = "/api/v1/events"
INTEGRATIONS = "/api/v1/integrations"
NEW_USER = {
    "username": "polished",
    "email": "polished@example.com",
    "password": "polishedpass123",
}


@pytest.fixture
def event(db_session: Session, test_user: User) -> Event:
    """An event of the logged-in test user."""
    company = Company(name="Acme", type=CompanyType.EMPLOYER)
    db_session.add(company)
    db_session.flush()
    event = Event(
        user_id=test_user.id,
        company_id=company.id,
        name="Trip",
        start_date=datetime.date(2025, 3, 10),
        end_date=datetime.date(2025, 3, 14),
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    return event


def test_create_user_is_201(admin_client: TestClient) -> None:
    """Creating a user answers 201 Created."""
    response = admin_client.post("/api/v1/users", json=NEW_USER)

    assert response.status_code == 201
    assert response.json()["username"] == "polished"


def test_photo_reference_delete_is_204(
    authenticated_client: TestClient, event: Event
) -> None:
    """Deleting a photo reference answers 204 without a body."""
    base = f"{EVENTS}/{event.id}/photos"
    ref = authenticated_client.post(base, json={"immich_asset_id": "a"}).json()

    response = authenticated_client.delete(f"{base}/{ref['id']}")

    assert response.status_code == 204
    assert response.content == b""


def test_content_disposition_uses_rfc_5987() -> None:
    """A non-ASCII name gets an ASCII fallback and a percent-encoded filename*."""
    header = content_disposition("Bericht März.pdf")

    assert header.startswith("attachment; ")
    assert 'filename="Bericht M_rz.pdf"' in header
    encoded = header.split("filename*=UTF-8''", 1)[1]
    assert "%C3%A4" in encoded
    assert unquote(encoded) == "Bericht März.pdf"


def test_content_disposition_neutralises_quotes_and_newlines() -> None:
    """Quotes, backslashes and control characters cannot break out of the header."""
    header = content_disposition('a"b\\c\r\nd.zip', "inline")

    assert header.startswith("inline; ")
    fallback = header.split('filename="', 1)[1].split('"', 1)[0]
    assert fallback == "a_b_c__d.zip"
    assert "\r" not in header
    assert "\n" not in header


def test_test_email_error_text_is_not_leaked(admin_client: TestClient) -> None:
    """A provider exception gives the generic message, not its own text."""
    created = admin_client.post(
        INTEGRATIONS,
        json={
            "integration_type": "smtp",
            "name": "smtp",
            "config": {"host": "smtp.example.com"},
        },
    ).json()
    provider = MagicMock(spec=EmailProvider)
    provider.send_email = AsyncMock(
        side_effect=smtplib.SMTPException("secret relay detail")
    )
    provider.close = AsyncMock()
    target = "src.services.integration_service.create_provider_instance"
    with patch(target, return_value=provider):
        response = admin_client.post(
            f"{INTEGRATIONS}/{created['id']}/test-email",
            json={"to_email": "a@example.com"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "success": False,
        "message": "Failed to send test email: unexpected response",
    }
    assert "secret relay detail" not in response.text


def test_backup_failure_message_is_generic(admin_client: TestClient) -> None:
    """A backup failure reports no exception text."""
    with patch(
        "src.api.v1.backup.backup_service.create_backup",
        side_effect=OSError("/secret/path missing"),
    ):
        response = admin_client.post(
            "/api/v1/backup/create", json={"password": "longenough1"}
        )

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to create backup"


def test_currency_code_is_upper_cased_and_validated() -> None:
    """Lower-case input is stored upper-case; a four-letter code is rejected."""
    body = {
        "date": "2025-03-11",
        "amount": "10.00",
        "payment_type": "cash",
        "category": "meals",
    }

    assert ExpenseCreate(**body, currency="eur").currency == "EUR"
    assert ExpenseCreate(**body).currency == "EUR"
    assert ExpenseCreate(**body, currency=" usd ").amount == Decimal("10.00")
    with pytest.raises(ValidationError):
        ExpenseCreate(**body, currency="EURO")


def test_expense_with_bad_currency_is_422(
    authenticated_client: TestClient, event: Event
) -> None:
    """The expense route rejects a four-letter currency code."""
    response = authenticated_client.post(
        f"{EVENTS}/{event.id}/expenses",
        json={
            "date": "2025-03-11",
            "amount": "10.00",
            "currency": "EURO",
            "payment_type": "cash",
            "category": "meals",
        },
    )

    assert response.status_code == 422


def test_settings_currency_is_stored_upper_case(admin_client: TestClient) -> None:
    """The base currency setting is normalised; four letters give 422."""
    url = "/api/v1/settings/currency"

    ok = admin_client.put(url, json={"base_currency": "eur"})
    bad = admin_client.put(url, json={"base_currency": "EURO"})

    assert ok.status_code == 200
    assert ok.json() == {"base_currency": "EUR"}
    assert admin_client.get(url).json() == {"base_currency": "EUR"}
    assert bad.status_code == 422


def test_event_count_shape(authenticated_client: TestClient) -> None:
    """The count route answers {"count": n}."""
    response = authenticated_client.get(f"{EVENTS}/count")

    assert response.status_code == 200
    assert response.json() == {"count": 0}
