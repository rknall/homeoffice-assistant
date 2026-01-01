# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Expense service."""

import logging
import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from src.models import Expense
from src.models.enums import ExpenseStatus, PaymentType
from src.plugins.events import AppEvent, event_bus
from src.schemas.expense import ExpenseCreate, ExpenseUpdate

logger = logging.getLogger(__name__)


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
    from src.services.currency_service import CurrencyService, CurrencyServiceError

    # Filter to expenses needing conversion
    needs_conversion = [e for e in expenses if e.converted_amount is None]
    if not needs_conversion:
        return expenses

    service = CurrencyService(db)
    try:
        for expense in needs_conversion:
            if expense.currency.upper() == base_currency.upper():
                # Same currency - no conversion needed
                expense.converted_amount = expense.amount
                expense.exchange_rate = Decimal("1.0")
                expense.rate_date = expense.date
            else:
                # Different currency - fetch rate and convert
                try:
                    result = await service.convert(
                        expense.amount,
                        expense.currency,
                        base_currency,
                        expense.date,
                    )
                    expense.converted_amount = result.converted_amount
                    expense.exchange_rate = result.exchange_rate
                    expense.rate_date = result.rate_date
                except CurrencyServiceError as e:
                    logger.warning(
                        f"Failed to convert expense {expense.id}: {e}"
                    )
                    # Skip this expense, leave converted_amount as None
                    continue

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
    db.delete(expense)
    db.commit()


def bulk_update_payment_type(
    db: Session,
    expense_ids: list[uuid.UUID],
    payment_type: PaymentType,
) -> int:
    """Bulk update payment type for multiple expenses. Returns count updated."""
    count = (
        db.query(Expense)
        .filter(Expense.id.in_(expense_ids))
        .update({"payment_type": payment_type}, synchronize_session=False)
    )
    db.commit()
    return count


def bulk_update_status(
    db: Session,
    expense_ids: list[uuid.UUID],
    status: ExpenseStatus,
    rejection_reason: str | None = None,
) -> int:
    """Bulk update status for multiple expenses.

    Args:
        db: Database session
        expense_ids: List of expense IDs to update
        status: New status to set
        rejection_reason: Required if status is REJECTED

    Returns:
        Count of updated expenses
    """
    from datetime import datetime

    update_values: dict = {"status": status}

    # Set submitted_at when marking as submitted
    if status == ExpenseStatus.SUBMITTED:
        update_values["submitted_at"] = datetime.utcnow()
        update_values["rejection_reason"] = None  # Clear any previous rejection

    # Set rejection reason when marking as rejected
    elif status == ExpenseStatus.REJECTED:
        update_values["rejection_reason"] = rejection_reason

    # Clear rejection reason when moving to other statuses
    elif status in (ExpenseStatus.PENDING, ExpenseStatus.REIMBURSED):
        update_values["rejection_reason"] = None

    count = (
        db.query(Expense)
        .filter(Expense.id.in_(expense_ids))
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


def get_pending_expenses(db: Session, event_id: uuid.UUID) -> list[Expense]:
    """Get all pending expenses for an event."""
    return (
        db.query(Expense)
        .filter(
            Expense.event_id == event_id,
            Expense.status == ExpenseStatus.PENDING,
        )
        .order_by(Expense.date)
        .all()
    )


def get_expense_summary(db: Session, event_id: uuid.UUID) -> dict:
    """Get expense summary for an event.

    Uses converted_amount for proper multi-currency totals.
    Returns the event's company base_currency and conversion info.
    """
    from src.models import Event

    expenses = get_expenses(db, event_id)

    # Get the event's company base currency
    event = db.query(Event).filter(Event.id == event_id).first()
    base_currency = event.company.base_currency if event and event.company else "EUR"

    # Sum converted amounts (or raw amount if no conversion yet)
    total = sum(
        e.converted_amount if e.converted_amount is not None else e.amount
        for e in expenses
    )
    by_category = {}
    by_payment_type = {}

    # Track currencies that were converted
    converted_currencies: set[str] = set()

    for expense in expenses:
        # Use converted amount for aggregations
        amount = float(
            expense.converted_amount
            if expense.converted_amount is not None
            else expense.amount
        )

        cat = expense.category.value
        by_category[cat] = by_category.get(cat, 0) + amount

        pt = expense.payment_type.value
        by_payment_type[pt] = by_payment_type.get(pt, 0) + amount

        # Track if this expense was converted from a different currency
        if expense.currency.upper() != base_currency.upper():
            converted_currencies.add(expense.currency.upper())

    return {
        "total": float(total),
        "count": len(expenses),
        "by_category": by_category,
        "by_payment_type": by_payment_type,
        "currency": base_currency,
        "converted_from": (
            sorted(converted_currencies) if converted_currencies else None
        ),
    }
