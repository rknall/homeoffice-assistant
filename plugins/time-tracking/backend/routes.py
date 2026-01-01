# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Time Tracking plugin API routes."""

import json
from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db, require_permission
from src.models import User

from .models import (
    DayType,
    LeaveBalance,
    TimeAllocation,
    TimeRecord,
    UserTimePreferences,
)
from .schemas import (
    CheckInRequest,
    CheckOutRequest,
    CompanyTimeSettingsResponse,
    CompanyTimeSettingsUpdate,
    CustomHolidayCreate,
    CustomHolidayResponse,
    LeaveBalanceResponse,
    LeaveBalanceUpdate,
    MonthlyReportResponse,
    PluginInfoResponse,
    PublicHolidayResponse,
    TimeAllocationCreate,
    TimeAllocationResponse,
    TimeRecordCreate,
    TimeRecordResponse,
    TimeRecordUpdate,
    UserTimePreferencesResponse,
    WorkLocation,
)
from .services import (
    CompanySettingsService,
    HolidayService,
    LeaveBalanceService,
    TimeRecordService,
)

router = APIRouter(tags=["time-tracking"])


# --- Helper functions ---


def _record_to_response(record: TimeRecord) -> TimeRecordResponse:
    """Convert a TimeRecord to a response schema."""
    warnings = None
    if record.compliance_warnings:
        warnings = json.loads(record.compliance_warnings)

    return TimeRecordResponse(
        id=str(record.id),
        user_id=str(record.user_id),
        date=record.date,
        company_id=str(record.company_id) if record.company_id else None,
        day_type=DayType(record.day_type),
        check_in=record.check_in,
        check_in_timezone=record.check_in_timezone,
        check_out=record.check_out,
        check_out_timezone=record.check_out_timezone,
        partial_absence_type=(
            DayType(record.partial_absence_type)
            if record.partial_absence_type
            else None
        ),
        partial_absence_hours=record.partial_absence_hours,
        gross_hours=record.gross_hours,
        break_minutes=record.break_minutes,
        net_hours=record.net_hours,
        work_location=(
            WorkLocation(record.work_location) if record.work_location else None
        ),
        notes=record.notes,
        compliance_warnings=warnings,
        submission_id=(
            str(record.submission_id) if record.submission_id else None
        ),
        is_locked=False,  # Will be set by service
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _balance_to_response(balance: LeaveBalance) -> LeaveBalanceResponse:
    """Convert a LeaveBalance to a response schema."""
    return LeaveBalanceResponse(
        id=str(balance.id),
        user_id=str(balance.user_id),
        company_id=str(balance.company_id) if balance.company_id else None,
        year=balance.year,
        vacation_entitled=balance.vacation_entitled,
        vacation_carryover=balance.vacation_carryover,
        vacation_taken=balance.vacation_taken,
        vacation_remaining=balance.vacation_remaining,
        comp_time_balance=balance.comp_time_balance,
        sick_days_taken=balance.sick_days_taken,
        created_at=balance.created_at,
        updated_at=balance.updated_at,
    )


# --- Plugin Info ---


@router.get("/info", response_model=PluginInfoResponse)
def get_plugin_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PluginInfoResponse:
    """Get information about the time tracking plugin."""
    record_count = (
        db.query(TimeRecord)
        .filter(TimeRecord.user_id == current_user.id)
        .count()
    )

    # Get current year's balance
    balance_service = LeaveBalanceService(db)
    balance = balance_service.get_balance(
        current_user.id, datetime.now().year
    )

    return PluginInfoResponse(
        plugin_id="time-tracking",
        plugin_name="Time Tracking",
        version="1.0.0",
        record_count=record_count,
        current_balance=_balance_to_response(balance) if balance else None,
    )


# --- Time Records ---


@router.get("/records", response_model=list[TimeRecordResponse])
def list_records(
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    company_id: str | None = Query(None),
    day_type: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("time-tracking.records.read")),
) -> list[TimeRecordResponse]:
    """List time records with optional filters."""
    service = TimeRecordService(db)
    records = service.list_records(
        user_id=current_user.id,
        from_date=from_date,
        to_date=to_date,
        company_id=UUID(company_id) if company_id else None,
        day_type=day_type,
    )

    responses = []
    for record in records:
        resp = _record_to_response(record)
        resp.is_locked = service.is_record_locked(record)
        responses.append(resp)

    return responses


