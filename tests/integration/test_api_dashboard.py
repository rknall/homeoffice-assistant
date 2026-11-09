# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Characterization of the dashboard summary endpoint."""

from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models import Company, Event, Expense, Todo, User
from src.models.enums import CompanyType, ExpenseCategory, PaymentType
from tests.conftest import LoginHelper, UserFactory

URL = "/api/v1/dashboard/summary"


def _company(db_session: Session) -> Company:
    company = Company(name="Dash Company", type=CompanyType.EMPLOYER)
    db_session.add(company)
    db_session.flush()
    return company


def _event(
    db_session: Session,
    user: User,
    company: Company,
    name: str,
    start_offset: int,
    end_offset: int,
) -> Event:
    today = date.today()
    event = Event(
        user_id=user.id,
        company_id=company.id,
        name=name,
        start_date=today + timedelta(days=start_offset),
        end_date=today + timedelta(days=end_offset),
    )
    db_session.add(event)
    db_session.flush()
    return event


def test_empty_summary(authenticated_client: TestClient) -> None:
    """A user without events gets zero counts and empty lists."""
    response = authenticated_client.get(URL)

    assert response.status_code == 200
    body = response.json()
    assert body["events_by_status"] == {"upcoming": 0, "active": 0, "past": 0}
    assert body["upcoming_events"] == []
    assert body["events_needing_reports"] == []
    assert body["incomplete_todos"] == []
    assert body["expense_summary"]["total"] == 0
    assert body["expense_summary"]["by_category"] == []


def test_summary_counts_and_lists(
    authenticated_client: TestClient, db_session: Session, test_user: User
) -> None:
    """Events are counted by computed status and listed by relevance."""
    company = _company(db_session)
    _event(db_session, test_user, company, "Past", -10, -8)
    _event(db_session, test_user, company, "Active", -1, 1)
    soon = _event(db_session, test_user, company, "Soon", 3, 5)
    _event(db_session, test_user, company, "Later", 20, 22)
    db_session.add(Todo(event_id=soon.id, title="Book hotel", due_date=None))
    db_session.add(
        Todo(
            event_id=soon.id,
            title="Done already",
            completed=True,
        )
    )
    db_session.commit()

    body = authenticated_client.get(URL).json()

    assert body["events_by_status"] == {"upcoming": 2, "active": 1, "past": 1}
    upcoming = body["upcoming_events"]
    assert [e["name"] for e in upcoming] == ["Soon", "Later"]
    assert upcoming[0]["days_until"] == 3
    assert upcoming[0]["company_name"] == "Dash Company"
    assert [t["title"] for t in body["incomplete_todos"]] == ["Book hotel"]
    assert body["incomplete_todos"][0]["event_name"] == "Soon"
    assert body["incomplete_todos"][0]["is_overdue"] is False


def test_past_event_with_expenses_needs_report(
    authenticated_client: TestClient, db_session: Session, test_user: User
) -> None:
    """A past event with expenses and no sent report is flagged, then cleared."""
    company = _company(db_session)
    past = _event(db_session, test_user, company, "Past trip", -10, -8)
    db_session.add(
        Expense(
            event_id=past.id,
            date=past.start_date,
            amount=Decimal("40.00"),
            converted_amount=Decimal("40.00"),
            payment_type=PaymentType.CASH,
            category=ExpenseCategory.MEALS,
        )
    )
    db_session.commit()

    flagged = authenticated_client.get(URL).json()["events_needing_reports"]
    assert [e["event_name"] for e in flagged] == ["Past trip"]
    assert flagged[0]["expense_count"] == 1
    assert flagged[0]["total_amount"] == 40.0
    assert flagged[0]["currency"] == "EUR"

    past.report_sent_at = datetime.now()
    db_session.commit()

    assert authenticated_client.get(URL).json()["events_needing_reports"] == []


def test_summary_only_covers_own_events(
    client: TestClient,
    login: LoginHelper,
    db_session: Session,
    test_user: User,
    second_user: User,
) -> None:
    """Another user's events do not show in the summary."""
    company = _company(db_session)
    _event(db_session, test_user, company, "Mine", 2, 3)
    db_session.commit()

    other = login(client, second_user)
    body = other.get(URL).json()

    assert body["events_by_status"]["upcoming"] == 0
    assert body["upcoming_events"] == []


def test_company_viewer_may_open_summary(
    client: TestClient, login: LoginHelper, company_viewer_user: User
) -> None:
    """event.read in any company is enough to open the dashboard."""
    assert login(client, company_viewer_user).get(URL).status_code == 200


def test_user_without_role_is_forbidden(
    client: TestClient, login: LoginHelper, user_factory: UserFactory
) -> None:
    """A user holding no event.read role gets 403."""
    user = user_factory("norole", roles=())

    assert login(client, user).get(URL).status_code == 403


def test_requires_login(client: TestClient) -> None:
    """An anonymous caller is rejected."""
    assert client.get(URL).status_code == 401
