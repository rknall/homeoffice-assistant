# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Ownership tests: a user never reaches another user's event data."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models import Company, Event, Expense, Note, Todo, User
from src.models.enums import CompanyType, ExpenseCategory, PaymentType
from src.services import rbac_service


@pytest.fixture
def owner_data(db_session: Session, test_user: User) -> dict[str, str]:
    """Create an event of ``test_user`` with one expense, note and todo."""
    company = Company(name="Owner Company", type=CompanyType.EMPLOYER)
    db_session.add(company)
    db_session.flush()
    event = Event(
        user_id=test_user.id,
        company_id=company.id,
        name="Owner Event",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 3),
    )
    db_session.add(event)
    db_session.flush()
    expense = Expense(
        event_id=event.id,
        date=date(2026, 3, 2),
        amount=Decimal("12.50"),
        payment_type=PaymentType.CASH,
        category=ExpenseCategory.MEALS,
    )
    note = Note(event_id=event.id, content="private note")
    todo = Todo(event_id=event.id, title="private todo")
    db_session.add_all([expense, note, todo])
    db_session.commit()
    base = f"/api/v1/events/{event.id}"
    return {
        "event": base,
        "expense": f"{base}/expenses/{expense.id}",
        "note": f"{base}/notes/{note.id}",
        "todo": f"{base}/todos/{todo.id}",
    }


@pytest.mark.parametrize("resource", ["event", "expense", "note", "todo"])
def test_other_user_gets_404(
    authenticated_client: TestClient,
    second_user: User,
    login: Callable[[TestClient, User], TestClient],
    owner_data: dict[str, str],
    resource: str,
) -> None:
    """User B gets 404 on user A's resource, while A still reaches it."""
    other_client = login(authenticated_client, second_user)

    assert other_client.get(owner_data[resource]).status_code == 404
    assert authenticated_client.get(owner_data[resource]).status_code == 200


def test_company_viewer_scope(
    db_session: Session, company_viewer_user: User, viewer_company: Company
) -> None:
    """The company viewer fixture grants its role on one company only."""
    other = Company(name="Other Company", type=CompanyType.EMPLOYER)
    db_session.add(other)
    db_session.commit()

    assert rbac_service.user_has_permission(
        db_session, company_viewer_user, "company.view", company_id=viewer_company.id
    )
    assert not rbac_service.user_has_permission(
        db_session, company_viewer_user, "company.view", company_id=other.id
    )
