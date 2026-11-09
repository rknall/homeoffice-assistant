# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Expense service."""

import logging
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from src.models import Expense
from src.models.enums import ExpenseStatus
from src.plugins.events import AppEvent, event_bus
from src.schemas.expense import ExpenseCreate, ExpenseUpdate
from src.utils.time import utc_now

if TYPE_CHECKING:
    from src.services.currency_service import CurrencyService

logger = logging.getLogger(__name__)


async def convert_expense(
    db: Session,
    expense: Expense,
    base_currency: str,
    service: CurrencyService | None = None,
) -> bool:
    """Convert one expense to the base currency, in place, without committing.

    Same-currency expenses get a 1:1 conversion. When the rate lookup fails,
    any earlier conversion is cleared, so a stale converted amount is never
    kept after the amount, currency or date changed.

    Args:
        db: Database session (used to create a currency service if none given).
        expense: Expense to convert.
        base_currency: Target currency for conversion.
        service: Optional shared currency service; the caller closes it.

    Returns:
        True when the expense now holds a conversion, False when it failed.
    """
    from src.services.currency_service import CurrencyService, CurrencyServiceError

    if expense.currency.upper() == base_currency.upper():
        expense.converted_amount = expense.amount
        expense.exchange_rate = Decimal("1.0")
        expense.rate_date = expense.date
        return True

    owns_service = service is None
    currency_service = service or CurrencyService(db)
    try:
        result = await currency_service.convert(
            expense.amount,
            expense.currency,
            base_currency,
            expense.date,
        )
    except CurrencyServiceError as e:
        logger.warning(f"Failed to convert expense {expense.id}: {e}")
        expense.converted_amount = None
        expense.exchange_rate = None
        expense.rate_date = None
        return False
    finally:
        if owns_service:
            await currency_service.close()

    expense.converted_amount = result.converted_amount
    expense.exchange_rate = result.exchange_rate
    expense.rate_date = result.rate_date
    return True


async def ensure_expense_conversions(
    db: Session,
    expenses: list[Expense],
    base_currency: str,
) -> list[Expense]:
    """Auto-convert expenses missing converted_amount.

    Converts expenses in-place and persists to DB. Safe to call multiple times -
    already-converted expenses are skipped.

    Args:
        db: Database session.
        expenses: List of expenses to check and convert.
        base_currency: Target currency for conversion.

    Returns:
        The same list of expenses, now with conversion data populated.
    """
    from src.services.currency_service import CurrencyService

    needs_conversion = [e for e in expenses if e.converted_amount is None]
    if not needs_conversion:
        return expenses

    service = CurrencyService(db)
    try:
        for expense in needs_conversion:
            await convert_expense(db, expense, base_currency, service)
        db.commit()
    finally:
        await service.close()

    return expenses


def get_expenses(
    db: Session,
    event_id: uuid.UUID,
    status: ExpenseStatus | None = None,
) -> list[Expense]:
    """Get expenses for an event."""
    query = db.query(Expense).filter(Expense.event_id == event_id)
    if status:
        query = query.filter(Expense.status == status)
    return query.order_by(Expense.date).all()


def get_expense(db: Session, expense_id: uuid.UUID) -> Expense | None:
    """Get an expense by ID."""
    return db.query(Expense).filter(Expense.id == expense_id).first()


def get_expense_for_event(
    db: Session,
    expense_id: uuid.UUID,
    event_id: uuid.UUID,
) -> Expense | None:
    """Get an expense that belongs to a specific event."""
    return (
        db.query(Expense)
        .filter(Expense.id == expense_id, Expense.event_id == event_id)
        .first()
    )


def create_expense(db: Session, event_id: uuid.UUID, data: ExpenseCreate) -> Expense:
    """Create a new expense."""
    expense = Expense(
        event_id=event_id,
        paperless_doc_id=data.paperless_doc_id,
        date=data.date,
        amount=data.amount,
        currency=data.currency,
        payment_type=data.payment_type,
        category=data.category,
        description=data.description,
        status=ExpenseStatus.PENDING,
        original_filename=data.original_filename,
        is_private=data.is_private,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)

    # Publish expense created event
    event_bus.publish_sync(
        AppEvent.EXPENSE_CREATED,
        {
            "expense_id": str(expense.id),
            "event_id": str(expense.event_id),
            "amount": float(expense.amount),
            "currency": expense.currency,
            "category": expense.category.value,
        },
    )

    return expense


def update_expense(db: Session, expense: Expense, data: ExpenseUpdate) -> Expense:
    """Update an existing expense."""
    if data.date is not None:
        expense.date = data.date
    if data.amount is not None:
        expense.amount = data.amount
    if data.currency is not None:
        expense.currency = data.currency
    if data.payment_type is not None:
        expense.payment_type = data.payment_type
    if data.category is not None:
        expense.category = data.category
    if data.description is not None:
        expense.description = data.description
    if data.status is not None:
        expense.status = data.status
    if data.paperless_doc_id is not None:
        expense.paperless_doc_id = data.paperless_doc_id
    if data.original_filename is not None:
        expense.original_filename = data.original_filename
    if data.is_private is not None:
        expense.is_private = data.is_private

    db.commit()
    db.refresh(expense)

    # Publish expense updated event
    event_bus.publish_sync(
        AppEvent.EXPENSE_UPDATED,
        {
            "expense_id": str(expense.id),
            "event_id": str(expense.event_id),
            "amount": float(expense.amount),
            "currency": expense.currency,
        },
    )

    return expense


def delete_expense(db: Session, expense: Expense) -> None:
    """Delete an expense."""
    payload = {"expense_id": str(expense.id), "event_id": str(expense.event_id)}
    db.delete(expense)
    db.commit()

    event_bus.publish_sync(AppEvent.EXPENSE_DELETED, payload)


def bulk_update_status(
    db: Session,
    event_id: uuid.UUID,
    expense_ids: list[uuid.UUID],
    status: ExpenseStatus,
    rejection_reason: str | None = None,
) -> int:
    """Bulk update status for multiple expenses of one event.

    Ids that belong to another event are ignored, so a caller allowed to
    manage one event cannot change expenses elsewhere.

    Args:
        db: Database session
        event_id: Event the expenses must belong to
        expense_ids: List of expense IDs to update
        status: New status to set
        rejection_reason: Required if status is REJECTED

    Returns:
        Count of updated expenses
    """
    update_values: dict = {"status": status}

    # Set submitted_at when marking as submitted
    if status == ExpenseStatus.SUBMITTED:
        update_values["submitted_at"] = utc_now()
        update_values["rejection_reason"] = None  # Clear any previous rejection

    # Set rejection reason when marking as rejected
    elif status == ExpenseStatus.REJECTED:
        update_values["rejection_reason"] = rejection_reason

    # Clear rejection reason when moving to other statuses
    elif status in (ExpenseStatus.PENDING, ExpenseStatus.REIMBURSED):
        update_values["rejection_reason"] = None

    count = (
        db.query(Expense)
        .filter(Expense.id.in_(expense_ids), Expense.event_id == event_id)
        .update(update_values, synchronize_session=False)
    )
    db.commit()
    return count


def get_expenses_by_ids(
    db: Session,
    expense_ids: list[uuid.UUID],
) -> list[Expense]:
    """Get expenses by a list of IDs."""
    return db.query(Expense).filter(Expense.id.in_(expense_ids)).all()
