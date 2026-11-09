# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for expense_service."""

from datetime import date
from decimal import Decimal

import pytest

from src.models import Company, Event, User
from src.models.enums import (
    CompanyType,
    ExpenseCategory,
    ExpenseStatus,
    PaymentType,
)
from src.plugins.events import AppEvent, EventPayload, event_bus
from src.schemas.expense import ExpenseCreate, ExpenseUpdate
from src.security import get_password_hash
from src.services import expense_service
from src.services.currency_service import CurrencyService, CurrencyServiceError


def create_user(db_session) -> User:
    user = User(
        username="expenseuser",
        email="expense@example.com",
        hashed_password=get_password_hash("Secret123!"),
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


def test_effective_amount_falls_back_to_amount(db_session):
    from src.models import Expense

    event = create_event(db_session)
    plain = create_expense(db_session, event.id, Decimal("10.00"))
    converted = create_expense(db_session, event.id, Decimal("20.00"))
    converted.converted_amount = Decimal("18.00")
    db_session.commit()

    assert plain.effective_amount == Decimal("10.00")
    assert converted.effective_amount == Decimal("18.00")
    rows = db_session.query(Expense.id, Expense.effective_amount).all()
    assert dict(rows) == {plain.id: Decimal("10.00"), converted.id: Decimal("18.00")}


@pytest.mark.asyncio
async def test_convert_expense_failure_clears_stale_conversion(db_session, monkeypatch):
    event = create_event(db_session)
    expense = create_expense(db_session, event.id, Decimal("10.00"))
    expense.currency = "USD"
    expense.converted_amount = Decimal("9.00")
    expense.exchange_rate = Decimal("0.9")
    expense.rate_date = date(2025, 5, 1)

    async def failing_convert(self, *args, **kwargs):
        raise CurrencyServiceError("no rate")

    monkeypatch.setattr(CurrencyService, "convert", failing_convert)

    assert await expense_service.convert_expense(db_session, expense, "EUR") is False
    assert expense.converted_amount is None
    assert expense.exchange_rate is None
    assert expense.rate_date is None


@pytest.mark.asyncio
async def test_convert_expense_same_currency_is_one_to_one(db_session):
    event = create_event(db_session)
    expense = create_expense(db_session, event.id, Decimal("10.00"))

    assert await expense_service.convert_expense(db_session, expense, "eur") is True
    assert expense.converted_amount == Decimal("10.00")
    assert expense.exchange_rate == Decimal("1.0")


def test_delete_expense_publishes_event(db_session):
    event = create_event(db_session)
    expense = create_expense(db_session, event.id)
    expense_id = str(expense.id)
    received: list[dict] = []

    def handler(payload: EventPayload) -> None:
        received.append(payload.data)

    event_bus.subscribe(AppEvent.EXPENSE_DELETED, handler)
    try:
        expense_service.delete_expense(db_session, expense)
    finally:
        event_bus.unsubscribe(AppEvent.EXPENSE_DELETED, handler)

    assert received == [{"expense_id": expense_id, "event_id": str(event.id)}]
