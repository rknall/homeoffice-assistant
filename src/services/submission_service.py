# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Expense submission service for tracking incremental expense submissions."""

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from src.models import Event, Expense, ExpenseSubmission, ExpenseSubmissionItem
from src.models.enums import ExpenseStatus


def get_submissions(db: Session, event_id: uuid.UUID) -> list[ExpenseSubmission]:
    """Get all submissions for an event, ordered by submission date descending."""
    return (
        db.query(ExpenseSubmission)
        .filter(ExpenseSubmission.event_id == event_id)
        .order_by(ExpenseSubmission.submitted_at.desc())
        .all()
    )


def get_submission(db: Session, submission_id: uuid.UUID) -> ExpenseSubmission | None:
    """Get a specific submission by ID."""
    return (
        db.query(ExpenseSubmission)
        .filter(ExpenseSubmission.id == submission_id)
        .first()
    )


def get_submission_items(
    db: Session, submission_id: uuid.UUID
) -> list[ExpenseSubmissionItem]:
    """Get all items for a submission."""
    return (
        db.query(ExpenseSubmissionItem)
        .filter(ExpenseSubmissionItem.submission_id == submission_id)
        .all()
    )


def create_submission(
    db: Session,
    event_id: uuid.UUID,
    expense_ids: list[uuid.UUID],
    submission_method: str = "download",
    notes: str | None = None,
    mark_as_submitted: bool = True,
) -> ExpenseSubmission:
    """Create a new submission record and optionally mark expenses as submitted.

    Args:
        db: Database session
        event_id: The event ID
        expense_ids: List of expense IDs to include in this submission
        submission_method: How the report was submitted (email, download, portal)
        notes: Optional notes about this submission
        mark_as_submitted: Whether to update expense status to SUBMITTED

    Returns:
        The created ExpenseSubmission record
    """
    # Get the event for currency info
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValueError(f"Event {event_id} not found")

    base_currency = event.company.base_currency if event.company else "EUR"

    # Fetch the expenses to include
    expenses = (
        db.query(Expense)
        .filter(Expense.id.in_(expense_ids), Expense.event_id == event_id)
        .all()
    )

    if not expenses:
        raise ValueError("No valid expenses found for submission")

    # Calculate totals (using converted amount where available)
    total_amount = sum(
        e.converted_amount if e.converted_amount is not None else e.amount
        for e in expenses
    )

    submitted_at = datetime.utcnow()

    # Create the submission record
    submission = ExpenseSubmission(
        event_id=event_id,
        submitted_at=submitted_at,
        submission_method=submission_method,
        notes=notes,
        total_amount=total_amount,
        currency=base_currency,
        expense_count=len(expenses),
    )
    db.add(submission)
    db.flush()  # Get the submission ID

    # Create submission items (snapshots)
    for expense in expenses:
        item = ExpenseSubmissionItem(
            submission_id=submission.id,
            expense_id=expense.id,
            amount=expense.amount,
            converted_amount=expense.converted_amount,
            currency=expense.currency,
            description=expense.description,
        )
        db.add(item)

        # Optionally update expense status
        if mark_as_submitted:
            expense.status = ExpenseStatus.SUBMITTED
            expense.submitted_at = submitted_at

    db.commit()
    db.refresh(submission)

    return submission


def get_submission_summary(db: Session, event_id: uuid.UUID) -> dict:
    """Get summary of all submissions for an event.

    Returns:
        Dict with total_submitted, total_reimbursed, pending totals
    """
    submissions = get_submissions(db, event_id)

    total_submitted = sum(s.total_amount for s in submissions)
    submission_count = len(submissions)

    # Get reimbursed expenses to calculate reimbursed total
    reimbursed_expenses = (
        db.query(Expense)
        .filter(
            Expense.event_id == event_id,
            Expense.status == ExpenseStatus.REIMBURSED,
        )
        .all()
    )
    total_reimbursed = sum(
        e.converted_amount if e.converted_amount is not None else e.amount
        for e in reimbursed_expenses
    )

    # Get pending expenses
    pending_expenses = (
        db.query(Expense)
        .filter(
            Expense.event_id == event_id,
            Expense.status == ExpenseStatus.PENDING,
        )
        .all()
    )
    total_pending = sum(
        e.converted_amount if e.converted_amount is not None else e.amount
        for e in pending_expenses
    )

    # Get awaiting reimbursement (submitted but not yet reimbursed)
    submitted_expenses = (
        db.query(Expense)
        .filter(
            Expense.event_id == event_id,
            Expense.status == ExpenseStatus.SUBMITTED,
        )
        .all()
    )
    total_awaiting = sum(
        e.converted_amount if e.converted_amount is not None else e.amount
        for e in submitted_expenses
    )

    # Get event currency
    event = db.query(Event).filter(Event.id == event_id).first()
    currency = event.company.base_currency if event and event.company else "EUR"

    return {
        "submission_count": submission_count,
        "total_submitted": float(total_submitted),
        "total_reimbursed": float(total_reimbursed),
        "total_pending": float(total_pending),
        "total_awaiting_reimbursement": float(total_awaiting),
        "currency": currency,
    }


def get_expense_submission_history(
    db: Session, expense_id: uuid.UUID
) -> list[dict]:
    """Get submission history for a specific expense.

    Returns list of submission events in chronological order.
    """
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        return []

    # Get all submission items for this expense
    items = (
        db.query(ExpenseSubmissionItem)
        .filter(ExpenseSubmissionItem.expense_id == expense_id)
        .all()
    )

    history = []

    for item in items:
        submission = item.submission
        history.append({
            "type": "submitted",
            "date": submission.submitted_at,
            "submission_id": str(submission.id),
            "submission_method": submission.submission_method,
            "amount_at_submission": float(item.amount),
            "currency": item.currency,
        })

    # Sort by date
    history.sort(key=lambda x: x["date"])

    return history
