# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Pure time and leave calculations."""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, time, timedelta

from sqlalchemy.orm import Session

from src.models.company import Company

from ..models import (
    EntryType,
    TimeEntry,
    WorkLocation,
)
from ..schemas import (
    TimeEntryResponse,
)
from .config import DEFAULT_BREAK_MINUTES


@dataclass
class EffectiveLeaveDays:
    """Result of effective leave day calculation."""

    sick_days: float
    vacation_days: float  # Full vacation days
    half_vacation_days: float  # Half vacation days (each counts as 0.5)

    @property
    def total_vacation_equivalent(self) -> float:
        """Total vacation days including half days."""
        return self.vacation_days + (self.half_vacation_days * 0.5)

    @property
    def total_leave_days(self) -> float:
        """Total effective leave days (sick + vacation)."""
        return self.sick_days + self.total_vacation_equivalent


# --- Time Calculation Functions ---


def round_time_employer_favor(t: time, is_check_in: bool) -> time:
    """Round time to nearest 5 minutes in employer's favor.

    Check-in: Round UP (benefits employer)
    Check-out: Round DOWN (benefits employer)

    Args:
        t: The time to round.
        is_check_in: True if this is a check-in time.

    Returns:
        The rounded time.
    """
    minutes = t.hour * 60 + t.minute

    # Round up for check-in (employer-favor), down for check-out
    rounded = ((minutes + 4) // 5) * 5 if is_check_in else (minutes // 5) * 5

    # Handle overflow past midnight
    if rounded >= 24 * 60:
        rounded = 24 * 60 - 5  # Cap at 23:55

    return time(hour=rounded // 60, minute=rounded % 60)


def calculate_break_minutes(
    gross_hours: float, break_minutes: int = DEFAULT_BREAK_MINUTES
) -> int:
    """Calculate required break based on Austrian law.

    Args:
        gross_hours: Total gross working hours.
        break_minutes: Break required once the day exceeds 6 hours.

    Returns:
        Required break time in minutes.
    """
    if gross_hours > 6.0:
        return break_minutes
    return 0


def company_name_map(db: Session) -> dict[str, str]:
    """Return a mapping of company id to company name."""
    return {str(c.id): c.name for c in db.query(Company).all()}


def entry_to_response(
    entry: TimeEntry,
    company_name: str | None = None,
    is_locked: bool = False,
) -> TimeEntryResponse:
    """Convert a TimeEntry model to the response schema.

    Args:
        entry: The time entry.
        company_name: Display name of the entry's company, if any.
        is_locked: Whether the entry's month is locked for editing.

    Returns:
        The response schema.
    """
    return TimeEntryResponse(
        id=str(entry.id),
        user_id=str(entry.user_id),
        date=entry.date,
        end_date=entry.end_date,
        company_id=str(entry.company_id) if entry.company_id else None,
        company_name=company_name,
        entry_type=EntryType(entry.entry_type),
        is_half_day=entry.is_half_day,
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


def calculate_gross_minutes(check_in: time, check_out: time) -> int:
    """Calculate gross minutes between check-in and check-out.

    Args:
        check_in: Check-in time.
        check_out: Check-out time.

    Returns:
        Gross minutes as an integer.
    """
    in_minutes = check_in.hour * 60 + check_in.minute
    out_minutes = check_out.hour * 60 + check_out.minute

    # Handle overnight shifts
    if out_minutes < in_minutes:
        out_minutes += 24 * 60

    return out_minutes - in_minutes


def times_overlap(start1: time, end1: time, start2: time, end2: time) -> bool:
    """Check if two time ranges overlap.

    Args:
        start1: Start time of first range.
        end1: End time of first range.
        start2: Start time of second range.
        end2: End time of second range.

    Returns:
        True if the time ranges overlap.
    """
    start1_mins = start1.hour * 60 + start1.minute
    end1_mins = end1.hour * 60 + end1.minute
    start2_mins = start2.hour * 60 + start2.minute
    end2_mins = end2.hour * 60 + end2.minute

    # Handle overnight shifts
    if end1_mins < start1_mins:
        end1_mins += 24 * 60
    if end2_mins < start2_mins:
        end2_mins += 24 * 60

    # Adjust for overnight comparisons
    if end1_mins > 24 * 60 and start2_mins < end1_mins - 24 * 60:
        start2_mins += 24 * 60
        end2_mins += 24 * 60
    if end2_mins > 24 * 60 and start1_mins < end2_mins - 24 * 60:
        start1_mins += 24 * 60
        end1_mins += 24 * 60

    return start1_mins < end2_mins and start2_mins < end1_mins


def count_effective_leave_days(
    entries: list[TimeEntry],
    holidays: set[date],
    year: int,
    month: int,
    up_to_date: date | None = None,
    from_date: date | None = None,
) -> EffectiveLeaveDays:
    """Count effective leave days applying priority rules.

    Priority (highest to lowest):
    1. National Holiday - takes precedence over everything
    2. Weekend - takes precedence over sick/vacation
    3. Sickness - takes precedence over vacation
    4. Vacation - lowest priority

    Args:
        entries: List of time entries (vacation/sick only).
        holidays: Set of holiday dates.
        year: Year to calculate for.
        month: Month to calculate for.
        up_to_date: Optional end date limit - only count days up to this date.
        from_date: Optional start date limit - only count days from this date.

    Returns:
        EffectiveLeaveDays with counts for each type.
    """
    month_start = date(year, month, 1)
    _, last_day = monthrange(year, month)
    month_end = date(year, month, last_day)

    # If up_to_date is specified and falls within this month, use it as the end
    if up_to_date and month_start <= up_to_date <= month_end:
        month_end = up_to_date

    # If from_date is specified and falls within this month, use it as the start
    if from_date and month_start < from_date <= month_end:
        month_start = from_date

    # Collect all sick days and vacation days in the month
    sick_dates: set[date] = set()
    vacation_dates: set[date] = set()
    half_vacation_dates: set[date] = set()

    for entry in entries:
        if entry.entry_type not in [EntryType.SICK.value, EntryType.VACATION.value]:
            continue

        # Determine date range (single day or multi-day)
        start = entry.date
        end = entry.end_date if entry.end_date else entry.date

        # Iterate through each day in the entry's range
        current = start
        while current <= end:
            # Only count days within the target month
            if month_start <= current <= month_end:
                if entry.entry_type == EntryType.SICK.value:
                    sick_dates.add(current)
                elif entry.entry_type == EntryType.VACATION.value:
                    if entry.is_half_day:
                        half_vacation_dates.add(current)
                    else:
                        vacation_dates.add(current)
            current += timedelta(days=1)

    # Apply priority rules and count effective days
    effective_sick = 0.0
    effective_vacation = 0.0
    effective_half_vacation = 0.0

    # Process sick days first (higher priority than vacation)
    for d in sick_dates:
        # Skip weekends
        if d.weekday() >= 5:  # Saturday = 5, Sunday = 6
            continue
        # Skip holidays
        if d in holidays:
            continue
        effective_sick += 1.0

    # Process full vacation days (only if not already a sick day)
    for d in vacation_dates:
        # Skip weekends
        if d.weekday() >= 5:
            continue
        # Skip holidays
        if d in holidays:
            continue
        # Skip if sick day takes precedence
        if d in sick_dates:
            continue
        effective_vacation += 1.0

    # Process half vacation days (only if not already a sick day or full vacation)
    for d in half_vacation_dates:
        # Skip weekends
        if d.weekday() >= 5:
            continue
        # Skip holidays
        if d in holidays:
            continue
        # Skip if sick day takes precedence
        if d in sick_dates:
            continue
        # Skip if full vacation already on this day
        if d in vacation_dates:
            continue
        effective_half_vacation += 1.0

    return EffectiveLeaveDays(
        sick_days=effective_sick,
        vacation_days=effective_vacation,
        half_vacation_days=effective_half_vacation,
    )


# --- Time Entry Service ---
