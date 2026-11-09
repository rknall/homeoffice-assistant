# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Permission checks on the routes nested under an event.

Every event-nested router loads the event through ``require_event_permission``:
another user's event is 404, a missing code for the event's company is 403.
"""

import datetime
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.main import app
from src.models import Company, Event, Expense, User
from src.models.enums import (
    CompanyType,
    ExpenseCategory,
    ExpenseStatus,
    PaymentType,
)
from src.services import settings_service
from tests.conftest import LoginHelper, UserFactory

EVENTS = "/api/v1/events"


@dataclass
class EventCtx:
    """An event and the ids a request against it needs."""

    event_id: uuid.UUID
    expense_id: uuid.UUID


# A request builder returns (method, url, json body) for an event.
RequestSpec = Callable[[EventCtx], tuple[str, str, dict[str, Any] | None]]


@dataclass
class RouterCase:
    """One read and one write route of an event-nested router."""

    name: str
    read: RequestSpec
    write: RequestSpec
    write_status: int


CASES = [
    RouterCase(
        "expenses",
        lambda c: ("GET", f"{EVENTS}/{c.event_id}/expenses", None),
        lambda c: (
            "POST",
            f"{EVENTS}/{c.event_id}/expenses",
            {
                "date": "2025-03-02",
                "amount": "12.50",
                "currency": "EUR",
                "payment_type": PaymentType.CASH.value,
                "category": ExpenseCategory.OTHER.value,
            },
        ),
        201,
    ),
    RouterCase(
        "notes",
        lambda c: ("GET", f"{EVENTS}/{c.event_id}/notes", None),
        lambda c: ("POST", f"{EVENTS}/{c.event_id}/notes", {"content": "hello"}),
        201,
    ),
    RouterCase(
        "todos",
        lambda c: ("GET", f"{EVENTS}/{c.event_id}/todos", None),
        lambda c: ("POST", f"{EVENTS}/{c.event_id}/todos", {"title": "Book hotel"}),
        201,
    ),
    RouterCase(
        "contacts",
        lambda c: ("GET", f"{EVENTS}/{c.event_id}/contacts", None),
        lambda c: ("POST", f"{EVENTS}/{c.event_id}/contacts", {"name": "Jane"}),
        201,
    ),
    RouterCase(
        "submissions",
        lambda c: ("GET", f"{EVENTS}/{c.event_id}/submissions/summary", None),
        lambda c: (
            "POST",
            f"{EVENTS}/{c.event_id}/submissions",
            {"expense_ids": [str(c.expense_id)], "mark_as_submitted": False},
        ),
        201,
    ),
    RouterCase(
        "reports",
        lambda c: ("GET", f"{EVENTS}/{c.event_id}/expense-report/preview", None),
        lambda c: (
            "POST",
            f"{EVENTS}/{c.event_id}/expense-report/generate",
            {"mark_as_submitted": False},
        ),
        200,
    ),
    RouterCase(
        "photos",
        lambda c: ("GET", f"{EVENTS}/{c.event_id}/photos/references", None),
        lambda c: (
            "POST",
            f"{EVENTS}/{c.event_id}/photos",
            {"immich_asset_id": "asset-1"},
        ),
        200,
    ),
]

CASE_IDS = [case.name for case in CASES]


def _send(client: TestClient, spec: RequestSpec, ctx: EventCtx) -> int:
    method, url, body = spec(ctx)
    return client.request(method, url, json=body).status_code


def _company(db: Session, name: str) -> Company:
    company = Company(name=name, type=CompanyType.EMPLOYER)
    db.add(company)
    db.commit()
    return company


def _event_with_expense(db: Session, user: User, company: Company) -> EventCtx:
    event = Event(
        user_id=user.id,
        company_id=company.id,
        name=f"Trip of {user.username}",
        start_date=datetime.date(2025, 3, 1),
        end_date=datetime.date(2025, 3, 3),
    )
    db.add(event)
    db.flush()
    base_currency = settings_service.get_base_currency(db)
    expense = Expense(
        event_id=event.id,
        date=datetime.date(2025, 3, 2),
        amount=Decimal("20.00"),
        currency=base_currency,
        converted_amount=Decimal("20.00"),
        exchange_rate=Decimal("1"),
        rate_date=datetime.date(2025, 3, 2),
        payment_type=PaymentType.CASH,
        category=ExpenseCategory.OTHER,
    )
    db.add(expense)
    db.commit()
    return EventCtx(event_id=event.id, expense_id=expense.id)


@pytest.fixture
def alpha(db_session: Session) -> Company:
    """Company Alpha, the scope of the viewer's role."""
    return _company(db_session, "Alpha")


