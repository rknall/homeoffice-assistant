# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Holiday calendar API endpoints."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.models import User
from src.schemas.holiday_calendar import (
    HolidayCalendarCreate,
    HolidayCalendarResponse,
    HolidayCalendarUpdate,
    HolidayEntry,
    HolidaysResponse,
    SupportedCountriesResponse,
)
from src.services import holiday_calendar_service

router = APIRouter()


@router.get(
    "",
    response_model=list[HolidayCalendarResponse],
)
def list_holiday_calendars(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[HolidayCalendarResponse]:
    """List all holiday calendar configurations for the current user."""
    calendars = holiday_calendar_service.get_holiday_calendars(db, current_user.id)
    return [HolidayCalendarResponse.model_validate(c) for c in calendars]


@router.get(
    "/countries",
    response_model=SupportedCountriesResponse,
)
def list_supported_countries(
    current_user: User = Depends(get_current_user),
) -> SupportedCountriesResponse:
    """List all supported countries with their subdivisions."""
    countries = holiday_calendar_service.get_supported_countries()
    return SupportedCountriesResponse(countries=countries)


@router.get(
    "/holidays",
    response_model=HolidaysResponse,
)
def get_holidays(
    start_date: date = Query(..., description="Start date (inclusive)"),
    end_date: date = Query(..., description="End date (inclusive)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HolidaysResponse:
    """Get all holidays for the user's configured calendars within a date range."""
    calendars = holiday_calendar_service.get_holiday_calendars(db, current_user.id)
    holidays_list = holiday_calendar_service.get_holidays_for_date_range(
        calendars, start_date, end_date
    )
    return HolidaysResponse(holidays=holidays_list)


@router.get(
    "/preview",
    response_model=list[HolidayEntry],
)
def preview_holidays(
    country_code: str = Query(..., min_length=2, max_length=2),
    subdivision: str | None = Query(None, max_length=10),
    year: int | None = Query(None, ge=1900, le=2100),
    current_user: User = Depends(get_current_user),
) -> list[HolidayEntry]:
    """Preview holidays for a country/subdivision before adding it."""
    return holiday_calendar_service.get_holidays_preview(
        country_code.upper(),
        subdivision.upper() if subdivision else None,
        year,
    )


@router.get(
    "/{calendar_id}",
    response_model=HolidayCalendarResponse,
)
def get_holiday_calendar(
    calendar_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HolidayCalendarResponse:
    """Get a specific holiday calendar configuration."""
    calendar = holiday_calendar_service.get_holiday_calendar_by_user(
        db, current_user.id, calendar_id
    )
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Holiday calendar not found",
        )

    return HolidayCalendarResponse.model_validate(calendar)


@router.post(
    "",
    response_model=HolidayCalendarResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_holiday_calendar(
    data: HolidayCalendarCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HolidayCalendarResponse:
    """Create a new holiday calendar configuration."""
    calendar = holiday_calendar_service.create_holiday_calendar(
        db, current_user.id, data
    )
    return HolidayCalendarResponse.model_validate(calendar)


@router.put(
    "/{calendar_id}",
    response_model=HolidayCalendarResponse,
)
def update_holiday_calendar(
    calendar_id: uuid.UUID,
    data: HolidayCalendarUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HolidayCalendarResponse:
    """Update a holiday calendar configuration."""
    calendar = holiday_calendar_service.get_holiday_calendar_by_user(
        db, current_user.id, calendar_id
    )
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Holiday calendar not found",
        )

    calendar = holiday_calendar_service.update_holiday_calendar(db, calendar, data)
    return HolidayCalendarResponse.model_validate(calendar)


@router.delete(
    "/{calendar_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_holiday_calendar(
    calendar_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a holiday calendar configuration."""
    calendar = holiday_calendar_service.get_holiday_calendar_by_user(
        db, current_user.id, calendar_id
    )
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Holiday calendar not found",
        )

    holiday_calendar_service.delete_holiday_calendar(db, calendar)
