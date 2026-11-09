# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Expense API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import require_event_permission
from src.database import get_db
from src.models import Event
from src.models.enums import ExpenseStatus
from src.schemas.expense import (
    ExpenseBulkStatusResult,
    ExpenseBulkStatusUpdate,
    ExpenseCreate,
    ExpenseResponse,
    ExpenseUpdate,
)
from src.services import expense_service, settings_service

router = APIRouter()


@router.get("/{event_id}/expenses", response_model=list[ExpenseResponse])
async def list_expenses(
    expense_status: ExpenseStatus | None = None,
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("expense.view")),
) -> list[ExpenseResponse]:
    """List expenses for an event."""
    # Verify user owns the event
    expenses = expense_service.get_expenses(db, event.id, expense_status)

    # Auto-convert any expenses missing conversion data
    base_currency = settings_service.get_base_currency(db)
    await expense_service.ensure_expense_conversions(db, expenses, base_currency)

    return [ExpenseResponse.model_validate(e) for e in expenses]


@router.post(
    "/{event_id}/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_expense(
    data: ExpenseCreate,
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("expense.manage")),
) -> ExpenseResponse:
    """Create a new expense for an event."""
    expense = expense_service.create_expense(db, event.id, data)

    base_currency = settings_service.get_base_currency(db)
    await expense_service.convert_expense(db, expense, base_currency)
    db.commit()
    db.refresh(expense)

    return ExpenseResponse.model_validate(expense)


@router.get("/{event_id}/expenses/{expense_id}", response_model=ExpenseResponse)
def get_expense(
    expense_id: uuid.UUID,
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("expense.view")),
) -> ExpenseResponse:
    """Get a specific expense."""
    expense = expense_service.get_expense_for_event(db, expense_id, event.id)
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found",
        )

    return ExpenseResponse.model_validate(expense)


@router.put("/{event_id}/expenses/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: uuid.UUID,
    data: ExpenseUpdate,
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("expense.manage")),
) -> ExpenseResponse:
    """Update an expense."""
    expense = expense_service.get_expense_for_event(db, expense_id, event.id)
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

    if needs_reconvert:
        base_currency = settings_service.get_base_currency(db)
        await expense_service.convert_expense(db, expense, base_currency)
        db.commit()
        db.refresh(expense)

    return ExpenseResponse.model_validate(expense)


@router.delete(
    "/{event_id}/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_expense(
    expense_id: uuid.UUID,
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("expense.manage")),
) -> None:
    """Delete an expense."""
    expense = expense_service.get_expense_for_event(db, expense_id, event.id)
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found",
        )

    expense_service.delete_expense(db, expense)


@router.post("/{event_id}/expenses/bulk-status", response_model=ExpenseBulkStatusResult)
def bulk_update_expense_status(
    data: ExpenseBulkStatusUpdate,
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("expense.manage")),
) -> ExpenseBulkStatusResult:
    """Bulk update status for multiple expenses."""
    # Validate rejection reason is provided for REJECTED status
    if data.status == ExpenseStatus.REJECTED and not data.rejection_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rejection reason is required when marking as rejected",
        )

    count = expense_service.bulk_update_status(
        db, event.id, data.expense_ids, data.status, data.rejection_reason
    )
    return ExpenseBulkStatusResult(updated=count)
