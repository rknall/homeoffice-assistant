# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Expense API endpoints."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.models import User
from src.models.enums import ExpenseStatus
from src.schemas.expense import (
    ExpenseBulkUpdate,
    ExpenseCreate,
    ExpenseResponse,
    ExpenseUpdate,
)
from src.services import event_service, expense_service
from src.services.currency_service import CurrencyService, CurrencyServiceError

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/{event_id}/expenses", response_model=list[ExpenseResponse])
def list_expenses(
    event_id: uuid.UUID,
    expense_status: ExpenseStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ExpenseResponse]:
    """List expenses for an event."""
    # Verify user owns the event
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    expenses = expense_service.get_expenses(db, event_id, expense_status)
    return [ExpenseResponse.model_validate(e) for e in expenses]


@router.post(
    "/{event_id}/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_expense(
    event_id: uuid.UUID,
    data: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpenseResponse:
    """Create a new expense for an event."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    expense = expense_service.create_expense(db, event_id, data)

    # Convert currency if different from company base currency
    base_currency = event.company.base_currency
    if expense.currency.upper() != base_currency.upper():
        currency_service = CurrencyService(db)
        try:
            result = await currency_service.convert(
                expense.amount,
                expense.currency,
                base_currency,
                expense.date,
            )
            expense.converted_amount = result.converted_amount
            expense.exchange_rate = result.exchange_rate
            expense.rate_date = result.rate_date
            db.commit()
            db.refresh(expense)
        except CurrencyServiceError as e:
            logger.warning(f"Currency conversion failed: {e}")
            # Continue without conversion - expense is still valid
        finally:
            await currency_service.close()
    else:
        # Same currency: converted = original, rate = 1.0
        expense.converted_amount = expense.amount
        expense.exchange_rate = 1
        expense.rate_date = expense.date
        db.commit()
        db.refresh(expense)

    return ExpenseResponse.model_validate(expense)


@router.get("/{event_id}/expenses/{expense_id}", response_model=ExpenseResponse)
def get_expense(
    event_id: uuid.UUID,
    expense_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpenseResponse:
    """Get a specific expense."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    expense = expense_service.get_expense_for_event(db, expense_id, event_id)
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found",
        )

    return ExpenseResponse.model_validate(expense)


@router.put("/{event_id}/expenses/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    event_id: uuid.UUID,
    expense_id: uuid.UUID,
    data: ExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpenseResponse:
    """Update an expense."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    expense = expense_service.get_expense_for_event(db, expense_id, event_id)
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found",
        )

    # Check if we need to re-convert (amount, currency, or date changed)
    needs_reconvert = (
        (data.amount is not None and data.amount != expense.amount)
        or (data.currency is not None and data.currency != expense.currency)
        or (data.date is not None and data.date != expense.date)
    )

    expense = expense_service.update_expense(db, expense, data)

    # Re-convert if needed
    if needs_reconvert:
        base_currency = event.company.base_currency
        if expense.currency.upper() != base_currency.upper():
            currency_service = CurrencyService(db)
            try:
                result = await currency_service.convert(
                    expense.amount,
                    expense.currency,
                    base_currency,
                    expense.date,
                )
                expense.converted_amount = result.converted_amount
                expense.exchange_rate = result.exchange_rate
                expense.rate_date = result.rate_date
                db.commit()
                db.refresh(expense)
            except CurrencyServiceError as e:
                logger.warning(f"Currency conversion failed: {e}")
            finally:
                await currency_service.close()
        else:
            # Same currency: converted = original, rate = 1.0
            expense.converted_amount = expense.amount
            expense.exchange_rate = 1
            expense.rate_date = expense.date
            db.commit()
            db.refresh(expense)

    return ExpenseResponse.model_validate(expense)


@router.delete(
    "/{event_id}/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_expense(
    event_id: uuid.UUID,
    expense_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete an expense."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    expense = expense_service.get_expense_for_event(db, expense_id, event_id)
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found",
        )

    expense_service.delete_expense(db, expense)


@router.post("/{event_id}/expenses/bulk-update")
def bulk_update_expenses(
    event_id: uuid.UUID,
    data: ExpenseBulkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Bulk update payment type for multiple expenses."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    count = expense_service.bulk_update_payment_type(
        db, data.expense_ids, data.payment_type
    )
    return {"updated": count}


@router.get("/{event_id}/expenses/summary")
def get_expense_summary(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get expense summary for an event."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    return expense_service.get_expense_summary(db, event_id)
