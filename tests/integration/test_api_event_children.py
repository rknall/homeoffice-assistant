# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Characterization of notes, contacts, todos and todo templates (current behavior)."""

import datetime
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models import Company, Event, TodoTemplate, User
from src.models.enums import CompanyType
from tests.conftest import LoginHelper, UserFactory

EVENTS = "/api/v1/events"
TEMPLATES = "/api/v1/todo-templates"


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


@pytest.fixture
def foreign_client(
    event: Event, client: TestClient, user_factory: UserFactory, login: LoginHelper
) -> TestClient:
    """A client of another user, who must not see the event."""
    return login(client, user_factory("stranger"))


CRUD_CASES = [
    pytest.param(
        "notes",
        {"content": "Met the CEO", "note_type": "observation"},
        {"content": "Changed"},
        "content",
        id="notes",
    ),
    pytest.param(
        "contacts",
        {"name": "Jane Doe", "email": "jane@example.com"},
        {"name": "Jane Roe"},
        "name",
        id="contacts",
    ),
    pytest.param(
        "todos",
        {"title": "Book flight", "due_date": "2025-03-01"},
        {"title": "Book train", "completed": True},
        "title",
        id="todos",
    ),
]


@pytest.mark.parametrize(("kind", "create", "update", "field"), CRUD_CASES)
def test_child_crud_cycle(
    authenticated_client: TestClient,
    event: Event,
    kind: str,
    create: dict,
    update: dict,
    field: str,
) -> None:
    base = f"{EVENTS}/{event.id}/{kind}"

    created = authenticated_client.post(base, json=create)
    assert created.status_code == 201
    item = created.json()
    assert item["event_id"] == str(event.id)
    item_url = f"{base}/{item['id']}"

    assert authenticated_client.get(item_url).json()[field] == create[field]
    assert [i["id"] for i in authenticated_client.get(base).json()] == [item["id"]]

    updated = authenticated_client.put(item_url, json=update)
    assert updated.status_code == 200
    assert updated.json()[field] == update[field]

    assert authenticated_client.delete(item_url).status_code == 204
    assert authenticated_client.get(item_url).status_code == 404
    assert authenticated_client.get(base).json() == []


@pytest.mark.parametrize(("kind", "create", "update", "field"), CRUD_CASES)
def test_child_unknown_id_is_404(
    authenticated_client: TestClient,
    event: Event,
    kind: str,
    create: dict,
    update: dict,
    field: str,
) -> None:
    url = f"{EVENTS}/{event.id}/{kind}/{uuid.uuid4()}"

    assert authenticated_client.get(url).status_code == 404
    assert authenticated_client.put(url, json=update).status_code == 404
    assert authenticated_client.delete(url).status_code == 404


@pytest.mark.parametrize(("kind", "create", "update", "field"), CRUD_CASES)
def test_child_of_another_users_event_is_404(
    foreign_client: TestClient,
    event: Event,
    kind: str,
    create: dict,
    update: dict,
    field: str,
) -> None:
    base = f"{EVENTS}/{event.id}/{kind}"

    assert foreign_client.get(base).status_code == 404
    assert foreign_client.post(base, json=create).status_code == 404


@pytest.mark.parametrize(
    ("kind", "bad"),
    [
        ("notes", {"content": ""}),
        ("contacts", {"name": "x", "email": "nope"}),
        ("todos", {"title": ""}),
    ],
)
def test_child_create_validates_input(
    authenticated_client: TestClient, event: Event, kind: str, bad: dict
) -> None:
    response = authenticated_client.post(f"{EVENTS}/{event.id}/{kind}", json=bad)

    assert response.status_code == 422


def test_child_requires_login(client: TestClient, event: Event) -> None:
    assert client.get(f"{EVENTS}/{event.id}/notes").status_code == 401


def test_child_cannot_be_read_through_another_event(
    authenticated_client: TestClient, db_session: Session, event: Event
) -> None:
    other = Event(
        user_id=event.user_id,
        company_id=event.company_id,
        name="Other",
        start_date=datetime.date(2025, 4, 1),
        end_date=datetime.date(2025, 4, 2),
    )
    db_session.add(other)
    db_session.commit()
    note = authenticated_client.post(
        f"{EVENTS}/{event.id}/notes", json={"content": "mine"}
    ).json()

    response = authenticated_client.get(f"{EVENTS}/{other.id}/notes/{note['id']}")

    assert response.status_code == 404


