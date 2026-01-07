# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Company calendar API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.models import User
from src.schemas.company_calendar import (
    CompanyCalendarCreate,
    CompanyCalendarResponse,
    CompanyCalendarUpdate,
)
from src.services import company_calendar_service, company_service

router = APIRouter()


@router.get(
    "/{company_id}/calendars",
    response_model=list[CompanyCalendarResponse],
)
def list_company_calendars(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CompanyCalendarResponse]:
    """List all calendar connections for a company."""
    company = company_service.get_company(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    calendars = company_calendar_service.get_calendars(db, company_id)
    return [CompanyCalendarResponse.model_validate(c) for c in calendars]


@router.get(
    "/{company_id}/calendars/{calendar_id}",
    response_model=CompanyCalendarResponse,
)
def get_company_calendar(
    company_id: uuid.UUID,
    calendar_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyCalendarResponse:
    """Get a specific calendar connection."""
    company = company_service.get_company(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    calendar = company_calendar_service.get_calendar_by_company(
        db, company_id, calendar_id
    )
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar not found",
        )

    return CompanyCalendarResponse.model_validate(calendar)


@router.post(
    "/{company_id}/calendars",
    response_model=CompanyCalendarResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_company_calendar(
    company_id: uuid.UUID,
    data: CompanyCalendarCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyCalendarResponse:
    """Create a new calendar connection for a company."""
    company = company_service.get_company(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    calendar = company_calendar_service.create_calendar(db, company_id, data)
    return CompanyCalendarResponse.model_validate(calendar)


@router.put(
    "/{company_id}/calendars/{calendar_id}",
    response_model=CompanyCalendarResponse,
)
def update_company_calendar(
    company_id: uuid.UUID,
    calendar_id: uuid.UUID,
    data: CompanyCalendarUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyCalendarResponse:
    """Update a calendar connection."""
    company = company_service.get_company(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    calendar = company_calendar_service.get_calendar_by_company(
        db, company_id, calendar_id
    )
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar not found",
        )

    calendar = company_calendar_service.update_calendar(db, calendar, data)
    return CompanyCalendarResponse.model_validate(calendar)


@router.delete(
    "/{company_id}/calendars/{calendar_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_company_calendar(
    company_id: uuid.UUID,
    calendar_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a calendar connection."""
    company = company_service.get_company(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    calendar = company_calendar_service.get_calendar_by_company(
        db, company_id, calendar_id
    )
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar not found",
        )

    company_calendar_service.delete_calendar(db, calendar)


@router.post(
    "/{company_id}/calendars/{calendar_id}/sync",
    response_model=CompanyCalendarResponse,
)
def sync_company_calendar(
    company_id: uuid.UUID,
    calendar_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyCalendarResponse:
    """Trigger a sync for a calendar connection.

    This updates the last_synced_at timestamp. Actual sync implementation
    will be added when calendar provider integrations are implemented.
    """
    company = company_service.get_company(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    calendar = company_calendar_service.get_calendar_by_company(
        db, company_id, calendar_id
    )
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar not found",
        )

    calendar = company_calendar_service.update_last_synced(db, calendar)
    return CompanyCalendarResponse.model_validate(calendar)
