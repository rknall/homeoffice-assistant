# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Expense submission API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.models import User
from src.schemas.expense import (
    ExpenseSubmissionCreate,
    ExpenseSubmissionResponse,
    ExpenseSubmissionSummary,
)
from src.services import event_service, submission_service

router = APIRouter()


@router.get(
    "/{event_id}/submissions", response_model=list[ExpenseSubmissionResponse]
)
def list_submissions(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ExpenseSubmissionResponse]:
    """List all submissions for an event."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    submissions = submission_service.get_submissions(db, event_id)
    return [ExpenseSubmissionResponse.model_validate(s) for s in submissions]


@router.post(
    "/{event_id}/submissions",
    response_model=ExpenseSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_submission(
    event_id: uuid.UUID,
    data: ExpenseSubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpenseSubmissionResponse:
    """Create a new expense submission record.

    This creates a submission record and optionally marks the included
    expenses as SUBMITTED.
    """
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    if not data.expense_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one expense ID is required",
        )

    try:
        submission = submission_service.create_submission(
            db,
            event_id,
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
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpenseSubmissionSummary:
    """Get submission summary for an event.

    Returns totals for submitted, reimbursed, pending, and awaiting reimbursement.
    """
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    summary = submission_service.get_submission_summary(db, event_id)
    return ExpenseSubmissionSummary(**summary)


@router.get(
    "/{event_id}/submissions/{submission_id}", response_model=ExpenseSubmissionResponse
)
def get_submission(
    event_id: uuid.UUID,
    submission_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpenseSubmissionResponse:
    """Get a specific submission by ID."""
    event = event_service.get_event_for_user(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    submission = submission_service.get_submission(db, submission_id)
    if not submission or submission.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )

    return ExpenseSubmissionResponse.model_validate(submission)
