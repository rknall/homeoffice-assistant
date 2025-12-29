# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Dashboard service for aggregated summary data."""

import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import case, func
from sqlalchemy.orm import Session, joinedload

from src.models import Event, Expense, Todo
from src.schemas.dashboard import (
    DashboardSummary,
    EventNeedingReport,
    EventsByStatus,
    ExpenseByCategory,
    ExpenseSummary,
    IncompleteTodo,
    UpcomingEvent,
)


def get_events_by_status(db: Session, user_id: uuid.UUID) -> EventsByStatus:
    """Get count of events by computed status for a user.

    Status is computed from dates:
    - UPCOMING: start_date > today
    - ACTIVE: start_date <= today <= end_date
    - PAST: end_date < today
    """
    today = date.today()

    # Compute status using SQL CASE expression
    computed_status = case(
        (Event.start_date > today, "upcoming"),
        (Event.end_date < today, "past"),
        else_="active",
    )

    counts = (
        db.query(computed_status.label("status"), func.count(Event.id))
        .filter(Event.user_id == user_id)
        .group_by(computed_status)
        .all()
    )

    result = EventsByStatus()
    for status, count in counts:
        if status == "upcoming":
            result.upcoming = count
        elif status == "active":
            result.active = count
        elif status == "past":
            result.past = count

    return result


def get_upcoming_events(
    db: Session,
    user_id: uuid.UUID,
    limit: int = 5,
) -> list[UpcomingEvent]:
    """Get upcoming events (start_date >= today) sorted by start_date."""
    today = date.today()

    events = (
        db.query(Event)
        .options(joinedload(Event.company))
        .filter(Event.user_id == user_id)
        .filter(Event.start_date >= today)
        .order_by(Event.start_date.asc())
        .limit(limit)
        .all()
    )

    return [
        UpcomingEvent(
            id=event.id,
            name=event.name,
            company_name=event.company.name if event.company else None,
            start_date=event.start_date,
            end_date=event.end_date,
            city=event.city,
            country=event.country,
            days_until=(event.start_date - today).days,
        )
        for event in events
    ]


def get_events_needing_reports(
    db: Session,
    user_id: uuid.UUID,
    limit: int = 5,
) -> list[EventNeedingReport]:
    """Get past events that have expenses and haven't had a report sent.

    Past status is computed: end_date < today
    Events are excluded if report_sent_at is set.
    """
    today = date.today()

    # Query past events (end_date < today) with their expense aggregates
    # Exclude events where report has already been sent
    results = (
        db.query(
            Event.id,
            Event.name,
            Event.company_id,
            func.count(Expense.id).label("expense_count"),
            func.sum(Expense.amount).label("total_amount"),
            func.min(Expense.currency).label("currency"),
        )
        .join(Expense, Event.id == Expense.event_id)
        .filter(Event.user_id == user_id)
        .filter(Event.end_date < today)  # Past events: end_date < today
        .filter(Event.report_sent_at.is_(None))  # Report not yet sent
        .group_by(Event.id, Event.name, Event.company_id)
        .having(func.count(Expense.id) > 0)
        .order_by(Event.end_date.desc())
        .limit(limit)
        .all()
    )

    # Get company names for the events
    event_ids = [r.id for r in results]
    events_with_company = (
        db.query(Event)
        .options(joinedload(Event.company))
        .filter(Event.id.in_(event_ids))
        .all()
    )
    company_names = {
        e.id: e.company.name if e.company else None for e in events_with_company
    }

    return [
        EventNeedingReport(
            event_id=r.id,
            event_name=r.name,
            company_name=company_names.get(r.id),
            expense_count=r.expense_count,
            total_amount=r.total_amount or Decimal(0),
            currency=r.currency or "EUR",
        )
        for r in results
    ]


def get_incomplete_todos(
    db: Session,
    user_id: uuid.UUID,
    limit: int = 10,
) -> list[IncompleteTodo]:
    """Get incomplete todos across all non-past events, sorted by due_date.

    Non-past means: end_date >= today (upcoming or active events).
    """
    today = date.today()

    todos = (
        db.query(Todo)
        .join(Event, Todo.event_id == Event.id)
        .filter(Event.user_id == user_id)
        .filter(Event.end_date >= today)  # Non-past events: end_date >= today
        .filter(Todo.completed.is_(False))
        .order_by(
            # NULLs last, then by due_date
            Todo.due_date.is_(None),
            Todo.due_date.asc(),
        )
        .limit(limit)
        .all()
    )

    # Get event names
    event_ids = list({t.event_id for t in todos})
    events = db.query(Event).filter(Event.id.in_(event_ids)).all()
    event_names = {e.id: e.name for e in events}

    return [
        IncompleteTodo(
            id=todo.id,
            title=todo.title,
            due_date=todo.due_date,
            event_id=todo.event_id,
            event_name=event_names.get(todo.event_id, "Unknown"),
            is_overdue=todo.due_date is not None and todo.due_date < today,
        )
        for todo in todos
    ]


def get_expense_summary(
    db: Session,
    user_id: uuid.UUID,
    period_days: int = 90,
) -> ExpenseSummary:
    """Get expense summary for the last N days."""
    cutoff_date = date.today() - timedelta(days=period_days)

    # Get expenses grouped by category
    results = (
        db.query(
            Expense.category,
            func.sum(Expense.amount).label("total"),
        )
        .join(Event, Expense.event_id == Event.id)
        .filter(Event.user_id == user_id)
        .filter(Expense.date >= cutoff_date)
        .group_by(Expense.category)
        .all()
    )

    # Calculate totals
    grand_total = sum((r.total or Decimal(0)) for r in results)

    by_category = []
    for r in results:
        amount = r.total or Decimal(0)
        percentage = float(amount / grand_total * 100) if grand_total > 0 else 0.0
        by_category.append(
            ExpenseByCategory(
                category=r.category.value,
                amount=amount,
                percentage=round(percentage, 1),
            )
        )

    # Sort by amount descending
    by_category.sort(key=lambda x: x.amount, reverse=True)

    return ExpenseSummary(
        total=grand_total,
        by_category=by_category,
        period_days=period_days,
    )


def get_dashboard_summary(db: Session, user_id: uuid.UUID) -> DashboardSummary:
    """Get complete dashboard summary for a user."""
    return DashboardSummary(
        events_by_status=get_events_by_status(db, user_id),
        upcoming_events=get_upcoming_events(db, user_id),
        events_needing_reports=get_events_needing_reports(db, user_id),
        incomplete_todos=get_incomplete_todos(db, user_id),
        expense_summary=get_expense_summary(db, user_id),
    )