@router.post("/records", response_model=TimeRecordResponse, status_code=201)
def create_record(
    data: TimeRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("time-tracking.records.write")),
) -> TimeRecordResponse:
    """Create a new time record."""
    service = TimeRecordService(db)

    # Check if record already exists for this date
    existing = service.get_record_by_date(current_user.id, data.date)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Record already exists for {data.date}",
        )

    record = service.create_record(
        user_id=current_user.id,
        record_date=data.date,
        day_type=data.day_type.value,
        company_id=UUID(data.company_id) if data.company_id else None,
        check_in=data.check_in,
        check_out=data.check_out,
        check_in_timezone=data.check_in_timezone,
        check_out_timezone=data.check_out_timezone,
        partial_absence_type=(
            data.partial_absence_type.value if data.partial_absence_type else None
        ),
        partial_absence_hours=data.partial_absence_hours,
        work_location=data.work_location.value if data.work_location else None,
        notes=data.notes,
    )

    return _record_to_response(record)


@router.get("/records/{record_id}", response_model=TimeRecordResponse)
def get_record(
    record_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("time-tracking.records.read")),
) -> TimeRecordResponse:
    """Get a specific time record."""
    service = TimeRecordService(db)
    record = service.get_record(UUID(record_id), current_user.id)

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    resp = _record_to_response(record)
    resp.is_locked = service.is_record_locked(record)
    return resp


@router.put("/records/{record_id}", response_model=TimeRecordResponse)
def update_record(
    record_id: str,
    data: TimeRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("time-tracking.records.write")),
) -> TimeRecordResponse:
    """Update a time record."""
    service = TimeRecordService(db)

    try:
        record = service.update_record(
            record_id=UUID(record_id),
            user_id=current_user.id,
            company_id=UUID(data.company_id) if data.company_id else None,
            day_type=data.day_type.value if data.day_type else None,
            check_in=data.check_in,
            check_out=data.check_out,
            check_in_timezone=data.check_in_timezone,
            check_out_timezone=data.check_out_timezone,
            partial_absence_type=(
                data.partial_absence_type.value if data.partial_absence_type else None
            ),
            partial_absence_hours=data.partial_absence_hours,
            work_location=data.work_location.value if data.work_location else None,
            notes=data.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    resp = _record_to_response(record)
    resp.is_locked = service.is_record_locked(record)
    return resp


@router.delete("/records/{record_id}", status_code=204)
def delete_record(
    record_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("time-tracking.records.delete")),
) -> None:
    """Delete a time record."""
    service = TimeRecordService(db)

    try:
        deleted = service.delete_record(UUID(record_id), current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    if not deleted:
        raise HTTPException(status_code=404, detail="Record not found")


# --- Quick Actions ---


@router.post("/check-in", response_model=TimeRecordResponse)
def check_in(
    data: CheckInRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("time-tracking.records.write")),
) -> TimeRecordResponse:
    """Quick check-in for today."""
    service = TimeRecordService(db)
    today = date.today()

    # Check if record already exists
    existing = service.get_record_by_date(current_user.id, today)
    if existing:
        if existing.check_in:
            raise HTTPException(
                status_code=400,
                detail="Already checked in today",
            )
        # Update existing record with check-in
        record = service.update_record(
            record_id=existing.id,
            user_id=current_user.id,
            check_in=datetime.now().time(),
            check_in_timezone=data.timezone,
            work_location=data.work_location.value if data.work_location else None,
            notes=data.notes,
        )
    else:
        # Create new record
        record = service.create_record(
            user_id=current_user.id,
            record_date=today,
            day_type=DayType.WORK.value,
            company_id=UUID(data.company_id) if data.company_id else None,
            check_in=datetime.now().time(),
            check_in_timezone=data.timezone,
            work_location=data.work_location.value if data.work_location else None,
            notes=data.notes,
        )

    return _record_to_response(record)


@router.post("/check-out", response_model=TimeRecordResponse)
def check_out(
    data: CheckOutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("time-tracking.records.write")),
) -> TimeRecordResponse:
    """Quick check-out for today."""
    service = TimeRecordService(db)
    today = date.today()

    existing = service.get_record_by_date(current_user.id, today)
    if not existing:
        raise HTTPException(
            status_code=400,
            detail="No check-in found for today",
        )

    if existing.check_out:
        raise HTTPException(
            status_code=400,
            detail="Already checked out today",
        )

    record = service.update_record(
        record_id=existing.id,
        user_id=current_user.id,
        check_out=datetime.now().time(),
        check_out_timezone=data.timezone,
        notes=data.notes if data.notes else existing.notes,
    )

    return _record_to_response(record)


