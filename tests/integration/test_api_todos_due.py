# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""GET /api/v1/todos: todos due in a date range across the user's events."""

import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models import Company, Event, Todo, User
from src.models.enums import CompanyType
from tests.conftest import LoginHelper, UserFactory

TODOS = "/api/v1/todos"
RANGE = {"due_from": "2025-05-01", "due_to": "2025-05-31"}


def _company(db: Session, name: str) -> Company:
    company = Company(name=name, type=CompanyType.EMPLOYER)
    db.add(company)
    db.commit()
    return company


def _event_with_todo(db: Session, user: User, company: Company, title: str) -> Event:
    event = Event(
        user_id=user.id,
        company_id=company.id,
        name=f"Trip {title}",
        start_date=datetime.date(2025, 5, 1),
        end_date=datetime.date(2025, 5, 3),
    )
    db.add(event)
    db.flush()
    db.add(Todo(event_id=event.id, title=title, due_date=datetime.date(2025, 5, 2)))
    db.commit()
    return event


def _titles(client: TestClient, params: dict[str, str] = RANGE) -> list[str]:
    response = client.get(TODOS, params=params)
    assert response.status_code == 200, response.text
    return [t["title"] for t in response.json()]


def test_owner_sees_own_todos_in_range_but_not_foreign(
    db_session: Session,
    client: TestClient,
    user_factory: UserFactory,
    login: LoginHelper,
) -> None:
    company = _company(db_session, "Shared Co")
    owner = user_factory("owner")
    other = user_factory("other")
    _event_with_todo(db_session, owner, company, "mine")
    _event_with_todo(db_session, other, company, "theirs")

    assert _titles(login(client, owner)) == ["mine"]
    assert _titles(login(client, other)) == ["theirs"]
    outside = {"due_from": "2025-06-01", "due_to": "2025-06-30"}
    assert _titles(login(client, owner), outside) == []


def test_company_without_event_read_is_excluded(
    db_session: Session,
    client: TestClient,
    user_factory: UserFactory,
    login: LoginHelper,
) -> None:
    allowed = _company(db_session, "Allowed Co")
    denied = _company(db_session, "Denied Co")
    user = user_factory("scoped", roles=["Company Viewer"], company=allowed)
    _event_with_todo(db_session, user, allowed, "visible")
    _event_with_todo(db_session, user, denied, "hidden")
    user_client = login(client, user)

    assert _titles(user_client) == ["visible"]
    # A company id in the query narrows the check but never widens results.
    assert _titles(user_client, {**RANGE, "company_id": str(allowed.id)}) == ["visible"]
    response = user_client.get(TODOS, params={**RANGE, "company_id": str(denied.id)})
    assert response.status_code == 403


def test_user_without_event_read_gets_403(
    client: TestClient, user_factory: UserFactory, login: LoginHelper
) -> None:
    response = login(client, user_factory("nobody", roles=())).get(TODOS, params=RANGE)
    assert response.status_code == 403


def test_reversed_range_is_422(
    client: TestClient, user_factory: UserFactory, login: LoginHelper
) -> None:
    response = login(client, user_factory("owner")).get(
        TODOS, params={"due_from": "2025-05-31", "due_to": "2025-05-01"}
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "due_from must not be after due_to"


def test_missing_params_are_422(
    client: TestClient, user_factory: UserFactory, login: LoginHelper
) -> None:
    user_client = login(client, user_factory("owner"))
    assert user_client.get(TODOS).status_code == 422
    assert user_client.get(TODOS, params={"due_from": "2025-05-01"}).status_code == 422
    assert user_client.get(TODOS, params={"due_to": "2025-05-31"}).status_code == 422


def test_per_event_route_still_works(
    db_session: Session,
    client: TestClient,
    user_factory: UserFactory,
    login: LoginHelper,
) -> None:
    owner = user_factory("owner")
    event = _event_with_todo(db_session, owner, _company(db_session, "Co"), "mine")

    response = login(client, owner).get(f"/api/v1/events/{event.id}/todos")

    assert response.status_code == 200
    assert [t["title"] for t in response.json()] == ["mine"]