@pytest.fixture
def owner(user_factory: UserFactory) -> User:
    """Event owner holding Member globally."""
    return user_factory("owner_a", roles=["Member"])


@pytest.fixture
def owner_event(db_session: Session, owner: User, alpha: Company) -> EventCtx:
    """An Alpha event owned by ``owner``."""
    return _event_with_expense(db_session, owner, alpha)


@pytest.fixture
def viewer_event(
    db_session: Session, user_factory: UserFactory, alpha: Company
) -> tuple[User, EventCtx]:
    """A user holding only Company Viewer on Alpha, and an Alpha event of theirs."""
    viewer = user_factory("viewer_alpha", roles=["Company Viewer"], company=alpha)
    return viewer, _event_with_expense(db_session, viewer, alpha)


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_other_user_gets_404(
    case: RouterCase,
    client: TestClient,
    login: LoginHelper,
    user_factory: UserFactory,
    owner_event: EventCtx,
) -> None:
    """A user who does not own the event cannot tell it exists."""
    other = login(client, user_factory("other_b", roles=["Member"]))
    assert _send(other, case.read, owner_event) == 404
    assert _send(other, case.write, owner_event) == 404


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_company_viewer_reads_but_cannot_write(
    case: RouterCase,
    client: TestClient,
    login: LoginHelper,
    viewer_event: tuple[User, EventCtx],
) -> None:
    """Company Viewer on the event's company may read, not write."""
    viewer, ctx = viewer_event
    viewer_client = login(client, viewer)
    assert _send(viewer_client, case.read, ctx) == 200
    assert _send(viewer_client, case.write, ctx) == 403


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_owner_with_member_keeps_access(
    case: RouterCase,
    client: TestClient,
    login: LoginHelper,
    owner: User,
    owner_event: EventCtx,
) -> None:
    """The owner holding Member reads and writes as before."""
    owner_client = login(client, owner)
    assert _send(owner_client, case.read, owner_event) == 200
    assert _send(owner_client, case.write, owner_event) == case.write_status


REMOVED_ROUTES = [
    ("POST", "/api/v1/events/{event_id}/expenses/bulk-update"),
    ("GET", "/api/v1/events/{event_id}/expenses/summary"),
    ("PATCH", "/api/v1/events/{event_id}/expenses/{expense_id}/status"),
]


@pytest.mark.parametrize(("method", "path"), REMOVED_ROUTES)
def test_removed_expense_routes_are_not_registered(method: str, path: str) -> None:
    """The unused expense endpoints are gone from the app."""
    registered = {
        (m, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        for m in route.methods
    }
    assert (method, path) not in registered


@pytest.mark.parametrize(("method", "path"), REMOVED_ROUTES)
def test_removed_expense_routes_are_not_served(
    method: str,
    path: str,
    client: TestClient,
    login: LoginHelper,
    owner: User,
    owner_event: EventCtx,
) -> None:
    """A request to a removed path reaches no removed handler.

    ``GET .../expenses/summary`` now matches ``GET .../expenses/{expense_id}``
    and fails UUID parsing, hence 422.
    """
    owner_client = login(client, owner)
    url = path.format(event_id=owner_event.event_id, expense_id=owner_event.expense_id)
    response = owner_client.request(method, url, json={})
    assert response.status_code in {404, 405, 422}


def test_bulk_status_changes_only_this_events_expenses(
    db_session: Session,
    client: TestClient,
    login: LoginHelper,
    user_factory: UserFactory,
    owner_event: EventCtx,
    alpha: Company,
) -> None:
    """Expense ids of another user's event are ignored by bulk-status."""
    other = user_factory("other_b")
    other_event = _event_with_expense(db_session, other, alpha)
    other_client = login(client, other)

    response = other_client.post(
        f"{EVENTS}/{other_event.event_id}/expenses/bulk-status",
        json={
            "expense_ids": [str(owner_event.expense_id), str(other_event.expense_id)],
            "status": ExpenseStatus.SUBMITTED.value,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"updated": 1}
    db_session.expire_all()
    victim = db_session.get(Expense, owner_event.expense_id)
    own = db_session.get(Expense, other_event.expense_id)
    assert victim is not None and own is not None
    assert victim.status == ExpenseStatus.PENDING
    assert own.status == ExpenseStatus.SUBMITTED


def test_user_without_roles_is_denied(
    client: TestClient,
    login: LoginHelper,
    user_factory: UserFactory,
) -> None:
    """A user holding no role at all gets 403 on event data."""
    nobody = login(client, user_factory("nobody", roles=()))
    assert nobody.get(EVENTS).status_code == 403
    assert nobody.get(f"{EVENTS}/count").status_code == 403