@router.get("/today", response_model=TimeRecordResponse | None)
def get_today(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("time-tracking.records.read")),
) -> TimeRecordResponse | None:
    """Get today's time record."""
    service = TimeRecordService(db)
    record = service.get_record_by_date(current_user.id, date.today())

    if not record:
        return None

    return _record_to_response(record)


# --- Time Allocations ---


@router.get(
    "/records/{record_id}/allocations",
    response_model=list[TimeAllocationResponse],
)
def list_allocations(
    record_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("time-tracking.records.read")),
) -> list[TimeAllocationResponse]:
    """List allocations for a time record."""
    # Verify record belongs to user
    record = (
        db.query(TimeRecord)
        .filter(
            TimeRecord.id == record_id,
            TimeRecord.user_id == current_user.id,
        )
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    allocations = (
        db.query(TimeAllocation)
        .filter(TimeAllocation.time_record_id == record_id)
        .all()
    )

    return [
        TimeAllocationResponse(
            id=str(a.id),
            time_record_id=str(a.time_record_id),
            hours=a.hours,
            description=a.description,
            event_id=str(a.event_id) if a.event_id else None,
            company_id=str(a.company_id) if a.company_id else None,
            created_at=a.created_at,
            updated_at=a.updated_at,
        )
        for a in allocations
    ]


@router.post(
    "/records/{record_id}/allocations",
    response_model=TimeAllocationResponse,
    status_code=201,
)
def create_allocation(
    record_id: str,
    data: TimeAllocationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("time-tracking.records.write")),
) -> TimeAllocationResponse:
    """Create a time allocation for a record."""
    # Verify record belongs to user
    record = (
        db.query(TimeRecord)
        .filter(
            TimeRecord.id == record_id,
            TimeRecord.user_id == current_user.id,
        )
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    allocation = TimeAllocation(
        time_record_id=UUID(record_id),
        hours=data.hours,
        description=data.description,
        event_id=UUID(data.event_id) if data.event_id else None,
        company_id=UUID(data.company_id) if data.company_id else None,
    )
    db.add(allocation)
    db.commit()
    db.refresh(allocation)

    return TimeAllocationResponse(
        id=str(allocation.id),
        time_record_id=str(allocation.time_record_id),
        hours=allocation.hours,
        description=allocation.description,
        event_id=str(allocation.event_id) if allocation.event_id else None,
        company_id=str(allocation.company_id) if allocation.company_id else None,
        created_at=allocation.created_at,
        updated_at=allocation.updated_at,
    )


@router.delete("/allocations/{allocation_id}", status_code=204)
def delete_allocation(
    allocation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("time-tracking.records.delete")),
) -> None:
    """Delete a time allocation."""
    allocation = db.query(TimeAllocation).filter(
        TimeAllocation.id == allocation_id
    ).first()

    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")

    # Verify the record belongs to user
    record = (
        db.query(TimeRecord)
        .filter(
            TimeRecord.id == allocation.time_record_id,
            TimeRecord.user_id == current_user.id,
        )
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    db.delete(allocation)
    db.commit()


# --- Leave Balance ---


@router.get("/leave-balance", response_model=LeaveBalanceResponse)
def get_leave_balance(
    year: int = Query(default_factory=lambda: datetime.now().year),
    company_id: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("time-tracking.records.read")),
) -> LeaveBalanceResponse:
    """Get leave balance for a year."""
    service = LeaveBalanceService(db)
    balance = service.get_balance(
        user_id=current_user.id,
        year=year,
        company_id=UUID(company_id) if company_id else None,
    )

    # Update comp time balance
    balance.comp_time_balance = service.calculate_comp_time_balance(
        current_user.id,
        UUID(company_id) if company_id else None,
    )
    db.commit()

    return _balance_to_response(balance)


@router.put("/leave-balance", response_model=LeaveBalanceResponse)
def update_leave_balance(
    data: LeaveBalanceUpdate,
    year: int = Query(default_factory=lambda: datetime.now().year),
    company_id: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("time-tracking.settings.write")),
) -> LeaveBalanceResponse:
    """Update leave balance settings."""
    service = LeaveBalanceService(db)
    balance = service.update_balance(
        user_id=current_user.id,
        year=year,
        company_id=UUID(company_id) if company_id else None,
        vacation_entitled=data.vacation_entitled,
        vacation_carryover=data.vacation_carryover,
    )

    return _balance_to_response(balance)


# --- Company Settings ---


