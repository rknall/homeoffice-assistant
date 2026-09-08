# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for submission_service."""

from datetime import date
from decimal import Decimal

from src.models import Company, Event, User
from src.models.enums import (
    CompanyType,
    ExpenseCategory,
    ExpenseStatus,
    PaymentType,
)
from src.schemas.expense import ExpenseCreate
from src.security import get_password_hash
from src.services import expense_service, submission_service


def create_event(db_session) -> Event:
    user = User(
        username="submituser",
        email="submit@example.com",
        hashed_password=get_password_hash("Secret123!"),
        is_admin=False,
        is_active=True,
    )
    company = Company(name="Acme", type=CompanyType.EMPLOYER)
    db_session.add_all([user, company])
    db_session.commit()

    event = Event(
        user_id=user.id,
        company_id=company.id,
        name="Submission Event",
        start_date=date(2025, 5, 1),
        end_date=date(2025, 5, 2),
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    return event


def create_expense(db_session, event_id, amount: str):
    return expense_service.create_expense(
        db_session,
        event_id,
        ExpenseCreate(
            date=date(2025, 5, 1),
            amount=Decimal(amount),
            currency="EUR",
            payment_type=PaymentType.CASH,
            category=ExpenseCategory.TRAVEL,
            description="Taxi",
        ),
    )


def test_summary_counts_each_expense_once_across_submissions(db_session):
    """Emailing a report and downloading it must not double the total."""
    event = create_event(db_session)
    expense = create_expense(db_session, event.id, "40.00")

    submission_service.create_submission(
        db_session, event.id, [expense.id], submission_method="email"
    )
    submission_service.create_submission(
        db_session, event.id, [expense.id], submission_method="download"
    )

    summary = submission_service.get_submission_summary(db_session, event.id)

    assert summary["submission_count"] == 2
    assert summary["total_submitted"] == 40.0


def test_summary_sums_distinct_expenses(db_session):
    event = create_event(db_session)
    first = create_expense(db_session, event.id, "40.00")
    second = create_expense(db_session, event.id, "10.00")

    submission_service.create_submission(db_session, event.id, [first.id])
    submission_service.create_submission(db_session, event.id, [first.id, second.id])

    summary = submission_service.get_submission_summary(db_session, event.id)

    assert summary["total_submitted"] == 50.0
    assert summary["total_awaiting_reimbursement"] == 50.0
    assert summary["total_pending"] == 0.0


def test_create_submission_marks_expenses_submitted(db_session):
    event = create_event(db_session)
    expense = create_expense(db_session, event.id, "25.00")

    submission = submission_service.create_submission(
        db_session, event.id, [expense.id]
    )

    assert submission.expense_count == 1
    db_session.refresh(expense)
    assert expense.status == ExpenseStatus.SUBMITTED
