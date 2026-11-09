# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for todo_template_service."""

import uuid
from datetime import date

from src.models import Company, Event, Todo, TodoTemplate
from src.models.enums import CompanyType, OffsetReference, TodoCategory
from src.schemas.todo_template import TodoTemplateCreate, TodoTemplateUpdate
from src.services import todo_template_service as service


def make_event(db_session, user) -> Event:
    company = Company(name="Acme", type=CompanyType.EMPLOYER)
    db_session.add(company)
    db_session.commit()
    event = Event(
        user_id=user.id,
        company_id=company.id,
        name="Trip",
        start_date=date(2025, 6, 10),
        end_date=date(2025, 6, 12),
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    return event


def make_template(db_session, user, title="Task", set_name="Set", **kwargs):
    return service.create_template(
        db_session,
        user.id,
        TodoTemplateCreate(title=title, template_set_name=set_name, **kwargs),
    )


def test_calculate_due_date_uses_reference(db_session, test_user):
    start = make_template(
        db_session,
        test_user,
        days_offset=-3,
        offset_reference=OffsetReference.START_DATE,
    )
    end = make_template(
        db_session,
        test_user,
        days_offset=7,
        offset_reference=OffsetReference.END_DATE,
    )

    assert service.calculate_due_date(
        start, date(2025, 6, 10), date(2025, 6, 12)
    ) == date(2025, 6, 7)
    assert service.calculate_due_date(
        end, date(2025, 6, 10), date(2025, 6, 12)
    ) == date(2025, 6, 19)


def test_create_template_is_user_owned_not_global(db_session, test_user):
    template = make_template(db_session, test_user)

    assert template.is_global is False
    assert template.user_id == test_user.id
    assert service.get_template_by_id(db_session, template.id) == template
    assert service.get_template_by_id(db_session, uuid.uuid4()) is None


def test_templates_for_user_include_global_and_own_only(
    db_session, test_user, second_user
):
    service.seed_default_templates(db_session)
    own = make_template(db_session, test_user, "Mine", "Own")
    make_template(db_session, second_user, "Theirs", "Other")

    templates = service.get_templates_for_user(db_session, test_user.id)

    assert own in templates
    assert all(t.is_global or t.user_id == test_user.id for t in templates)
    assert "Theirs" not in {t.title for t in templates}
    assert len(templates) == 9


def test_template_sets_group_by_name_and_flag_global(db_session, test_user):
    service.seed_default_templates(db_session)
    make_template(db_session, test_user, "Mine", "Business Trip")
    make_template(db_session, test_user, "Solo", "Solo Set")

    sets = {
        s.name: s for s in service.get_template_sets_for_user(db_session, test_user.id)
    }

    assert set(sets) == {"Business Trip", "Conference Event", "Solo Set"}
    assert sets["Conference Event"].is_global is True
    # Mixed set (global plus a user template) is not global.
    assert sets["Business Trip"].is_global is False
    assert sets["Solo Set"].is_global is False
    assert len(sets["Business Trip"].templates) == 5


def test_template_sets_with_computed_dates(db_session, test_user):
    event = make_event(db_session, test_user)
    make_template(
        db_session,
        test_user,
        "Book",
        "Set",
        days_offset=-5,
        offset_reference=OffsetReference.START_DATE,
    )

    sets = service.get_template_sets_with_computed_dates(
        db_session, test_user.id, event.id
    )

    assert len(sets) == 1
    assert sets[0].templates[0].computed_due_date == date(2025, 6, 5)


def test_template_sets_with_computed_dates_unknown_event(db_session, test_user):
    make_template(db_session, test_user)

    assert (
        service.get_template_sets_with_computed_dates(
            db_session, test_user.id, uuid.uuid4()
        )
        == []
    )


def test_update_template_changes_set_fields_only(db_session, test_user):
    template = make_template(db_session, test_user, "Old", "Set", days_offset=2)

    updated = service.update_template(
        db_session, template, TodoTemplateUpdate(title="New")
    )

    assert updated.title == "New"
    assert updated.days_offset == 2
    assert updated.template_set_name == "Set"


def test_delete_template(db_session, test_user):
    template = make_template(db_session, test_user)
    template_id = template.id

    service.delete_template(db_session, template)

    assert service.get_template_by_id(db_session, template_id) is None


def test_apply_templates_creates_todos_with_due_dates(db_session, test_user):
    event = make_event(db_session, test_user)
    first = make_template(
        db_session,
        test_user,
        "First",
        days_offset=-2,
        category=TodoCategory.TRAVEL,
    )
    second = make_template(
        db_session,
        test_user,
        "Second",
        days_offset=1,
        offset_reference=OffsetReference.END_DATE,
    )

    count, ids = service.apply_templates_to_event(
        db_session, event.id, [first.id, second.id]
    )

    assert count == 2
    todos = {t.title: t for t in db_session.query(Todo).filter(Todo.id.in_(ids))}
    assert todos["First"].due_date == date(2025, 6, 8)
    assert todos["First"].category == TodoCategory.TRAVEL
    assert todos["Second"].due_date == date(2025, 6, 13)
    assert all(t.event_id == event.id and not t.completed for t in todos.values())


def test_apply_templates_unknown_event_creates_nothing(db_session, test_user):
    template = make_template(db_session, test_user)

    assert service.apply_templates_to_event(
        db_session, uuid.uuid4(), [template.id]
    ) == (0, [])
    assert db_session.query(Todo).count() == 0


def test_seed_default_templates_is_idempotent(db_session):
    assert service.seed_default_templates(db_session) == 8
    assert service.seed_default_templates(db_session) == 0
    assert db_session.query(TodoTemplate).count() == 8
