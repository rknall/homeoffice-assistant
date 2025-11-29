# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Expense API endpoints."""

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

router = APIRouter()


@router.get("/{event_id}/expenses", response_model=list[ExpenseResponse])
def list_expenses(
    event_id: str,
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
def create_expense(
    event_id: str,
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
    return ExpenseResponse.model_validate(expense)


@router.get("/{event_id}/expenses/{expense_id}", response_model=ExpenseResponse)
def get_expense(
    event_id: str,
    expense_id: str,
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
def update_expense(
    event_id: str,
    expense_id: str,
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

    expense = expense_service.update_expense(db, expense, data)
    return ExpenseResponse.model_validate(expense)


@router.delete("/{event_id}/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    event_id: str,
    expense_id: str,
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
    event_id: str,
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

    count = expense_service.bulk_update_payment_type(db, data.expense_ids, data.payment_type)
    return {"updated": count}


@router.get("/{event_id}/expenses/summary")
def get_expense_summary(
    event_id: str,
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