def test_todo_templates_for_event_have_computed_dates(
    authenticated_client: TestClient,
    db_session: Session,
    event: Event,
    test_user: User,
) -> None:
    db_session.add_all(
        [
            TodoTemplate(
                title="Pack",
                template_set_name="Trip",
                days_offset=-2,
                is_global=True,
            ),
            TodoTemplate(
                title="Expenses",
                template_set_name="Trip",
                days_offset=3,
                offset_reference="end_date",
                user_id=test_user.id,
            ),
        ]
    )
    db_session.commit()

    response = authenticated_client.get(f"{EVENTS}/{event.id}/todos/templates")

    assert response.status_code == 200
    (trip,) = [s for s in response.json() if s["name"] == "Trip"]
    dates = {t["title"]: t["computed_due_date"] for t in trip["templates"]}
    assert dates == {"Pack": "2025-03-08", "Expenses": "2025-03-17"}
    assert trip["is_global"] is False


def test_apply_templates_creates_todos(
    authenticated_client: TestClient,
    db_session: Session,
    event: Event,
    test_user: User,
) -> None:
    template = TodoTemplate(
        title="Pack", template_set_name="Trip", days_offset=-1, user_id=test_user.id
    )
    db_session.add(template)
    db_session.commit()
    url = f"{EVENTS}/{event.id}/todos"

    response = authenticated_client.post(
        f"{url}/from-templates", json={"template_ids": [str(template.id)]}
    )

    assert response.status_code == 201
    assert response.json()["created_count"] == 1
    (todo,) = authenticated_client.get(url).json()
    assert todo["title"] == "Pack"
    assert todo["due_date"] == "2025-03-09"
    assert todo["completed"] is False


def test_apply_templates_requires_ids(
    authenticated_client: TestClient, event: Event
) -> None:
    response = authenticated_client.post(
        f"{EVENTS}/{event.id}/todos/from-templates", json={"template_ids": []}
    )

    assert response.status_code == 422


TEMPLATE_BODY = {
    "title": "Check passport",
    "template_set_name": "Travel",
    "days_offset": -7,
    "offset_reference": "start_date",
}


def test_template_crud_cycle(authenticated_client: TestClient) -> None:
    created = authenticated_client.post(TEMPLATES, json=TEMPLATE_BODY)
    assert created.status_code == 201
    template = created.json()
    assert template["is_global"] is False
    url = f"{TEMPLATES}/{template['id']}"

    assert authenticated_client.get(url).json()["title"] == "Check passport"
    sets = {s["name"]: s for s in authenticated_client.get(TEMPLATES).json()}
    assert sets["Travel"]["is_global"] is False
    flat = authenticated_client.get(f"{TEMPLATES}/all").json()
    assert template["id"] in [t["id"] for t in flat]

    updated = authenticated_client.put(url, json={"days_offset": -14})
    assert updated.status_code == 200
    assert updated.json()["days_offset"] == -14

    assert authenticated_client.delete(url).status_code == 204
    assert authenticated_client.get(url).status_code == 404


def test_template_validates_input(authenticated_client: TestClient) -> None:
    bad = {**TEMPLATE_BODY, "title": ""}

    assert authenticated_client.post(TEMPLATES, json=bad).status_code == 422


def test_template_unknown_id_is_404(authenticated_client: TestClient) -> None:
    url = f"{TEMPLATES}/{uuid.uuid4()}"

    assert authenticated_client.get(url).status_code == 404
    assert authenticated_client.put(url, json={"title": "x"}).status_code == 404
    assert authenticated_client.delete(url).status_code == 404


def test_global_template_is_readable_but_not_changeable(
    authenticated_client: TestClient, db_session: Session
) -> None:
    template = TodoTemplate(title="Shipped", template_set_name="Core", is_global=True)
    db_session.add(template)
    db_session.commit()
    url = f"{TEMPLATES}/{template.id}"

    assert authenticated_client.get(url).status_code == 200
    assert authenticated_client.put(url, json={"title": "x"}).status_code == 403
    assert authenticated_client.delete(url).status_code == 403


def test_other_users_template_is_hidden(
    client: TestClient,
    user_factory: UserFactory,
    login: LoginHelper,
    test_user: User,
    db_session: Session,
) -> None:
    template = TodoTemplate(
        title="Private", template_set_name="Mine", user_id=test_user.id
    )
    db_session.add(template)
    db_session.commit()
    url = f"{TEMPLATES}/{template.id}"
    stranger = login(client, user_factory("stranger"))

    assert stranger.get(url).status_code == 404
    assert stranger.put(url, json={"title": "x"}).status_code == 404
    assert stranger.delete(url).status_code == 404
    assert "Mine" not in [s["name"] for s in stranger.get(TEMPLATES).json()]


def test_templates_require_login(client: TestClient) -> None:
    assert client.get(TEMPLATES).status_code == 401