@router.get(
    "/settings/company/{company_id}",
    response_model=CompanyTimeSettingsResponse,
)
def get_company_settings(
    company_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("time-tracking.records.read")),
) -> CompanyTimeSettingsResponse:
    """Get time tracking settings for a company."""
    service = CompanySettingsService(db)
    settings = service.get_or_create_settings(UUID(company_id))

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
    company_id: str,
    data: CompanyTimeSettingsUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("time-tracking.settings.write")),
) -> CompanyTimeSettingsResponse:
    """Update time tracking settings for a company."""
    service = CompanySettingsService(db)
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


# --- Public Holidays ---


@router.get("/holidays", response_model=list[PublicHolidayResponse])
def get_public_holidays(
    year: int = Query(default_factory=lambda: datetime.now().year),
    country: str = Query(default="AT"),
    region: str | None = Query(None),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[PublicHolidayResponse]:
    """Get public holidays for a year."""
    service = HolidayService(db)
    holidays_dict = service.get_public_holidays(year, country, region)

    return [
        PublicHolidayResponse(date=d, name=name)
        for d, name in sorted(holidays_dict.items())
    ]


@router.post("/holidays/custom", response_model=CustomHolidayResponse, status_code=201)
def create_custom_holiday(
    data: CustomHolidayCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("time-tracking.settings.write")),
) -> CustomHolidayResponse:
    """Create a custom holiday."""
    service = HolidayService(db)
    holiday = service.create_custom_holiday(
        user_id=current_user.id,
        holiday_date=data.date,
        name=data.name,
        company_id=UUID(data.company_id) if data.company_id else None,
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


# --- User Preferences ---


@router.get("/preferences", response_model=UserTimePreferencesResponse | None)
def get_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserTimePreferencesResponse | None:
    """Get user's time tracking preferences."""
    prefs = (
        db.query(UserTimePreferences)
        .filter(UserTimePreferences.user_id == current_user.id)
        .first()
    )

    if not prefs:
        return None

    return UserTimePreferencesResponse(
        id=str(prefs.id),
        user_id=str(prefs.user_id),
        last_company_id=str(prefs.last_company_id) if prefs.last_company_id else None,
        last_work_location=prefs.last_work_location,
        last_check_in=prefs.last_check_in,
        last_check_out=prefs.last_check_out,
    )


# --- Reports ---


@router.get("/reports/monthly", response_model=MonthlyReportResponse)
def get_monthly_report(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    company_id: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("time-tracking.reports.read")),
) -> MonthlyReportResponse:
    """Generate a monthly time tracking report."""
    service = TimeRecordService(db)
    records = service.get_records_for_month(
        user_id=current_user.id,
        year=year,
        month=month,
        company_id=UUID(company_id) if company_id else None,
    )

    # Calculate totals
    work_days = 0
    total_gross = 0.0
    total_net = 0.0
    total_break = 0
    vacation_days = 0
    sick_days = 0
    comp_time_days = 0
    holiday_days = 0

    for record in records:
        if record.day_type == DayType.WORK.value:
            work_days += 1
            total_gross += record.gross_hours or 0.0
            total_net += record.net_hours or 0.0
            total_break += record.break_minutes or 0
        elif record.day_type == DayType.VACATION.value:
            vacation_days += 1
        elif record.day_type == DayType.SICK.value:
            sick_days += 1
        elif record.day_type == DayType.COMP_TIME.value:
            comp_time_days += 1
        elif record.day_type == DayType.PUBLIC_HOLIDAY.value:
            holiday_days += 1

    # Calculate overtime (hours beyond 8h/day * work days)
    expected_hours = work_days * 8.0
    overtime = max(0.0, total_net - expected_hours)

    # Get company name if provided
    company_name = None
    if company_id:
        from src.models import Company

        company = db.query(Company).filter(Company.id == company_id).first()
        if company:
            company_name = company.name

    return MonthlyReportResponse(
        year=year,
        month=month,
        company_id=company_id,
        company_name=company_name,
        user_name=current_user.display_name or current_user.username,
        total_work_days=work_days,
        total_gross_hours=round(total_gross, 2),
        total_net_hours=round(total_net, 2),
        total_break_minutes=total_break,
        overtime_hours=round(overtime, 2),
        vacation_days=vacation_days,
        sick_days=sick_days,
        comp_time_days=comp_time_days,
        public_holiday_days=holiday_days,
        records=[_record_to_response(r) for r in records],
    )


