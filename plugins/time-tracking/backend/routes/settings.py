# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Company settings and holiday routes."""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, require_permission
from src.database import get_db
from src.models.user import User
from src.services.holiday_calendar_service import UnknownHolidayRegionError

from ..schemas import (
    CompanyTimeSettingsBase,
    CompanyTimeSettingsResponse,
    CompanyTimeSettingsUpdate,
    CustomHolidayCreate,
    CustomHolidayResponse,
    PublicHolidayResponse,
)
from ..services import (
    CompanySettingsService,
    HolidayService,
    TimeTrackingConfig,
)
from .common import (
    RECORDS_READ,
    RECORDS_WRITE,
    SETTINGS_WRITE,
    get_plugin_config,
    require_company_code,
    router,
)


@router.get(
    "/settings/company/{company_id}",
    response_model=CompanyTimeSettingsResponse | None,
)
def get_company_settings(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission(RECORDS_READ, company_id_param="company_id")
    ),
) -> CompanyTimeSettingsResponse | None:
    """Get time tracking settings for a company."""
    service = CompanySettingsService(db)
    settings = service.get_settings(company_id)

    if not settings:
        return None

    return CompanyTimeSettingsResponse(
        id=str(settings.id),
        company_id=str(settings.company_id),
        timezone=settings.timezone,
        country_code=settings.country_code,
        vacation_days_per_year=settings.vacation_days_per_year,
        daily_overtime_threshold=settings.daily_overtime_threshold,
        weekly_overtime_threshold=settings.weekly_overtime_threshold,
        overtime_threshold_hours=settings.overtime_threshold_hours,
        comp_time_warning_balance=settings.comp_time_warning_balance,
        default_timesheet_contact_id=(
            str(settings.default_timesheet_contact_id)
            if settings.default_timesheet_contact_id
            else None
        ),
        lock_period_days=settings.lock_period_days,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


@router.post(
    "/settings/company/{company_id}",
    response_model=CompanyTimeSettingsResponse,
)
def create_company_settings(
    company_id: UUID,
    data: CompanyTimeSettingsBase,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission(SETTINGS_WRITE, company_id_param="company_id")
    ),
) -> CompanyTimeSettingsResponse:
    """Create time tracking settings for a company."""
    service = CompanySettingsService(db)

    # Check if settings already exist
    existing = service.get_settings(company_id)
    if existing:
        raise HTTPException(
            status_code=400, detail="Settings already exist for this company"
        )

    settings = service.update_settings(
        company_id=company_id,
        timezone=data.timezone,
        country_code=data.country_code,
        vacation_days_per_year=data.vacation_days_per_year,
        daily_overtime_threshold=data.daily_overtime_threshold,
        weekly_overtime_threshold=data.weekly_overtime_threshold,
        overtime_threshold_hours=data.overtime_threshold_hours,
        comp_time_warning_balance=data.comp_time_warning_balance,
        default_timesheet_contact_id=(
            UUID(data.default_timesheet_contact_id)
            if data.default_timesheet_contact_id
            else None
        ),
        lock_period_days=data.lock_period_days,
    )

    return CompanyTimeSettingsResponse(
        id=str(settings.id),
        company_id=str(settings.company_id),
        timezone=settings.timezone,
        country_code=settings.country_code,
        vacation_days_per_year=settings.vacation_days_per_year,
        daily_overtime_threshold=settings.daily_overtime_threshold,
        weekly_overtime_threshold=settings.weekly_overtime_threshold,
        overtime_threshold_hours=settings.overtime_threshold_hours,
        comp_time_warning_balance=settings.comp_time_warning_balance,
        default_timesheet_contact_id=(
            str(settings.default_timesheet_contact_id)
            if settings.default_timesheet_contact_id
            else None
        ),
        lock_period_days=settings.lock_period_days,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


@router.put(
    "/settings/company/{company_id}",
    response_model=CompanyTimeSettingsResponse,
)
def update_company_settings(
    company_id: UUID,
    data: CompanyTimeSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission(SETTINGS_WRITE, company_id_param="company_id")
    ),
) -> CompanyTimeSettingsResponse:
    """Update time tracking settings for a company."""
    service = CompanySettingsService(db)

    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("default_timesheet_contact_id"):
        contact_id = update_data["default_timesheet_contact_id"]
        update_data["default_timesheet_contact_id"] = UUID(contact_id)

    settings = service.update_settings(company_id, **update_data)

    return CompanyTimeSettingsResponse(
        id=str(settings.id),
        company_id=str(settings.company_id),
        timezone=settings.timezone,
        country_code=settings.country_code,
        vacation_days_per_year=settings.vacation_days_per_year,
        daily_overtime_threshold=settings.daily_overtime_threshold,
        weekly_overtime_threshold=settings.weekly_overtime_threshold,
        overtime_threshold_hours=settings.overtime_threshold_hours,
        comp_time_warning_balance=settings.comp_time_warning_balance,
        default_timesheet_contact_id=(
            str(settings.default_timesheet_contact_id)
            if settings.default_timesheet_contact_id
            else None
        ),
        lock_period_days=settings.lock_period_days,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


# --- Holiday Endpoints ---


@router.get("/holidays", response_model=list[PublicHolidayResponse])
def get_holidays(
    year: int,
    region: str | None = None,
    db: Session = Depends(get_db),
    config: TimeTrackingConfig = Depends(get_plugin_config),
    current_user: User = Depends(require_permission(RECORDS_READ)),
) -> list[PublicHolidayResponse]:
    """Get public holidays for a year."""
    service = HolidayService(db, config)
    try:
        holidays = service.get_public_holidays(year, region=region)
    except UnknownHolidayRegionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    return [
        PublicHolidayResponse(date=d, name=name) for d, name in sorted(holidays.items())
    ]


@router.get("/holidays/custom", response_model=list[CustomHolidayResponse])
def get_custom_holidays(
    year: int,
    company_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission(RECORDS_READ, company_id_param="company_id")
    ),
) -> list[CustomHolidayResponse]:
    """Get user's custom holidays for a year."""
    service = HolidayService(db)
    holidays = service.get_custom_holidays(current_user.id, year, company_id)

    return [
        CustomHolidayResponse(
            id=str(h.id),
            user_id=str(h.user_id),
            company_id=str(h.company_id) if h.company_id else None,
            date=h.date,
            name=h.name,
            created_at=h.created_at,
            updated_at=h.updated_at,
        )
        for h in holidays
    ]


@router.post("/holidays/custom", response_model=CustomHolidayResponse)
def create_custom_holiday(
    data: CustomHolidayCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomHolidayResponse:
    """Create a custom holiday."""
    company_uuid = require_company_code(
        db, current_user, RECORDS_WRITE, data.company_id
    )
    service = HolidayService(db)
    holiday = service.create_custom_holiday(
        user_id=current_user.id,
        holiday_date=data.date,
        name=data.name,
        company_id=company_uuid,
    )

    return CustomHolidayResponse(
        id=str(holiday.id),
        user_id=str(holiday.user_id),
        company_id=str(holiday.company_id) if holiday.company_id else None,
        date=holiday.date,
        name=holiday.name,
        created_at=holiday.created_at,
        updated_at=holiday.updated_at,
    )


# --- Report Endpoints ---
