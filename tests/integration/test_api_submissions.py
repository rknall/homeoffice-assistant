# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Characterization of the expense submission endpoints."""

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models import Company, Event, Expense, User
from src.models.enums import (
    CompanyType,
    ExpenseCategory,
    ExpenseStatus,
    PaymentType,
)
from tests.conftest import LoginHelper


@pytest.fixture
def submission_event(db_session: Session, test_user: User) -> dict[str, Any]:
    """Create an event owned by ``test_user`` with two open expenses."""
    company = Company(name="Submission Company", type=CompanyType.EMPLOYER)
    db_session.add(company)
    db_session.flush()
    event = Event(
        user_id=test_user.id,
        company_id=company.id,
        name="Submission Event",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 2),
    )
    db_session.add(event)
    db_session.flush()
    expenses = [
        Expense(
            event_id=event.id,
            date=date(2026, 5, 1),
            amount=Decimal(amount),
            payment_type=PaymentType.CASH,
            category=ExpenseCategory.MEALS,
        )
        for amount in ("15.00", "25.00")
    ]
    db_session.add_all(expenses)
    db_session.commit()
    return {"event": event, "expenses": expenses}


def _url(data: dict[str, Any], suffix: str = "") -> str:
    return f"/api/v1/events/{data['event'].id}/submissions{suffix}"


def _create(client: TestClient, data: dict[str, Any], **extra: Any) -> Any:
    ids = [str(e.id) for e in data["expenses"]]
    return client.post(_url(data), json={"expense_ids": ids, **extra})


def test_create_submission_marks_expenses_submitted(
    authenticated_client: TestClient,
    db_session: Session,
    submission_event: dict[str, Any],
) -> None:
    """Creating a submission totals the expenses and marks them SUBMITTED."""
    response = _create(authenticated_client, submission_event, notes="March trip")

    assert response.status_code == 201
    body = response.json()
    assert body["expense_count"] == 2
    assert Decimal(str(body["total_amount"])) == Decimal("40.00")
    assert body["notes"] == "March trip"
    assert len(body["items"]) == 2
    db_session.expire_all()
    for expense in submission_event["expenses"]:
        stored = db_session.get(Expense, expense.id)
        assert stored is not None
        assert stored.status == ExpenseStatus.SUBMITTED


def test_create_without_marking_keeps_status(
    authenticated_client: TestClient,
    db_session: Session,
    submission_event: dict[str, Any],
) -> None:
    """mark_as_submitted=false records the submission but keeps the status."""
    response = _create(authenticated_client, submission_event, mark_as_submitted=False)

    assert response.status_code == 201
    db_session.expire_all()
    stored = db_session.get(Expense, submission_event["expenses"][0].id)
    assert stored is not None
    assert stored.status != ExpenseStatus.SUBMITTED


def test_create_with_empty_ids_is_rejected(
    authenticated_client: TestClient, submission_event: dict[str, Any]
) -> None:
    """An empty expense list is a 400."""
    response = authenticated_client.post(
        _url(submission_event), json={"expense_ids": []}
    )

    assert response.status_code == 400
    assert "expense" in response.json()["detail"].lower()


def test_create_with_unknown_expense_is_rejected(
    authenticated_client: TestClient, submission_event: dict[str, Any]
) -> None:
    """Expense ids that match nothing in the event are a 400."""
    response = authenticated_client.post(
        _url(submission_event), json={"expense_ids": [str(uuid.uuid4())]}
    )

    assert response.status_code == 400


def test_list_get_and_summary(
    authenticated_client: TestClient, submission_event: dict[str, Any]
) -> None:
    """A created submission is listed, readable by id and counted in the summary."""
    created = _create(authenticated_client, submission_event).json()

    listed = authenticated_client.get(_url(submission_event))
    assert listed.status_code == 200
    assert [s["id"] for s in listed.json()] == [created["id"]]

    single = authenticated_client.get(_url(submission_event, f"/{created['id']}"))
    assert single.status_code == 200
    assert single.json()["id"] == created["id"]

    summary = authenticated_client.get(_url(submission_event, "/summary"))
    assert summary.status_code == 200
    body = summary.json()
    assert body["submission_count"] == 1
    assert body["total_submitted"] == 40.0
    assert body["total_reimbursed"] == 0.0


def test_summary_without_submissions_is_zero(
    authenticated_client: TestClient, submission_event: dict[str, Any]
) -> None:
    """The summary of an event without submissions is all zero."""
    response = authenticated_client.get(_url(submission_event, "/summary"))

    assert response.status_code == 200
    assert response.json()["submission_count"] == 0
    assert response.json()["total_submitted"] == 0.0


def test_get_unknown_submission_is_not_found(
    authenticated_client: TestClient, submission_event: dict[str, Any]
) -> None:
    """An unknown submission id is a 404."""
    response = authenticated_client.get(_url(submission_event, f"/{uuid.uuid4()}"))

    assert response.status_code == 404
    assert response.json()["detail"] == "Submission not found"


def test_submission_of_another_event_is_not_found(
    authenticated_client: TestClient,
    db_session: Session,
    test_user: User,
    submission_event: dict[str, Any],
) -> None:
    """A submission is only readable through the event it belongs to."""
    created = _create(authenticated_client, submission_event).json()
    other_event = Event(
        user_id=test_user.id,
        company_id=submission_event["event"].company_id,
        name="Other Event",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 2),
    )
    db_session.add(other_event)
    db_session.commit()

    response = authenticated_client.get(
        f"/api/v1/events/{other_event.id}/submissions/{created['id']}"
    )

    assert response.status_code == 404


def test_other_users_event_is_not_found(
    client: TestClient,
    login: LoginHelper,
    second_user: User,
    submission_event: dict[str, Any],
) -> None:
    """Another user cannot list or create submissions on the event."""
    other = login(client, second_user)

    assert other.get(_url(submission_event)).status_code == 404
    assert _create(other, submission_event).status_code == 404


def test_requires_login(client: TestClient, submission_event: dict[str, Any]) -> None:
    """An anonymous caller is rejected."""
    assert client.get(_url(submission_event)).status_code == 401
