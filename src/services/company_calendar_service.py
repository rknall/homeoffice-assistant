# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Company calendar service for managing external calendar connections."""

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from src.models import CompanyCalendar
from src.schemas.company_calendar import (
    CompanyCalendarCreate,
    CompanyCalendarUpdate,
)


def get_calendars(db: Session, company_id: uuid.UUID) -> list[CompanyCalendar]:
    """Get all calendar connections for a company."""
    return (
        db.query(CompanyCalendar)
        .filter(CompanyCalendar.company_id == company_id)
        .order_by(CompanyCalendar.name)
        .all()
    )


def get_active_calendars(db: Session, company_id: uuid.UUID) -> list[CompanyCalendar]:
    """Get all active calendar connections for a company."""
    return (
        db.query(CompanyCalendar)
        .filter(
            CompanyCalendar.company_id == company_id,
            CompanyCalendar.is_active == True,  # noqa: E712
        )
        .order_by(CompanyCalendar.name)
        .all()
    )


def get_calendar(db: Session, calendar_id: uuid.UUID) -> CompanyCalendar | None:
    """Get a single calendar connection by ID."""
    return db.query(CompanyCalendar).filter(CompanyCalendar.id == calendar_id).first()


def get_calendar_by_company(
    db: Session, company_id: uuid.UUID, calendar_id: uuid.UUID
) -> CompanyCalendar | None:
    """Get a calendar by ID, ensuring it belongs to the specified company."""
    return (
        db.query(CompanyCalendar)
        .filter(
            CompanyCalendar.id == calendar_id,
            CompanyCalendar.company_id == company_id,
        )
        .first()
    )


def create_calendar(
    db: Session, company_id: uuid.UUID, data: CompanyCalendarCreate
) -> CompanyCalendar:
    """Create a new calendar connection for a company."""
    calendar = CompanyCalendar(
        company_id=company_id,
        name=data.name,
        calendar_type=data.calendar_type,
        external_id=data.external_id,
        color=data.color,
        is_active=data.is_active,
        sync_interval_minutes=data.sync_interval_minutes,
    )
    db.add(calendar)
    db.commit()
    db.refresh(calendar)
    return calendar


def update_calendar(
    db: Session, calendar: CompanyCalendar, data: CompanyCalendarUpdate
) -> CompanyCalendar:
    """Update an existing calendar connection."""
    if data.name is not None:
        calendar.name = data.name
    if data.external_id is not None:
        calendar.external_id = data.external_id
    if data.color is not None:
        calendar.color = data.color
    if data.is_active is not None:
        calendar.is_active = data.is_active
    if data.sync_interval_minutes is not None:
        calendar.sync_interval_minutes = data.sync_interval_minutes

    db.commit()
    db.refresh(calendar)
    return calendar


def delete_calendar(db: Session, calendar: CompanyCalendar) -> None:
    """Delete a calendar connection."""
    db.delete(calendar)
    db.commit()


def update_last_synced(db: Session, calendar: CompanyCalendar) -> CompanyCalendar:
    """Update the last_synced_at timestamp for a calendar."""
    calendar.last_synced_at = datetime.utcnow()
    db.commit()
    db.refresh(calendar)
    return calendar


def count_calendars(db: Session, company_id: uuid.UUID) -> int:
    """Count the number of calendar connections for a company."""
    return (
        db.query(CompanyCalendar)
        .filter(CompanyCalendar.company_id == company_id)
        .count()
    )
