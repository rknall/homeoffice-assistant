# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Email dates follow the configured locale date format."""

from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models import Company, EmailTemplate, Event, Expense, User
from src.models.enums import CompanyType, ExpenseCategory, PaymentType
from src.services import settings_service
from tests.integration.test_report_send import FakeSmtp, _send

PREVIEW = "/api/v1/email-templates/preview"


@pytest.fixture
def german_dates(db_session: Session) -> None:
    """Configure the DD.MM.YYYY locale date format."""
    settings_service.update_locale_settings(db_session, date_format="DD.MM.YYYY")


@pytest.fixture
def dated_event(db_session: Session, test_user: User) -> Event:
    """Create an event from 2026-03-01 to 2026-03-03 with one expense."""
    company = Company(name="Locale Company", type=CompanyType.EMPLOYER)
    db_session.add(company)
    db_session.flush()
    event = Event(
        user_id=test_user.id,
        company_id=company.id,
        name="Locale Event",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 3),
    )
    db_session.add(event)
    db_session.flush()
    db_session.add(
        Expense(
            event_id=event.id,
            date=date(2026, 3, 2),
            amount=10,
            payment_type=PaymentType.CASH,
            category=ExpenseCategory.MEALS,
        )
    )
    db_session.add(
        EmailTemplate(
            name="Dates",
            reason="expense_report",
            company_id=company.id,
            subject="{{event.start_date}} to {{event.end_date}}",
            body_html="<p>x</p>",
            body_text="x",
            is_default=True,
        )
    )
    db_session.commit()
    return event


def _preview(client: TestClient, **extra: Any) -> dict[str, Any]:
    response = client.post(
        PREVIEW,
        json={
            "reason": "expense_report",
            "subject": "{{event.start_date}} to {{event.end_date}}",
            "body_html": "<p>x</p>",
            "body_text": "x",
            **extra,
        },
    )
    assert response.status_code == 200
    return response.json()


@pytest.mark.usefixtures("german_dates")
def test_sample_preview_uses_locale_date_format(
    authenticated_client: TestClient,
) -> None:
    """The sample-data preview renders dates in the configured format."""
    subject = _preview(authenticated_client)["subject"]

    assert "-" not in subject
    assert subject.count(".") == 4


@pytest.mark.usefixtures("german_dates")
def test_event_preview_uses_locale_date_format(
    authenticated_client: TestClient, dated_event: Event
) -> None:
    """The real-event preview renders dates in the configured format."""
    subject = _preview(authenticated_client, event_id=str(dated_event.id))["subject"]

    assert subject == "01.03.2026 to 03.03.2026"


def test_event_preview_defaults_to_iso(
    authenticated_client: TestClient, dated_event: Event
) -> None:
    """Without a locale setting the default ISO format applies."""
    subject = _preview(authenticated_client, event_id=str(dated_event.id))["subject"]

    assert subject == "2026-03-01 to 2026-03-03"


@pytest.mark.usefixtures("german_dates")
def test_sent_report_uses_locale_date_format(
    authenticated_client: TestClient, dated_event: Event
) -> None:
    """The report email renders dates in the configured format."""
    provider = FakeSmtp(True)

    response = _send(authenticated_client, dated_event, provider)

    assert response.status_code == 200
    assert provider.sent[0]["subject"] == "01.03.2026 to 03.03.2026"
