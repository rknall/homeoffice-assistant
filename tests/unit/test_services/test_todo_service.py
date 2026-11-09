# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for todo_service."""

import uuid
from datetime import date

from src.models import Company, Event, Todo
from src.models.enums import CompanyType, TodoCategory
from src.schemas.todo import TodoCreate, TodoUpdate
from src.services import todo_service


def make_event(db_session, user, name: str = "Trip") -> Event:
    company = Company(name=f"Co {name}", type=CompanyType.EMPLOYER)
    db_session.add(company)
    db_session.commit()
    event = Event(
        user_id=user.id,
        company_id=company.id,
        name=name,
        start_date=date(2025, 5, 1),
        end_date=date(2025, 5, 2),
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    return event


def test_create_todo_is_open_and_belongs_to_event(db_session, test_user):
    event = make_event(db_session, test_user)

    todo = todo_service.create_todo(
        db_session,
        event.id,
        TodoCreate(title="Pack", category=TodoCategory.TRAVEL),
    )

    assert todo.event_id == event.id
    assert todo.completed is False
    assert todo.category == TodoCategory.TRAVEL


def test_get_todo_for_event_requires_matching_event(db_session, test_user):
    event = make_event(db_session, test_user, "A")
    other = make_event(db_session, test_user, "B")
    todo = todo_service.create_todo(db_session, event.id, TodoCreate(title="Pack"))

    assert todo_service.get_todo_for_event(db_session, todo.id, event.id) == todo
    assert todo_service.get_todo_for_event(db_session, todo.id, other.id) is None
    assert todo_service.get_todo_for_event(db_session, uuid.uuid4(), event.id) is None


def test_update_todo_applies_only_set_fields(db_session, test_user):
    event = make_event(db_session, test_user)
    todo = todo_service.create_todo(
        db_session,
        event.id,
        TodoCreate(title="Pack", description="bags", due_date=date(2025, 4, 30)),
    )

    updated = todo_service.update_todo(
        db_session, todo, TodoUpdate(completed=True, description=None)
    )

    assert updated.completed is True
    assert updated.description is None
    assert updated.title == "Pack"
    assert updated.due_date == date(2025, 4, 30)


def test_delete_todo(db_session, test_user):
    event = make_event(db_session, test_user)
    todo = todo_service.create_todo(db_session, event.id, TodoCreate(title="Pack"))
    todo_id = todo.id

    todo_service.delete_todo(db_session, todo)

    assert todo_service.get_todo_for_event(db_session, todo_id, event.id) is None


def test_auto_complete_report_todos_matches_keywords_and_followup(
    db_session, test_user
):
    event = make_event(db_session, test_user, "A")
    other = make_event(db_session, test_user, "B")
    matching = [
        TodoCreate(title="Write Report"),
        TodoCreate(title="submit it"),
        TodoCreate(title="Send mail"),
        TodoCreate(title="Expense check"),
        TodoCreate(title="Call", category=TodoCategory.FOLLOWUP),
    ]
    for data in matching:
        todo_service.create_todo(db_session, event.id, data)
    unrelated = todo_service.create_todo(
        db_session, event.id, TodoCreate(title="Book hotel")
    )
    foreign = todo_service.create_todo(
        db_session, other.id, TodoCreate(title="Write Report")
    )

    count = todo_service.auto_complete_report_todos(db_session, event.id)

    assert count == 5
    db_session.refresh(unrelated)
    db_session.refresh(foreign)
    assert unrelated.completed is False
    assert foreign.completed is False
    done = db_session.query(Todo).filter(Todo.completed).count()
    assert done == 5


def test_auto_complete_report_todos_ignores_completed(db_session, test_user):
    event = make_event(db_session, test_user)
    todo = todo_service.create_todo(db_session, event.id, TodoCreate(title="Report"))
    todo_service.update_todo(db_session, todo, TodoUpdate(completed=True))

    assert todo_service.auto_complete_report_todos(db_session, event.id) == 0


def _due(db_session, event, title: str, due: date | None) -> Todo:
    return todo_service.create_todo(
        db_session, event.id, TodoCreate(title=title, due_date=due)
    )


def test_list_due_todos_range_is_inclusive_and_skips_undated(db_session, test_user):
    event = make_event(db_session, test_user)
    _due(db_session, event, "before", date(2025, 4, 30))
    _due(db_session, event, "b-start", date(2025, 5, 1))
    _due(db_session, event, "a-start", date(2025, 5, 1))
    _due(db_session, event, "end", date(2025, 5, 31))
    _due(db_session, event, "after", date(2025, 6, 1))
    _due(db_session, event, "undated", None)

    todos = todo_service.list_due_todos(
        db_session, test_user.id, date(2025, 5, 1), date(2025, 5, 31), None
    )

    assert [t.title for t in todos] == ["a-start", "b-start", "end"]


def test_list_due_todos_excludes_other_users_events(db_session, test_user, second_user):
    _due(db_session, make_event(db_session, test_user, "Own"), "own", date(2025, 5, 2))
    _due(
        db_session,
        make_event(db_session, second_user, "Other"),
        "foreign",
        date(2025, 5, 2),
    )

    todos = todo_service.list_due_todos(
        db_session, test_user.id, date(2025, 5, 1), date(2025, 5, 31), None
    )

    assert [t.title for t in todos] == ["own"]


def test_list_due_todos_filters_by_company(db_session, test_user):
    allowed = make_event(db_session, test_user, "Allowed")
    other = make_event(db_session, test_user, "Other")
    _due(db_session, allowed, "in", date(2025, 5, 2))
    _due(db_session, other, "out", date(2025, 5, 2))
    start, end = date(2025, 5, 1), date(2025, 5, 31)

    scoped = todo_service.list_due_todos(
        db_session, test_user.id, start, end, {allowed.company_id}
    )

    assert [t.title for t in scoped] == ["in"]
    assert (
        todo_service.list_due_todos(db_session, test_user.id, start, end, set()) == []
    )