@router.get("/reports/monthly/pdf")
def download_monthly_report_pdf(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    company_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("time-tracking.reports.read")),
) -> Response:
    """Download a monthly timesheet report as PDF."""
    from .report_generator import generate_monthly_timesheet

    pdf_bytes = generate_monthly_timesheet(
        db=db,
        user_id=current_user.id,
        company_id=UUID(company_id),
        year=year,
        month=month,
    )

    # Generate filename
    month_name = date(year, month, 1).strftime("%B")
    filename = f"timesheet_{year}_{month:02d}_{month_name}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# --- Timesheet Submission ---


@router.post("/submissions", status_code=201)
def submit_timesheet(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    company_id: str = Query(...),
    recipient_email: str = Query(...),
    notes: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("time-tracking.reports.submit")),
) -> dict:
    """Submit a timesheet for a month via email."""
    from calendar import monthrange

    from .models import TimesheetSubmission
    from .report_generator import generate_monthly_timesheet

    # Generate the PDF
    pdf_bytes = generate_monthly_timesheet(
        db=db,
        user_id=current_user.id,
        company_id=UUID(company_id),
        year=year,
        month=month,
    )

    # Get records for the period to store their IDs
    _, last_day = monthrange(year, month)
    period_start = date(year, month, 1)
    period_end = date(year, month, last_day)

    records = (
        db.query(TimeRecord)
        .filter(
            TimeRecord.user_id == current_user.id,
            TimeRecord.company_id == company_id,
            TimeRecord.date >= period_start,
            TimeRecord.date <= period_end,
        )
        .all()
    )
    record_ids = [str(r.id) for r in records]

    # Create submission record
    submission = TimesheetSubmission(
        company_id=UUID(company_id),
        user_id=current_user.id,
        period_start=period_start,
        period_end=period_end,
        period_type="monthly",
        submitted_at=datetime.now(),
        submitted_by=current_user.id,
        sent_to_email=recipient_email,
        record_ids=json.dumps(record_ids),
        status="pending",
        notes=notes,
    )
    db.add(submission)

    # Try to send email
    try:
        from src.services import integration_service

        smtp_provider = integration_service.get_active_smtp_provider(db)
        if smtp_provider:
            month_name = date(year, month, 1).strftime("%B %Y")
            from src.models import Company

            company = db.query(Company).filter(Company.id == company_id).first()
            company_name = company.name if company else "Unknown"

            user_display = current_user.full_name or current_user.username
            subject = f"Timesheet for {month_name} - {user_display}"
            body = f"""Please find attached the timesheet for {month_name}.

Employee: {current_user.full_name or current_user.username}
Company: {company_name}
Period: {period_start.strftime('%d.%m.%Y')} - {period_end.strftime('%d.%m.%Y')}

{notes or ''}

This timesheet was automatically generated by HomeOffice Assistant.
"""
            filename = f"timesheet_{year}_{month:02d}.pdf"

            # Send email with attachment
            import asyncio

            asyncio.get_event_loop().run_until_complete(
                smtp_provider.send_email(
                    to_email=recipient_email,
                    subject=subject,
                    body=body,
                    attachments=[(filename, pdf_bytes, "application/pdf")],
                )
            )
            submission.status = "sent"
        else:
            submission.status = "pending"  # No SMTP configured
    except Exception as e:
        submission.status = "failed"
        submission.notes = f"{notes or ''}\n\nError: {e!s}"

    db.commit()
    db.refresh(submission)

    # Update records with submission ID
    for record in records:
        record.submission_id = submission.id
    db.commit()

    return {
        "id": str(submission.id),
        "status": submission.status,
        "sent_to": recipient_email,
        "period": f"{period_start} - {period_end}",
        "record_count": len(record_ids),
    }


@router.get("/submissions")
def list_submissions(
    company_id: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("time-tracking.reports.read")),
) -> dict:
    """List timesheet submissions."""
    from .models import TimesheetSubmission

    query = db.query(TimesheetSubmission).filter(
        TimesheetSubmission.user_id == current_user.id
    )

    if company_id:
        query = query.filter(TimesheetSubmission.company_id == UUID(company_id))

    total = query.count()
    submissions = (
        query.order_by(TimesheetSubmission.submitted_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "submissions": [
            {
                "id": str(s.id),
                "company_id": str(s.company_id),
                "period_start": s.period_start.isoformat(),
                "period_end": s.period_end.isoformat(),
                "period_type": s.period_type,
                "submitted_at": s.submitted_at.isoformat(),
                "sent_to_email": s.sent_to_email,
                "status": s.status,
                "notes": s.notes,
            }
            for s in submissions
        ],
    }
