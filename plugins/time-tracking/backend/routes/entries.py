# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Time entry and check-in/out routes."""

from datetime import date
from uuid import UUID

from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, require_permission
from src.database import get_db
from src.models.user import User

from ..schemas import (
    CheckInRequest,
    CheckInStatusResponse,
    CheckOutRequest,
    DailySummary,
    TimeEntryCreate,
    TimeEntryResponse,
    TimeEntryUpdate,
)
from ..services import (
    TimeEntryService,
    TimeTrackingConfig,
    company_name_map,
    entry_to_response,
)
from .common import (
    RECORDS_DELETE,
    RECORDS_READ,
    RECORDS_WRITE,
    get_plugin_config,
    require_company_code,
    router,
)


@router.get("/entries", response_model=list[TimeEntryResponse])
def list_entries(
    company_id: UUID | None = None,
    start_date: str | None = Query(None, alias="from"),
    end_date: str | None = Query(None, alias="to"),
    entry_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission(RECORDS_READ, company_id_param="company_id")
    ),
) -> list[TimeEntryResponse]:
    """List time entries with optional filters."""
    service = TimeEntryService(db)
    company_map = company_name_map(db)

    from_date = date.fromisoformat(start_date) if start_date else None
    to_date = date.fromisoformat(end_date) if end_date else None

    entries = service.list_entries(
        user_id=current_user.id,
        from_date=from_date,
        to_date=to_date,
        company_id=company_id,
        entry_type=entry_type,
    )

    responses = []
    for entry in entries:
        cid = str(entry.company_id) if entry.company_id else None
        company_name = company_map.get(cid) if cid else None
        is_locked = service.is_entry_locked(entry)
        responses.append(entry_to_response(entry, company_name, is_locked))

    return responses


@router.post("/entries", response_model=TimeEntryResponse)
def create_entry(
    data: TimeEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TimeEntryResponse:
    """Create a new time entry."""
    company_uuid = require_company_code(
        db, current_user, RECORDS_WRITE, data.company_id
    )
    service = TimeEntryService(db)
    company_map = company_name_map(db)

    try:
        entry = service.create_entry(
            user_id=current_user.id,
            entry_date=data.date,
            entry_type=data.entry_type.value,
            company_id=company_uuid,
            end_date=data.end_date,
            is_half_day=data.is_half_day,
            check_in=data.check_in,
            check_out=data.check_out,
            timezone=data.timezone,
            work_location=data.work_location.value if data.work_location else None,
            notes=data.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    company_name = company_map.get(str(entry.company_id)) if entry.company_id else None
    return entry_to_response(entry, company_name)


@router.get("/entries/{entry_id}", response_model=TimeEntryResponse)
def get_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(RECORDS_READ)),
) -> TimeEntryResponse:
    """Get a time entry by ID."""
    service = TimeEntryService(db)
    company_map = company_name_map(db)

    entry = service.get_entry(entry_id, current_user.id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    company_name = company_map.get(str(entry.company_id)) if entry.company_id else None
    is_locked = service.is_entry_locked(entry)
    return entry_to_response(entry, company_name, is_locked)


@router.put("/entries/{entry_id}", response_model=TimeEntryResponse)
def update_entry(
    entry_id: UUID,
    data: TimeEntryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TimeEntryResponse:
    """Update an existing time entry.

    Moving the entry to a company needs the write code for that company;
    without a company in the body the code must be held globally.
    """
    company_uuid = require_company_code(
        db, current_user, RECORDS_WRITE, data.company_id
    )
    service = TimeEntryService(db)
    company_map = company_name_map(db)

    update_data = data.model_dump(exclude_unset=True)
    if company_uuid is not None:
        update_data["company_id"] = company_uuid

    # Convert enums to strings
    if update_data.get("entry_type"):
        update_data["entry_type"] = update_data["entry_type"].value
    if update_data.get("work_location"):
        update_data["work_location"] = update_data["work_location"].value

    try:
        entry = service.update_entry(entry_id, current_user.id, **update_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    company_name = company_map.get(str(entry.company_id)) if entry.company_id else None
    is_locked = service.is_entry_locked(entry)
    return entry_to_response(entry, company_name, is_locked)


@router.delete("/entries/{entry_id}", status_code=204)
def delete_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(RECORDS_DELETE)),
) -> None:
    """Delete a time entry."""
    service = TimeEntryService(db)

    try:
        deleted = service.delete_entry(entry_id, current_user.id)
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
    company_uuid = require_company_code(
        db, current_user, RECORDS_WRITE, data.company_id
    )
    service = TimeEntryService(db)
    company_map = company_name_map(db)

    try:
        entry = service.check_in(
            user_id=current_user.id,
            company_id=company_uuid,
            timezone=data.timezone,
            work_location=data.work_location.value if data.work_location else None,
            notes=data.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    company_name = company_map.get(str(entry.company_id)) if entry.company_id else None
    return entry_to_response(entry, company_name)


@router.post("/check-out", response_model=TimeEntryResponse)
def check_out(
    data: CheckOutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(RECORDS_WRITE)),
) -> TimeEntryResponse:
    """Quick check-out for today."""
    service = TimeEntryService(db)
    company_map = company_name_map(db)

    try:
        entry = service.check_out(
            user_id=current_user.id,
            timezone=data.timezone,
            notes=data.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    company_name = company_map.get(str(entry.company_id)) if entry.company_id else None
    return entry_to_response(entry, company_name)


@router.get("/status", response_model=CheckInStatusResponse)
def get_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(RECORDS_READ)),
) -> CheckInStatusResponse:
    """Get current check-in status."""
    service = TimeEntryService(db)
    company_map = company_name_map(db)

    open_entry = service.get_open_entry(current_user.id)
    today_entries = service.get_entries_for_date(current_user.id, date.today())

    # Calculate today's total hours
    total_minutes = sum(e.gross_minutes or 0 for e in today_entries if not e.is_open)
    total_hours = total_minutes / 60

    # Build response with proper company name lookups
    open_entry_response = None
    if open_entry:
        oe_cid = str(open_entry.company_id) if open_entry.company_id else None
        open_entry_response = entry_to_response(
            open_entry, company_map.get(oe_cid) if oe_cid else None
        )

    today_responses = []
    for e in today_entries:
        e_cid = str(e.company_id) if e.company_id else None
        today_responses.append(
            entry_to_response(e, company_map.get(e_cid) if e_cid else None)
        )

    return CheckInStatusResponse(
        is_checked_in=open_entry is not None,
        open_entry=open_entry_response,
        today_entries=today_responses,
        today_total_hours=total_hours,
    )


@router.get("/today", response_model=list[TimeEntryResponse])
def get_today(
    company_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission(RECORDS_READ, company_id_param="company_id")
    ),
) -> list[TimeEntryResponse]:
    """Get today's entries."""
    service = TimeEntryService(db)
    company_map = company_name_map(db)

    entries = service.get_entries_for_date(current_user.id, date.today(), company_id)

    return [
        entry_to_response(
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
    company_id: UUID | None = None,
    db: Session = Depends(get_db),
    config: TimeTrackingConfig = Depends(get_plugin_config),
    current_user: User = Depends(
        require_permission(RECORDS_READ, company_id_param="company_id")
    ),
) -> DailySummary:
    """Get aggregated summary for a specific date."""
    service = TimeEntryService(db, config)
    company_map = company_name_map(db)

    target_date = date.fromisoformat(summary_date)

    summary = service.get_daily_summary(current_user.id, target_date, company_id)

    return DailySummary(
        date=summary["date"],
        entries=[
            entry_to_response(
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
