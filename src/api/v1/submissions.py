# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Expense submission API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import require_event_permission
from src.database import get_db
from src.models import Event
from src.schemas.expense import (
    ExpenseSubmissionCreate,
    ExpenseSubmissionResponse,
    ExpenseSubmissionSummary,
)
from src.services import submission_service

router = APIRouter()


@router.get("/{event_id}/submissions", response_model=list[ExpenseSubmissionResponse])
def list_submissions(
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("expense.view")),
) -> list[ExpenseSubmissionResponse]:
    """List all submissions for an event."""
    submissions = submission_service.get_submissions(db, event.id)
    return [ExpenseSubmissionResponse.model_validate(s) for s in submissions]


@router.post(
    "/{event_id}/submissions",
    response_model=ExpenseSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_submission(
    data: ExpenseSubmissionCreate,
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("expense.manage")),
) -> ExpenseSubmissionResponse:
    """Create a new expense submission record.

    This creates a submission record and optionally marks the included
    expenses as SUBMITTED.
    """
    if not data.expense_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one expense ID is required",
        )

    try:
        submission = submission_service.create_submission(
            db,
            event.id,
            data.expense_ids,
            data.submission_method,
            data.notes,
            data.mark_as_submitted,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None

    return ExpenseSubmissionResponse.model_validate(submission)


# NOTE: /summary route must come BEFORE /{submission_id} to avoid "summary"
# being parsed as a UUID
@router.get("/{event_id}/submissions/summary", response_model=ExpenseSubmissionSummary)
def get_submission_summary(
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("expense.view")),
) -> ExpenseSubmissionSummary:
    """Get submission summary for an event.

    Returns totals for submitted, reimbursed, pending, and awaiting reimbursement.
    """
    summary = submission_service.get_submission_summary(db, event.id)
    return ExpenseSubmissionSummary(**summary)


@router.get(
    "/{event_id}/submissions/{submission_id}", response_model=ExpenseSubmissionResponse
)
def get_submission(
    submission_id: uuid.UUID,
    db: Session = Depends(get_db),
    event: Event = Depends(require_event_permission("expense.view")),
) -> ExpenseSubmissionResponse:
    """Get a specific submission by ID."""
    submission = submission_service.get_submission(db, submission_id)
    if not submission or submission.event_id != event.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )

    return ExpenseSubmissionResponse.model_validate(submission)
