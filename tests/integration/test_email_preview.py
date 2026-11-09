# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Email template preview: event scope and HTML escaping."""

from collections.abc import Callable
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models import Company, Event, User
from src.models.enums import CompanyType


@pytest.fixture
def owner_event_id(db_session: Session, test_user: User) -> str:
    """Create an event of ``test_user`` whose name contains markup."""
    company = Company(name="Owner Company", type=CompanyType.EMPLOYER)
    db_session.add(company)
    db_session.flush()
    event = Event(
        user_id=test_user.id,
        company_id=company.id,
        name="<i>Expo</i>",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 3),
    )
    db_session.add(event)
    db_session.commit()
    return str(event.id)


def _payload(event_id: str) -> dict[str, str]:
    return {
        "reason": "expense_report",
        "subject": "{{event.name}}",
        "body_html": "<p>{{event.name}}</p>",
        "body_text": "{{event.name}}",
        "event_id": event_id,
    }


def test_preview_other_users_event_404(
    authenticated_client: TestClient,
    second_user: User,
    login: Callable[[TestClient, User], TestClient],
    owner_event_id: str,
) -> None:
    """User B cannot preview user A's event; A can, with escaped HTML."""
    other_client = login(authenticated_client, second_user)
    response = other_client.post(
        "/api/v1/email-templates/preview", json=_payload(owner_event_id)
    )
    assert response.status_code == 404

    response = authenticated_client.post(
        "/api/v1/email-templates/preview", json=_payload(owner_event_id)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["body_html"] == "<p>&lt;i&gt;Expo&lt;/i&gt;</p>"
    assert body["body_text"] == "<i>Expo</i>"
