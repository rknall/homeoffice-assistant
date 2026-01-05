# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Time Tracking plugin API routes."""

from calendar import monthrange
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.models.company import Company
from src.models.user import User

from .models import TimeEntry
from .schemas import (
    CheckInRequest,
    CheckInStatusResponse,
    CheckOutRequest,
    CompanyTimeSettingsBase,
    CompanyTimeSettingsResponse,
    CompanyTimeSettingsUpdate,
    CustomHolidayCreate,
    CustomHolidayResponse,
    DailySummary,
    EntryType,
    LeaveBalanceResponse,
    LeaveBalanceUpdate,
    MonthlyReportResponse,
    PluginInfoResponse,
    PublicHolidayResponse,
    TimeEntryCreate,
    TimeEntryResponse,
    TimeEntryUpdate,
    WorkLocation,
)
from .services import (
    CompanySettingsService,
    HolidayService,
    LeaveBalanceService,
    TimeEntryService,
    calculate_break_minutes,
)

router = APIRouter()


# --- Helper Functions ---


def _entry_to_response(
    entry: TimeEntry,
    company_name: str | None = None,
    is_locked: bool = False,
) -> TimeEntryResponse:
    """Convert a TimeEntry model to response schema."""
    return TimeEntryResponse(
        id=str(entry.id),
        user_id=str(entry.user_id),
        date=entry.date,
        company_id=str(entry.company_id) if entry.company_id else None,
        company_name=company_name,
        entry_type=EntryType(entry.entry_type),
        check_in=entry.check_in,
        check_out=entry.check_out,
        timezone=entry.timezone,
        work_location=(
            WorkLocation(entry.work_location) if entry.work_location else None
        ),
        notes=entry.notes,
        submission_id=str(entry.submission_id) if entry.submission_id else None,
        is_locked=is_locked,
        is_open=entry.is_open,
        gross_minutes=entry.gross_minutes,
        gross_hours=entry.gross_hours,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def _get_company_map(db: Session) -> dict[str, str]:
    """Get a mapping of company_id -> company_name."""
    companies = db.query(Company).all()
    return {str(c.id): c.name for c in companies}


# --- Time Entry Endpoints ---


@router.get("/entries", response_model=list[TimeEntryResponse])
def list_entries(
    company_id: str | None = None,
    start_date: str | None = Query(None, alias="from"),
    end_date: str | None = Query(None, alias="to"),
    entry_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TimeEntryResponse]:
    """List time entries with optional filters."""
    service = TimeEntryService(db)
    company_map = _get_company_map(db)

    from_date = date.fromisoformat(start_date) if start_date else None
    to_date = date.fromisoformat(end_date) if end_date else None
    company_uuid = UUID(company_id) if company_id else None

    entries = service.list_entries(
        user_id=current_user.id,
        from_date=from_date,
        to_date=to_date,
        company_id=company_uuid,
        entry_type=entry_type,
    )

    responses = []
    for entry in entries:
        cid = str(entry.company_id) if entry.company_id else None
        company_name = company_map.get(cid) if cid else None
        is_locked = service.is_entry_locked(entry)
        responses.append(_entry_to_response(entry, company_name, is_locked))

    return responses


@router.post("/entries", response_model=TimeEntryResponse)
def create_entry(
    data: TimeEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TimeEntryResponse:
    """Create a new time entry."""
    service = TimeEntryService(db)
    company_map = _get_company_map(db)

    try:
        entry = service.create_entry(
            user_id=current_user.id,
            entry_date=data.date,
            entry_type=data.entry_type.value,
            company_id=UUID(data.company_id) if data.company_id else None,
            check_in=data.check_in,
            check_out=data.check_out,
            timezone=data.timezone,
            work_location=data.work_location.value if data.work_location else None,
            notes=data.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    company_name = company_map.get(str(entry.company_id)) if entry.company_id else None
    return _entry_to_response(entry, company_name)


@router.get("/entries/{entry_id}", response_model=TimeEntryResponse)
def get_entry(
    entry_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TimeEntryResponse:
    """Get a time entry by ID."""
    service = TimeEntryService(db)
    company_map = _get_company_map(db)

    entry = service.get_entry(UUID(entry_id), current_user.id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    company_name = company_map.get(str(entry.company_id)) if entry.company_id else None
    is_locked = service.is_entry_locked(entry)
    return _entry_to_response(entry, company_name, is_locked)


@router.put("/entries/{entry_id}", response_model=TimeEntryResponse)
def update_entry(
    entry_id: str,
    data: TimeEntryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TimeEntryResponse:
    """Update an existing time entry."""
    service = TimeEntryService(db)
    company_map = _get_company_map(db)

    update_data = data.model_dump(exclude_unset=True)

    # Convert enums to strings
    if update_data.get("entry_type"):
        update_data["entry_type"] = update_data["entry_type"].value
    if update_data.get("work_location"):
        update_data["work_location"] = update_data["work_location"].value

    try:
        entry = service.update_entry(UUID(entry_id), current_user.id, **update_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    company_name = company_map.get(str(entry.company_id)) if entry.company_id else None
    is_locked = service.is_entry_locked(entry)
    return _entry_to_response(entry, company_name, is_locked)


@router.delete("/entries/{entry_id}", status_code=204)
def delete_entry(
    entry_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a time entry."""
    service = TimeEntryService(db)

    try:
        deleted = service.delete_entry(UUID(entry_id), current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    if not deleted:
        raise HTTPException(status_code=404, detail="Entry not found")


# --- Quick Action Endpoints ---


@router.post("/check-in", response_model=TimeEntryResponse)
def check_in(
    data: CheckInRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TimeEntryResponse:
    """Quick check-in for today."""
    service = TimeEntryService(db)
    company_map = _get_company_map(db)

    try:
        entry = service.check_in(
            user_id=current_user.id,
            company_id=UUID(data.company_id) if data.company_id else None,
            timezone=data.timezone,
            work_location=data.work_location.value if data.work_location else None,
            notes=data.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    company_name = company_map.get(str(entry.company_id)) if entry.company_id else None
    return _entry_to_response(entry, company_name)


@router.post("/check-out", response_model=TimeEntryResponse)
def check_out(
    data: CheckOutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TimeEntryResponse:
    """Quick check-out for today."""
    service = TimeEntryService(db)
    company_map = _get_company_map(db)

    try:
        entry = service.check_out(
            user_id=current_user.id,
            timezone=data.timezone,
            notes=data.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    company_name = company_map.get(str(entry.company_id)) if entry.company_id else None
    return _entry_to_response(entry, company_name)


@router.get("/status", response_model=CheckInStatusResponse)
def get_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CheckInStatusResponse:
    """Get current check-in status."""
    service = TimeEntryService(db)
    company_map = _get_company_map(db)

    open_entry = service.get_open_entry(current_user.id)
    today_entries = service.get_entries_for_date(current_user.id, date.today())

    # Calculate today's total hours
    total_minutes = sum(e.gross_minutes or 0 for e in today_entries if not e.is_open)
    total_hours = total_minutes / 60

    # Build response with proper company name lookups
    open_entry_response = None
    if open_entry:
        oe_cid = str(open_entry.company_id) if open_entry.company_id else None
        open_entry_response = _entry_to_response(
            open_entry, company_map.get(oe_cid) if oe_cid else None
        )

    today_responses = []
    for e in today_entries:
        e_cid = str(e.company_id) if e.company_id else None
        today_responses.append(
            _entry_to_response(e, company_map.get(e_cid) if e_cid else None)
        )

    return CheckInStatusResponse(
        is_checked_in=open_entry is not None,
        open_entry=open_entry_response,
        today_entries=today_responses,
        today_total_hours=total_hours,
    )


@router.get("/today", response_model=list[TimeEntryResponse])
def get_today(
    company_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TimeEntryResponse]:
    """Get today's entries."""
    service = TimeEntryService(db)
    company_map = _get_company_map(db)

    company_uuid = UUID(company_id) if company_id else None
    entries = service.get_entries_for_date(current_user.id, date.today(), company_uuid)

    return [
        _entry_to_response(
            e,
            company_map.get(str(e.company_id)) if e.company_id else None,
            service.is_entry_locked(e),
        )
        for e in entries
    ]


# --- Daily Summary Endpoint ---


@router.get("/daily-summary", response_model=DailySummary)
def get_daily_summary(
    summary_date: str,
    company_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DailySummary:
    """Get aggregated summary for a specific date."""
    service = TimeEntryService(db)
    company_map = _get_company_map(db)

    target_date = date.fromisoformat(summary_date)
    company_uuid = UUID(company_id) if company_id else None

    summary = service.get_daily_summary(current_user.id, target_date, company_uuid)

    return DailySummary(
        date=summary["date"],
        entries=[
            _entry_to_response(
                e,
                company_map.get(str(e.company_id)) if e.company_id else None,
                service.is_entry_locked(e),
            )
            for e in summary["entries"]
        ],
        total_gross_hours=summary["total_gross_hours"],
        total_net_hours=summary["total_net_hours"],
        break_minutes=summary["break_minutes"],
        entry_count=summary["entry_count"],
        has_open_entry=summary["has_open_entry"],
        warnings=summary["warnings"],
    )


# --- Leave Balance Endpoints ---


@router.get("/leave-balance", response_model=LeaveBalanceResponse)
def get_leave_balance(
    year: int | None = None,
    company_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LeaveBalanceResponse:
    """Get leave balance for a year."""
    service = LeaveBalanceService(db)

    if year is None:
        year = date.today().year

    company_uuid = UUID(company_id) if company_id else None
    balance = service.get_balance(current_user.id, year, company_uuid)

    # Calculate planned vacation (future vacation entries)
    entry_service = TimeEntryService(db)
    future_vacation = entry_service.list_entries(
        user_id=current_user.id,
        from_date=date.today(),
        company_id=company_uuid,
        entry_type=EntryType.VACATION.value,
    )
    vacation_planned = len(future_vacation)

    return LeaveBalanceResponse(
        id=str(balance.id),
        user_id=str(balance.user_id),
        company_id=str(balance.company_id) if balance.company_id else None,
        year=balance.year,
        vacation_entitled=balance.vacation_entitled,
        vacation_carryover=balance.vacation_carryover,
        vacation_taken=balance.vacation_taken,
        vacation_planned=float(vacation_planned),
        vacation_remaining=balance.vacation_remaining,
        comp_time_balance=balance.comp_time_balance,
        sick_days_taken=balance.sick_days_taken,
        created_at=balance.created_at,
        updated_at=balance.updated_at,
    )


@router.put("/leave-balance", response_model=LeaveBalanceResponse)
def update_leave_balance(
    data: LeaveBalanceUpdate,
    year: int | None = None,
    company_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LeaveBalanceResponse:
    """Update leave balance settings."""
    service = LeaveBalanceService(db)

    if year is None:
        year = date.today().year

    company_uuid = UUID(company_id) if company_id else None
    balance = service.update_balance(
        user_id=current_user.id,
        year=year,
        company_id=company_uuid,
        vacation_entitled=data.vacation_entitled,
        vacation_carryover=data.vacation_carryover,
    )

    return LeaveBalanceResponse(
        id=str(balance.id),
        user_id=str(balance.user_id),
        company_id=str(balance.company_id) if balance.company_id else None,
        year=balance.year,
        vacation_entitled=balance.vacation_entitled,
        vacation_carryover=balance.vacation_carryover,
        vacation_taken=balance.vacation_taken,
        vacation_planned=0.0,
        vacation_remaining=balance.vacation_remaining,
        comp_time_balance=balance.comp_time_balance,
        sick_days_taken=balance.sick_days_taken,
        created_at=balance.created_at,
        updated_at=balance.updated_at,
    )


# --- Company Settings Endpoints ---


@router.get(
    "/settings/company/{company_id}",
    response_model=CompanyTimeSettingsResponse | None,
)
def get_company_settings(
    company_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyTimeSettingsResponse | None:
    """Get time tracking settings for a company."""
    service = CompanySettingsService(db)
    settings = service.get_settings(UUID(company_id))

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
            if settings.default_timesheet_contact_id else None
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
    company_id: str,
    data: CompanyTimeSettingsBase,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyTimeSettingsResponse:
    """Create time tracking settings for a company."""
    service = CompanySettingsService(db)

    # Check if settings already exist
    existing = service.get_settings(UUID(company_id))
    if existing:
        raise HTTPException(
            status_code=400, detail="Settings already exist for this company"
        )

    settings = service.update_settings(
        company_id=UUID(company_id),
        timezone=data.timezone,
        country_code=data.country_code,
        vacation_days_per_year=data.vacation_days_per_year,
        daily_overtime_threshold=data.daily_overtime_threshold,
        weekly_overtime_threshold=data.weekly_overtime_threshold,
        overtime_threshold_hours=data.overtime_threshold_hours,
        comp_time_warning_balance=data.comp_time_warning_balance,
        default_timesheet_contact_id=(
            UUID(data.default_timesheet_contact_id)
            if data.default_timesheet_contact_id else None
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
            if settings.default_timesheet_contact_id else None
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
    company_id: str,
    data: CompanyTimeSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyTimeSettingsResponse:
    """Update time tracking settings for a company."""
    service = CompanySettingsService(db)

    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("default_timesheet_contact_id"):
        contact_id = update_data["default_timesheet_contact_id"]
        update_data["default_timesheet_contact_id"] = UUID(contact_id)

    settings = service.update_settings(UUID(company_id), **update_data)

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
            if settings.default_timesheet_contact_id else None
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
    current_user: User = Depends(get_current_user),
) -> list[PublicHolidayResponse]:
    """Get public holidays for a year."""
    service = HolidayService(db)
    holidays = service.get_public_holidays(year, region=region)

    return [
        PublicHolidayResponse(date=d, name=name)
        for d, name in sorted(holidays.items())
    ]


@router.get("/holidays/custom", response_model=list[CustomHolidayResponse])
def get_custom_holidays(
    year: int,
    company_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CustomHolidayResponse]:
    """Get user's custom holidays for a year."""
    service = HolidayService(db)
    company_uuid = UUID(company_id) if company_id else None
    holidays = service.get_custom_holidays(current_user.id, year, company_uuid)

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
    service = HolidayService(db)
    company_uuid = UUID(data.company_id) if data.company_id else None
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


@router.get("/reports/monthly", response_model=MonthlyReportResponse)
def get_monthly_report(
    year: int,
    month: int,
    company_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MonthlyReportResponse:
    """Get monthly report summary."""
    entry_service = TimeEntryService(db)
    company_map = _get_company_map(db)

    # Get date range for month
    _, last_day = monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)

    company_uuid = UUID(company_id) if company_id else None
    company_name = company_map.get(company_id) if company_id else None

    # Get all entries for the month
    entries = entry_service.list_entries(
        user_id=current_user.id,
        from_date=start_date,
        to_date=end_date,
        company_id=company_uuid,
    )

    # Calculate totals
    work_dates: set[date] = set()
    total_gross_minutes = 0
    vacation_days = 0
    sick_days = 0
    comp_time_days = 0
    holiday_days = 0

    for entry in entries:
        if entry.entry_type == EntryType.WORK.value:
            if entry.gross_minutes:
                work_dates.add(entry.date)
                total_gross_minutes += entry.gross_minutes
        elif entry.entry_type == EntryType.VACATION.value:
            vacation_days += 1
        elif entry.entry_type == EntryType.SICK.value:
            sick_days += 1
        elif entry.entry_type == EntryType.COMP_TIME.value:
            comp_time_days += 1
        elif entry.entry_type == EntryType.PUBLIC_HOLIDAY.value:
            holiday_days += 1

    total_work_days = len(work_dates)
    total_gross_hours = total_gross_minutes / 60
    avg_hours_per_day = total_gross_hours / max(total_work_days, 1)
    break_minutes = calculate_break_minutes(avg_hours_per_day) * total_work_days
    total_net_hours = total_gross_hours - (break_minutes / 60)

    # Calculate expected hours (8h per working day in month)
    expected_hours = total_work_days * 8
    overtime_hours = max(0, total_net_hours - expected_hours)

    # Build daily summaries
    daily_summaries = []
    dates_with_entries = sorted({e.date for e in entries})
    for d in dates_with_entries:
        summary = entry_service.get_daily_summary(current_user.id, d, company_uuid)
        daily_summaries.append(DailySummary(
            date=summary["date"],
            entries=[
                _entry_to_response(
                    e,
                    company_map.get(str(e.company_id)) if e.company_id else None,
                    entry_service.is_entry_locked(e),
                )
                for e in summary["entries"]
            ],
            total_gross_hours=summary["total_gross_hours"],
            total_net_hours=summary["total_net_hours"],
            break_minutes=summary["break_minutes"],
            entry_count=summary["entry_count"],
            has_open_entry=summary["has_open_entry"],
            warnings=summary["warnings"],
        ))

    return MonthlyReportResponse(
        year=year,
        month=month,
        company_id=company_id,
        company_name=company_name,
        user_name=current_user.username,
        total_work_days=total_work_days,
        total_gross_hours=round(total_gross_hours, 2),
        total_net_hours=round(total_net_hours, 2),
        total_break_minutes=break_minutes,
        overtime_hours=round(overtime_hours, 2),
        vacation_days=vacation_days,
        sick_days=sick_days,
        comp_time_days=comp_time_days,
        public_holiday_days=holiday_days,
        entries=[
            _entry_to_response(
                e,
                company_map.get(str(e.company_id)) if e.company_id else None,
                entry_service.is_entry_locked(e),
            )
            for e in entries
        ],
        daily_summaries=daily_summaries,
    )


# --- Plugin Info Endpoint ---


@router.get("/info", response_model=PluginInfoResponse)
def get_plugin_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PluginInfoResponse:
    """Get plugin information and summary."""
    from sqlalchemy import func

    from .models import LeaveBalance, TimeEntry

    entry_count = db.query(func.count(TimeEntry.id)).filter(
        TimeEntry.user_id == current_user.id
    ).scalar() or 0

    current_balance = db.query(LeaveBalance).filter(
        LeaveBalance.user_id == current_user.id,
        LeaveBalance.year == date.today().year,
    ).first()

    balance_response = None
    if current_balance:
        cb_company_id = (
            str(current_balance.company_id) if current_balance.company_id else None
        )
        balance_response = LeaveBalanceResponse(
            id=str(current_balance.id),
            user_id=str(current_balance.user_id),
            company_id=cb_company_id,
            year=current_balance.year,
            vacation_entitled=current_balance.vacation_entitled,
            vacation_carryover=current_balance.vacation_carryover,
            vacation_taken=current_balance.vacation_taken,
            vacation_planned=0.0,
            vacation_remaining=current_balance.vacation_remaining,
            comp_time_balance=current_balance.comp_time_balance,
            sick_days_taken=current_balance.sick_days_taken,
            created_at=current_balance.created_at,
            updated_at=current_balance.updated_at,
        )

    return PluginInfoResponse(
        plugin_id="time-tracking",
        plugin_name="Time Tracking",
        version="0.4.0",
        entry_count=entry_count,
        current_balance=balance_response,
    )
