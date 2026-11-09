# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Characterization of the expense report preview and download endpoints."""

import io
import zipfile
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models import Company, Event, Expense, ExpenseSubmission, User
from src.models.enums import (
    CompanyType,
    ExpenseCategory,
    ExpenseStatus,
    PaymentType,
)
from tests.conftest import LoginHelper


@pytest.fixture
def report_event(db_session: Session, test_user: User) -> dict[str, Any]:
    """Create an event owned by ``test_user`` with two open expenses."""
    company = Company(name="Report API Company", type=CompanyType.EMPLOYER)
    db_session.add(company)
    db_session.flush()
    event = Event(
        user_id=test_user.id,
        company_id=company.id,
        name="Report API Event",
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 3),
    )
    db_session.add(event)
    db_session.flush()
    expenses = [
        Expense(
            event_id=event.id,
            date=date(2026, 4, 2),
            amount=Decimal("10.00"),
            payment_type=PaymentType.CASH,
            category=ExpenseCategory.MEALS,
        ),
        Expense(
            event_id=event.id,
            date=date(2026, 4, 2),
            amount=Decimal("20.00"),
            payment_type=PaymentType.CREDIT_CARD,
            category=ExpenseCategory.TRAVEL,
        ),
    ]
    db_session.add_all(expenses)
    db_session.commit()
    return {"event": event, "expenses": expenses}


def test_preview_totals_and_breakdown(
    authenticated_client: TestClient, report_event: dict[str, Any]
) -> None:
    """The preview sums all expenses and groups them by category."""
    event = report_event["event"]
    response = authenticated_client.get(
        f"/api/v1/events/{event.id}/expense-report/preview"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["event_name"] == "Report API Event"
    assert body["expense_count"] == 2
    assert body["total"] == 30.0
    assert body["by_category"] == {"meals": 10.0, "travel": 20.0}
    assert body["paperless_configured"] is False


def test_preview_requires_login(
    client: TestClient, report_event: dict[str, Any]
) -> None:
    """An anonymous caller is rejected."""
    event = report_event["event"]
    response = client.get(f"/api/v1/events/{event.id}/expense-report/preview")

    assert response.status_code == 401


def test_preview_other_users_event_is_not_found(
    client: TestClient,
    login: LoginHelper,
    second_user: User,
    report_event: dict[str, Any],
) -> None:
    """A user who does not own the event cannot preview its report."""
    other = login(client, second_user)
    event = report_event["event"]
    response = other.get(f"/api/v1/events/{event.id}/expense-report/preview")

    assert response.status_code == 404


def test_generate_returns_zip_and_marks_submitted(
    authenticated_client: TestClient,
    db_session: Session,
    report_event: dict[str, Any],
) -> None:
    """Generate returns a ZIP, writes a submission and sets report_sent_at."""
    event = report_event["event"]
    response = authenticated_client.post(
        f"/api/v1/events/{event.id}/expense-report/generate"
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "attachment" in response.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert archive.namelist()
    db_session.expire_all()
    assert db_session.query(ExpenseSubmission).count() == 1
    stored = db_session.get(Event, event.id)
    assert stored is not None
    assert stored.report_sent_at is not None
    for expense in report_event["expenses"]:
        stored_expense = db_session.get(Expense, expense.id)
        assert stored_expense is not None
        assert stored_expense.status == ExpenseStatus.SUBMITTED


def test_generate_without_marking_keeps_expenses_open(
    authenticated_client: TestClient,
    db_session: Session,
    report_event: dict[str, Any],
) -> None:
    """mark_as_submitted=false writes no submission."""
    event = report_event["event"]
    response = authenticated_client.post(
        f"/api/v1/events/{event.id}/expense-report/generate",
        json={"mark_as_submitted": False},
    )

    assert response.status_code == 200
    db_session.expire_all()
    assert db_session.query(ExpenseSubmission).count() == 0


def test_generate_selected_expenses_only(
    authenticated_client: TestClient,
    db_session: Session,
    report_event: dict[str, Any],
) -> None:
    """Only the selected expenses are submitted."""
    event = report_event["event"]
    first = report_event["expenses"][0]
    response = authenticated_client.post(
        f"/api/v1/events/{event.id}/expense-report/generate",
        json={"expense_ids": [str(first.id)]},
    )

    assert response.status_code == 200
    db_session.expire_all()
    submission = db_session.query(ExpenseSubmission).one()
    assert submission.expense_count == 1


def test_generate_other_users_event_is_not_found(
    client: TestClient,
    login: LoginHelper,
    second_user: User,
    report_event: dict[str, Any],
) -> None:
    """A user who does not own the event cannot generate its report."""
    other = login(client, second_user)
    event = report_event["event"]
    response = other.post(f"/api/v1/events/{event.id}/expense-report/generate")

    assert response.status_code == 404
