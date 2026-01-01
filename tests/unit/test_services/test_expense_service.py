# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for expense_service."""

from datetime import date
from decimal import Decimal

from src.models import Company, Event, User
from src.models.enums import (
    CompanyType,
    ExpenseCategory,
    ExpenseStatus,
    PaymentType,
)
from src.schemas.expense import ExpenseCreate, ExpenseUpdate
from src.security import get_password_hash
from src.services import expense_service


def create_user(db_session) -> User:
    user = User(
        username="expenseuser",
        email="expense@example.com",
        hashed_password=get_password_hash("Secret123!"),
        is_admin=False,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_company(db_session) -> Company:
    company = Company(name="Acme", type=CompanyType.EMPLOYER)
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


def create_event(db_session) -> Event:
    user = create_user(db_session)
    company = create_company(db_session)
    event = Event(
        user_id=user.id,
        company_id=company.id,
        name="Expense Event",
        description="Desc",
        start_date=date(2025, 5, 1),
        end_date=date(2025, 5, 2),
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    return event


def create_expense(db_session, event_id: str, amount: Decimal = Decimal("10.00")):
    data = ExpenseCreate(
        date=date(2025, 5, 1),
        amount=amount,
        currency="EUR",
        payment_type=PaymentType.CASH,
        category=ExpenseCategory.TRAVEL,
        description="Taxi",
    )
    return expense_service.create_expense(db_session, event_id, data)


def test_create_and_get_expense(db_session):
    event = create_event(db_session)
    expense = create_expense(db_session, event.id)

    fetched = expense_service.get_expense(db_session, expense.id)
    assert fetched == expense
    fetched_event = expense_service.get_expense_for_event(
        db_session, expense.id, event.id
    )
    assert fetched_event == expense
    all_expenses = expense_service.get_expenses(db_session, event.id)
    assert len(all_expenses) == 1


def test_update_and_delete_expense(db_session):
    event = create_event(db_session)
    expense = create_expense(db_session, event.id)

    update = ExpenseUpdate(
        amount=Decimal("20.00"),
        payment_type=PaymentType.CREDIT_CARD,
        status=ExpenseStatus.SUBMITTED,
        category=ExpenseCategory.MEALS,
        currency="USD",
        description="Dinner",
        paperless_doc_id=123,
    )

    updated = expense_service.update_expense(db_session, expense, update)
    assert updated.amount == Decimal("20.00")
    assert updated.payment_type == PaymentType.CREDIT_CARD
    assert updated.paperless_doc_id == 123

    expense_service.delete_expense(db_session, updated)
    assert expense_service.get_expense(db_session, updated.id) is None


def test_bulk_update_payment_type(db_session):
    event = create_event(db_session)
    exp1 = create_expense(db_session, event.id)
    exp2 = create_expense(db_session, event.id, amount=Decimal("5.00"))

    updated = expense_service.bulk_update_payment_type(
        db_session,
        [exp1.id, exp2.id],
        PaymentType.COMPANY_CARD,
    )

    assert updated == 2
    db_session.refresh(exp1)
    db_session.refresh(exp2)
    assert exp1.payment_type == PaymentType.COMPANY_CARD


def test_expense_summary(db_session):
    event = create_event(db_session)
    create_expense(db_session, event.id, amount=Decimal("3.00"))
    create_expense(db_session, event.id, amount=Decimal("2.00"))

    summary = expense_service.get_expense_summary(db_session, event.id)

    assert summary["total"] == 5.0
    assert summary["count"] == 2
    assert "travel" in summary["by_category"]
