# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for dashboard_service."""

from datetime import date, datetime, timedelta
from decimal import Decimal

from src.models import Company, Event, Expense, Todo
from src.models.enums import (
    CompanyType,
    ExpenseCategory,
    PaymentType,
)
from src.services import dashboard_service as service

TODAY = date.today()


def make_company(db_session, name: str = "Acme") -> Company:
    company = Company(name=name, type=CompanyType.EMPLOYER)
    db_session.add(company)
    db_session.commit()
    return company


def make_event(db_session, user, company, name, start_offset, end_offset, **kwargs):
    event = Event(
        user_id=user.id,
        company_id=company.id,
        name=name,
        start_date=TODAY + timedelta(days=start_offset),
        end_date=TODAY + timedelta(days=end_offset),
        **kwargs,
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    return event


def add_expense(db_session, event, amount, category=ExpenseCategory.MEALS, days=-1):
    expense = Expense(
        event_id=event.id,
        date=TODAY + timedelta(days=days),
        amount=Decimal(amount),
        currency="EUR",
        converted_amount=Decimal(amount),
        payment_type=PaymentType.CASH,
        category=category,
    )
    db_session.add(expense)
    db_session.commit()
    return expense


def test_events_by_status_counts_computed_status(db_session, test_user, second_user):
    company = make_company(db_session)
    make_event(db_session, test_user, company, "Future", 5, 6)
    make_event(db_session, test_user, company, "Future2", 8, 9)
    make_event(db_session, test_user, company, "Now", -1, 1)
    make_event(db_session, test_user, company, "Old", -10, -9)
    make_event(db_session, second_user, company, "Foreign", 5, 6)

    result = service.get_events_by_status(db_session, test_user.id)

    assert (result.upcoming, result.active, result.past) == (2, 1, 1)


def test_events_by_status_empty(db_session, test_user):
    result = service.get_events_by_status(db_session, test_user.id)

    assert (result.upcoming, result.active, result.past) == (0, 0, 0)


def test_upcoming_events_sorted_limited_and_scoped(db_session, test_user, second_user):
    company = make_company(db_session)
    make_event(db_session, test_user, company, "Later", 10, 11)
    make_event(db_session, test_user, company, "Soon", 2, 3)
    make_event(db_session, test_user, company, "Today", 0, 1)
    make_event(db_session, test_user, company, "Past", -5, -4)
    make_event(db_session, second_user, company, "Foreign", 1, 2)

    events = service.get_upcoming_events(db_session, test_user.id, limit=2)

    assert [e.name for e in events] == ["Today", "Soon"]
    assert [e.days_until for e in events] == [0, 2]
    assert events[0].company_name == "Acme"


def test_events_needing_reports_filters_and_sums(db_session, test_user):
    company = make_company(db_session)
    needs = make_event(db_session, test_user, company, "Needs", -10, -9)
    sent = make_event(
        db_session,
        test_user,
        company,
        "Sent",
        -10,
        -9,
        report_sent_at=datetime.now(),
    )
    no_expenses = make_event(db_session, test_user, company, "Empty", -10, -9)
    current = make_event(db_session, test_user, company, "Current", -1, 1)
    add_expense(db_session, needs, "10.50")
    add_expense(db_session, needs, "4.50")
    add_expense(db_session, sent, "3.00")
    add_expense(db_session, current, "3.00")

    result = service.get_events_needing_reports(db_session, test_user.id)

    assert [r.event_name for r in result] == ["Needs"]
    assert result[0].event_id == needs.id
    assert result[0].expense_count == 2
    assert result[0].total_amount == Decimal("15.00")
    assert result[0].company_name == "Acme"
    assert no_expenses.id not in [r.event_id for r in result]


def test_incomplete_todos_exclude_past_and_completed_sorted_nulls_last(
    db_session, test_user
):
    company = make_company(db_session)
    live = make_event(db_session, test_user, company, "Live", 1, 2)
    past = make_event(db_session, test_user, company, "Past", -5, -4)
    db_session.add_all(
        [
            Todo(event_id=live.id, title="NoDate", completed=False),
            Todo(
                event_id=live.id,
                title="Late",
                completed=False,
                due_date=TODAY - timedelta(days=1),
            ),
            Todo(
                event_id=live.id,
                title="Soon",
                completed=False,
                due_date=TODAY + timedelta(days=1),
            ),
            Todo(event_id=live.id, title="Done", completed=True),
            Todo(event_id=past.id, title="PastTodo", completed=False),
        ]
    )
    db_session.commit()

    result = service.get_incomplete_todos(db_session, test_user.id)

    assert [t.title for t in result] == ["Late", "Soon", "NoDate"]
    assert [t.is_overdue for t in result] == [True, False, False]
    assert {t.event_name for t in result} == {"Live"}


def test_incomplete_todos_respects_limit(db_session, test_user):
    company = make_company(db_session)
    live = make_event(db_session, test_user, company, "Live", 1, 2)
    db_session.add_all(
        [Todo(event_id=live.id, title=f"T{i}", completed=False) for i in range(3)]
    )
    db_session.commit()

    assert len(service.get_incomplete_todos(db_session, test_user.id, limit=2)) == 2


def test_expense_summary_groups_by_category_and_period(db_session, test_user):
    company = make_company(db_session)
    event = make_event(db_session, test_user, company, "Trip", -5, -4)
    add_expense(db_session, event, "75.00", ExpenseCategory.MEALS)
    add_expense(db_session, event, "25.00", ExpenseCategory.TRAVEL)
    add_expense(db_session, event, "99.00", ExpenseCategory.OTHER, days=-200)

    summary = service.get_expense_summary(db_session, test_user.id)

    assert summary.total == Decimal("100.00")
    assert summary.period_days == 90
    assert [c.category for c in summary.by_category] == ["meals", "travel"]
    assert [c.percentage for c in summary.by_category] == [75.0, 25.0]
    assert summary.base_currency == "EUR"


def test_expense_summary_empty_has_zero_total(db_session, test_user):
    summary = service.get_expense_summary(db_session, test_user.id)

    assert summary.total == 0
    assert summary.by_category == []


def test_dashboard_summary_combines_sections(db_session, test_user):
    company = make_company(db_session)
    make_event(db_session, test_user, company, "Future", 3, 4)

    summary = service.get_dashboard_summary(db_session, test_user.id)

    assert summary.events_by_status.upcoming == 1
    assert [e.name for e in summary.upcoming_events] == ["Future"]
    assert summary.events_needing_reports == []
    assert summary.incomplete_todos == []
    assert summary.expense_summary.total == 0
