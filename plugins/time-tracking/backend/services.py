# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Time Tracking plugin business logic services."""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, time, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import (
    CompanyTimeSettings,
    CustomHoliday,
    EntryType,
    LeaveBalance,
    TimeEntry,
    UserTimePreferences,
)
from .schemas import ComplianceWarning
from .validators import AustrianComplianceValidator


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


def calculate_break_minutes(gross_hours: float) -> int:
    """Calculate required break based on Austrian law.

    Args:
        gross_hours: Total gross working hours.

    Returns:
        Required break time in minutes.
    """
    if gross_hours > 6.0:
        return 30  # 30min break required after 6h work
    return 0


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


def times_overlap(
    start1: time, end1: time, start2: time, end2: time
) -> bool:
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
    if up_to_date and month_start <= up_to_date < month_end:
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


class TimeEntryService:
    """Service for managing time entries."""

    def __init__(self, db: Session) -> None:
        """Initialize the service.

        Args:
            db: Database session.
        """
        self.db = db
        self.validator = AustrianComplianceValidator()

    def create_entry(
        self,
        user_id: UUID,
        entry_date: date,
        entry_type: str,
        company_id: UUID | None = None,
        end_date: date | None = None,
        is_half_day: bool = False,
        check_in: time | None = None,
        check_out: time | None = None,
        timezone: str | None = None,
        work_location: str | None = None,
        notes: str | None = None,
    ) -> TimeEntry:
        """Create a new time entry.

        Args:
            user_id: The user ID.
            entry_date: The date of the entry.
            entry_type: Type of entry (work, vacation, etc.).
            company_id: Optional company ID.
            end_date: End date for multi-day leave entries (inclusive).
            is_half_day: Whether this is a half-day vacation (vacation only).
            check_in: Check-in time.
            check_out: Check-out time.
            timezone: Timezone.
            work_location: Work location.
            notes: Notes.

        Returns:
            The created time entry.
        """
        # Round times if provided
        if check_in:
            check_in = round_time_employer_favor(check_in, is_check_in=True)
        if check_out:
            check_out = round_time_employer_favor(check_out, is_check_in=False)

        # Validate for time overlaps (only for work entries with times)
        if (
            entry_type in [EntryType.WORK.value, EntryType.DOCTOR_VISIT.value]
            and check_in
            and check_out
        ):
            self._validate_no_overlap(
                user_id, entry_date, check_in, check_out, exclude_entry_id=None
            )

        # is_half_day only applies to vacation entries
        if entry_type != EntryType.VACATION.value:
            is_half_day = False

        entry = TimeEntry(
            user_id=user_id,
            date=entry_date,
            end_date=end_date,
            is_half_day=is_half_day,
            company_id=company_id,
            entry_type=entry_type,
            check_in=check_in,
            check_out=check_out,
            timezone=timezone,
            work_location=work_location,
            notes=notes,
        )

        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)

        # Update user preferences
        self._update_preferences(user_id, entry)

        # Update leave balance if needed
        self._update_leave_balance(user_id, company_id, entry_date.year, entry_type)

        return entry

    def update_entry(
        self,
        entry_id: UUID,
        user_id: UUID,
        **kwargs: Any,
    ) -> TimeEntry | None:
        """Update an existing time entry.

        Args:
            entry_id: The entry ID.
            user_id: The user ID.
            **kwargs: Fields to update.

        Returns:
            The updated entry, or None if not found.
        """
        entry = self.db.query(TimeEntry).filter(
            TimeEntry.id == entry_id,
            TimeEntry.user_id == user_id,
        ).first()

        if not entry:
            return None

        # Check if entry is locked
        if self.is_entry_locked(entry):
            raise ValueError("Cannot edit locked entry")

        # Update fields
        for key, value in kwargs.items():
            if value is not None and hasattr(entry, key):
                if key == "check_in" and value:
                    value = round_time_employer_favor(value, is_check_in=True)
                elif key == "check_out" and value:
                    value = round_time_employer_favor(value, is_check_in=False)
                setattr(entry, key, value)

        # Validate for time overlaps after updates
        if (
            entry.entry_type in [EntryType.WORK.value, EntryType.DOCTOR_VISIT.value]
            and entry.check_in
            and entry.check_out
        ):
            self._validate_no_overlap(
                user_id, entry.date, entry.check_in, entry.check_out,
                exclude_entry_id=entry_id
            )

        self.db.commit()
        self.db.refresh(entry)

        return entry

    def delete_entry(
        self,
        entry_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Delete a time entry.

        Args:
            entry_id: The entry ID.
            user_id: The user ID.

        Returns:
            True if deleted, False if not found.
        """
        entry = self.db.query(TimeEntry).filter(
            TimeEntry.id == entry_id,
            TimeEntry.user_id == user_id,
        ).first()

        if not entry:
            return False

        if self.is_entry_locked(entry):
            raise ValueError("Cannot delete locked entry")

        self.db.delete(entry)
        self.db.commit()

        return True

    def get_entry(
        self,
        entry_id: UUID,
        user_id: UUID,
    ) -> TimeEntry | None:
        """Get a time entry by ID.

        Args:
            entry_id: The entry ID.
            user_id: The user ID.

        Returns:
            The time entry, or None if not found.
        """
        return self.db.query(TimeEntry).filter(
            TimeEntry.id == entry_id,
            TimeEntry.user_id == user_id,
        ).first()

    def list_entries(
        self,
        user_id: UUID,
        from_date: date | None = None,
        to_date: date | None = None,
        company_id: UUID | None = None,
        entry_type: str | None = None,
    ) -> list[TimeEntry]:
        """List time entries with optional filters.

        Args:
            user_id: The user ID.
            from_date: Optional start date filter.
            to_date: Optional end date filter.
            company_id: Optional company filter.
            entry_type: Optional entry type filter.

        Returns:
            List of matching time entries.
        """
        query = self.db.query(TimeEntry).filter(TimeEntry.user_id == user_id)

        if from_date:
            query = query.filter(TimeEntry.date >= from_date)
        if to_date:
            query = query.filter(TimeEntry.date <= to_date)
        if company_id:
            query = query.filter(TimeEntry.company_id == company_id)
        if entry_type:
            query = query.filter(TimeEntry.entry_type == entry_type)

        return query.order_by(TimeEntry.date.desc(), TimeEntry.check_in.asc()).all()

    def get_entries_for_date(
        self,
        user_id: UUID,
        entry_date: date,
        company_id: UUID | None = None,
    ) -> list[TimeEntry]:
        """Get all entries for a specific date.

        Args:
            user_id: The user ID.
            entry_date: The date.
            company_id: Optional company filter.

        Returns:
            List of entries for that date.
        """
        query = self.db.query(TimeEntry).filter(
            TimeEntry.user_id == user_id,
            TimeEntry.date == entry_date,
        )
        if company_id:
            query = query.filter(TimeEntry.company_id == company_id)

        return query.order_by(TimeEntry.check_in.asc()).all()

    def get_open_entry(
        self,
        user_id: UUID,
        company_id: UUID | None = None,
    ) -> TimeEntry | None:
        """Get the currently open entry (checked in but not out).

        Args:
            user_id: The user ID.
            company_id: Optional company filter.

        Returns:
            The open entry, or None.
        """
        today = date.today()
        query = self.db.query(TimeEntry).filter(
            TimeEntry.user_id == user_id,
            TimeEntry.date == today,
            TimeEntry.entry_type == EntryType.WORK.value,
            TimeEntry.check_in.isnot(None),
            TimeEntry.check_out.is_(None),
        )
        if company_id:
            query = query.filter(TimeEntry.company_id == company_id)

        return query.first()

    def has_open_entry(
        self,
        user_id: UUID,
    ) -> bool:
        """Check if user has any open entry today.

        Args:
            user_id: The user ID.

        Returns:
            True if there's an open entry.
        """
        return self.get_open_entry(user_id) is not None

    def check_in(
        self,
        user_id: UUID,
        company_id: UUID | None = None,
        check_in_time: time | None = None,
        timezone: str | None = None,
        work_location: str | None = None,
        notes: str | None = None,
    ) -> TimeEntry:
        """Quick check-in for today.

        Args:
            user_id: The user ID.
            company_id: Optional company ID.
            check_in_time: Optional specific time (defaults to now).
            timezone: Timezone.
            work_location: Work location.
            notes: Notes.

        Returns:
            The created entry.

        Raises:
            ValueError: If already checked in.
        """
        # Check for existing open entry
        open_entry = self.get_open_entry(user_id)
        if open_entry:
            raise ValueError("Already checked in - please check out first")

        # Use current time if not specified
        if check_in_time is None:
            from datetime import datetime
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(timezone) if timezone else ZoneInfo("UTC")
            check_in_time = datetime.now(tz).time()

        return self.create_entry(
            user_id=user_id,
            entry_date=date.today(),
            entry_type=EntryType.WORK.value,
            company_id=company_id,
            check_in=check_in_time,
            check_out=None,
            timezone=timezone,
            work_location=work_location,
            notes=notes,
        )

    def check_out(
        self,
        user_id: UUID,
        check_out_time: time | None = None,
        timezone: str | None = None,
        notes: str | None = None,
    ) -> TimeEntry:
        """Quick check-out for today.

        Args:
            user_id: The user ID.
            check_out_time: Optional specific time (defaults to now).
            timezone: Timezone.
            notes: Optional notes to add.

        Returns:
            The updated entry.

        Raises:
            ValueError: If not checked in.
        """
        open_entry = self.get_open_entry(user_id)
        if not open_entry:
            raise ValueError("Not checked in - nothing to check out")

        # Use current time if not specified
        if check_out_time is None:
            from datetime import datetime
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(timezone) if timezone else ZoneInfo("UTC")
            check_out_time = datetime.now(tz).time()

        # Round in employer's favor
        rounded_time = round_time_employer_favor(check_out_time, is_check_in=False)

        # Ensure check_out >= check_in
        in_minutes = open_entry.check_in.hour * 60 + open_entry.check_in.minute
        out_minutes = rounded_time.hour * 60 + rounded_time.minute

        if out_minutes < in_minutes and (in_minutes - out_minutes) < 10:
            # Same 5-min window rounding issue - use check_in time
            rounded_time = open_entry.check_in

        open_entry.check_out = rounded_time
        if notes:
            open_entry.notes = (
                f"{open_entry.notes}\n{notes}" if open_entry.notes else notes
            )

        self.db.commit()
        self.db.refresh(open_entry)

        # Update preferences
        self._update_preferences(user_id, open_entry)

        return open_entry

    def is_entry_locked(self, entry: TimeEntry) -> bool:
        """Check if an entry is locked for editing.

        Args:
            entry: The time entry.

        Returns:
            True if the entry is locked.
        """
        if entry.submission_id:
            return True

        # Get company settings for lock period
        settings = None
        if entry.company_id:
            settings = self.db.query(CompanyTimeSettings).filter(
                CompanyTimeSettings.company_id == entry.company_id
            ).first()

        lock_days = settings.lock_period_days if settings else 7

        # Calculate lock date (X days after month end)
        _, last_day = monthrange(entry.date.year, entry.date.month)
        month_end = date(entry.date.year, entry.date.month, last_day)
        lock_date = month_end + timedelta(days=lock_days)

        return date.today() > lock_date

    def get_daily_summary(
        self,
        user_id: UUID,
        summary_date: date,
        company_id: UUID | None = None,
    ) -> dict:
        """Get aggregated summary for a day.

        Args:
            user_id: The user ID.
            summary_date: The date.
            company_id: Optional company filter.

        Returns:
            Dictionary with daily totals and entries.
        """
        entries = self.get_entries_for_date(user_id, summary_date, company_id)

        total_minutes = 0
        has_open = False

        for entry in entries:
            if entry.is_open:
                has_open = True
            elif entry.gross_minutes:
                total_minutes += entry.gross_minutes

        gross_hours = total_minutes / 60
        break_minutes = calculate_break_minutes(gross_hours)
        net_hours = gross_hours - (break_minutes / 60)

        # Calculate compliance warnings
        warnings = self._validate_daily_compliance(entries, summary_date, user_id)

        return {
            "date": summary_date,
            "entries": entries,
            "total_gross_hours": gross_hours,
            "total_net_hours": net_hours,
            "break_minutes": break_minutes,
            "entry_count": len(entries),
            "has_open_entry": has_open,
            "warnings": warnings,
        }

    def _validate_no_overlap(
        self,
        user_id: UUID,
        entry_date: date,
        check_in: time,
        check_out: time,
        exclude_entry_id: UUID | None = None,
    ) -> None:
        """Validate that times don't overlap with existing entries.

        Args:
            user_id: The user ID.
            entry_date: The date.
            check_in: Check-in time.
            check_out: Check-out time.
            exclude_entry_id: Entry ID to exclude (for updates).

        Raises:
            ValueError: If overlap detected.
        """
        query = self.db.query(TimeEntry).filter(
            TimeEntry.user_id == user_id,
            TimeEntry.date == entry_date,
            TimeEntry.check_in.isnot(None),
            TimeEntry.check_out.isnot(None),
        )

        if exclude_entry_id:
            query = query.filter(TimeEntry.id != exclude_entry_id)

        existing = query.all()

        for entry in existing:
            if times_overlap(check_in, check_out, entry.check_in, entry.check_out):
                raise ValueError(
                    f"Time overlap with existing entry: "
                    f"{entry.check_in.strftime('%H:%M')}-"
                    f"{entry.check_out.strftime('%H:%M')}"
                )

    def _validate_daily_compliance(
        self,
        entries: list[TimeEntry],
        entry_date: date,
        user_id: UUID,
    ) -> list[ComplianceWarning]:
        """Validate daily compliance rules.

        Args:
            entries: List of entries for the day.
            entry_date: The date.
            user_id: The user ID.

        Returns:
            List of compliance warnings.
        """
        warnings: list[ComplianceWarning] = []

        # Calculate total hours
        total_minutes = sum(e.gross_minutes or 0 for e in entries if not e.is_open)
        total_hours = total_minutes / 60

        # Check daily limits
        if total_hours > 12:
            warnings.append(ComplianceWarning(
                level="error",
                code="DAILY_MAX_EXCEEDED",
                message=f"Daily maximum of 12 hours exceeded ({total_hours:.1f}h)",
                law_reference="AZG §9",
            ))
        elif total_hours > 10:
            warnings.append(ComplianceWarning(
                level="warning",
                code="DAILY_OVERTIME",
                message=f"Working more than 10 hours ({total_hours:.1f}h)",
                law_reference="AZG §9",
            ))

        # Check half-vacation overtime rule
        # If a half-vacation is taken, work hours should not exceed 4h
        has_half_vacation = any(
            e.entry_type == EntryType.VACATION.value and e.is_half_day
            for e in entries
        )
        if has_half_vacation and total_hours > 4:
            warnings.append(ComplianceWarning(
                level="warning",
                code="HALF_VACATION_OVERTIME",
                message=(
                    f"Half-vacation day with {total_hours:.1f}h of work. "
                    "Overtime not permitted on half-vacation days."
                ),
            ))

        # Check rest period from previous day
        prev_entries = self.list_entries(
            user_id,
            from_date=entry_date - timedelta(days=1),
            to_date=entry_date - timedelta(days=1),
        )
        if prev_entries and entries:
            # Find latest checkout yesterday and earliest checkin today
            prev_checkouts = [
                e.check_out for e in prev_entries
                if e.check_out and e.entry_type == EntryType.WORK.value
            ]
            today_checkins = [
                e.check_in for e in entries
                if e.check_in and e.entry_type == EntryType.WORK.value
            ]

            if prev_checkouts and today_checkins:
                last_out = max(prev_checkouts)
                first_in = min(today_checkins)

                out_mins = last_out.hour * 60 + last_out.minute
                in_mins = first_in.hour * 60 + first_in.minute + (24 * 60)
                rest_hours = (in_mins - out_mins) / 60

                if rest_hours < 11:
                    warnings.append(ComplianceWarning(
                        level="warning",
                        code="REST_PERIOD_SHORT",
                        message=(
                            f"Rest period of {rest_hours:.1f}h is less than "
                            f"required 11 hours"
                        ),
                        law_reference="AZG §12",
                    ))

        return warnings

    def _update_preferences(
        self,
        user_id: UUID,
        entry: TimeEntry,
    ) -> None:
        """Update user preferences from an entry.

        Args:
            user_id: The user ID.
            entry: The time entry.
        """
        prefs = self.db.query(UserTimePreferences).filter(
            UserTimePreferences.user_id == user_id
        ).first()

        if not prefs:
            prefs = UserTimePreferences(user_id=user_id)
            self.db.add(prefs)

        prefs.last_company_id = entry.company_id
        prefs.last_work_location = entry.work_location
        prefs.last_check_in = entry.check_in
        prefs.last_check_out = entry.check_out
        self.db.commit()

    def _update_leave_balance(
        self,
        user_id: UUID,
        company_id: UUID | None,
        year: int,
        entry_type: str,
    ) -> None:
        """Update leave balance based on entry type.

        Args:
            user_id: The user ID.
            company_id: The company ID.
            year: The year.
            entry_type: The entry type.
        """
        if entry_type not in [
            EntryType.VACATION.value,
            EntryType.SICK.value,
            EntryType.COMP_TIME.value,
        ]:
            return

        balance = self.db.query(LeaveBalance).filter(
            LeaveBalance.user_id == user_id,
            LeaveBalance.company_id == company_id,
            LeaveBalance.year == year,
        ).first()

        if not balance:
            entitled = 25.0
            if company_id:
                settings = self.db.query(CompanyTimeSettings).filter(
                    CompanyTimeSettings.company_id == company_id
                ).first()
                if settings:
                    entitled = settings.vacation_days_per_year

            balance = LeaveBalance(
                user_id=user_id,
                company_id=company_id,
                year=year,
                vacation_entitled=entitled,
            )
            self.db.add(balance)

        # Recalculate from entries
        self._recalculate_balance(balance)

    def _recalculate_balance(self, balance: LeaveBalance) -> None:
        """Recalculate a leave balance from entries.

        This counts effective leave days by iterating each day in multi-day
        entries and accounting for half-day vacation.

        vacation_taken only includes PAST vacation days (before today).
        Future/planned vacation is calculated separately in the API response.

        Args:
            balance: The leave balance to update.
        """
        year_start = date(balance.year, 1, 1)
        today = date.today()
        # Only count entries up to yesterday (past entries)
        past_end = today - timedelta(days=1)

        # If we're in January of the target year, there are no past entries yet
        if past_end < year_start:
            balance.vacation_taken = 0.0
            balance.sick_days_taken = 0
            self.db.commit()
            return

        # Get vacation and sick entries from the past (before today)
        leave_entries = self.db.query(TimeEntry).filter(
            TimeEntry.user_id == balance.user_id,
            TimeEntry.date >= year_start,
            TimeEntry.date <= past_end,
            TimeEntry.entry_type.in_([
                EntryType.VACATION.value,
                EntryType.SICK.value,
            ]),
        ).all()

        # Get holidays for the year
        holidays_dict = self.validator.get_public_holidays(balance.year)
        holidays_set = set(holidays_dict.keys())

        # Count effective leave days only for past days (up to yesterday)
        total_vacation = 0.0
        total_sick = 0

        for month in range(1, today.month + 1):
            # For the current month, only count days up to yesterday
            up_to = past_end if month == today.month else None
            effective = count_effective_leave_days(
                leave_entries, holidays_set, balance.year, month, up_to_date=up_to
            )
            total_vacation += effective.total_vacation_equivalent
            total_sick += int(effective.sick_days)

        balance.vacation_taken = total_vacation
        balance.sick_days_taken = total_sick
        self.db.commit()


# --- Leave Balance Service ---


class LeaveBalanceService:
    """Service for managing leave balances."""

    def __init__(self, db: Session) -> None:
        """Initialize the service.

        Args:
            db: Database session.
        """
        self.db = db
        self.validator = AustrianComplianceValidator()

    def get_balance(
        self,
        user_id: UUID,
        year: int,
        company_id: UUID | None = None,
    ) -> LeaveBalance:
        """Get or create leave balance for a year.

        Args:
            user_id: The user ID.
            year: The year.
            company_id: Optional company ID.

        Returns:
            The leave balance.
        """
        balance = self.db.query(LeaveBalance).filter(
            LeaveBalance.user_id == user_id,
            LeaveBalance.company_id == company_id,
            LeaveBalance.year == year,
        ).first()

        if not balance:
            entitled = 25.0
            carryover = 0.0

            if company_id:
                settings = self.db.query(CompanyTimeSettings).filter(
                    CompanyTimeSettings.company_id == company_id
                ).first()
                if settings:
                    entitled = settings.vacation_days_per_year

            # Check for carryover from previous year
            prev_balance = self.db.query(LeaveBalance).filter(
                LeaveBalance.user_id == user_id,
                LeaveBalance.company_id == company_id,
                LeaveBalance.year == year - 1,
            ).first()

            if prev_balance:
                carryover = prev_balance.vacation_remaining

            balance = LeaveBalance(
                user_id=user_id,
                company_id=company_id,
                year=year,
                vacation_entitled=entitled,
                vacation_carryover=carryover,
            )
            self.db.add(balance)
            self.db.commit()
            self.db.refresh(balance)

        return balance

    def update_balance(
        self,
        user_id: UUID,
        year: int,
        company_id: UUID | None = None,
        vacation_entitled: float | None = None,
        vacation_carryover: float | None = None,
    ) -> LeaveBalance:
        """Update leave balance settings.

        Args:
            user_id: The user ID.
            year: The year.
            company_id: Optional company ID.
            vacation_entitled: New entitled days.
            vacation_carryover: New carryover days.

        Returns:
            The updated balance.
        """
        balance = self.get_balance(user_id, year, company_id)

        if vacation_entitled is not None:
            balance.vacation_entitled = vacation_entitled
        if vacation_carryover is not None:
            balance.vacation_carryover = vacation_carryover

        self.db.commit()
        self.db.refresh(balance)
        return balance

    def calculate_comp_time_balance(
        self,
        user_id: UUID,
        company_id: UUID | None = None,
    ) -> float:
        """Calculate current comp time balance.

        Args:
            user_id: The user ID.
            company_id: Optional company ID.

        Returns:
            Current comp time balance in hours.
        """
        # Get company settings
        settings = None
        if company_id:
            settings = self.db.query(CompanyTimeSettings).filter(
                CompanyTimeSettings.company_id == company_id
            ).first()

        daily_threshold = settings.daily_overtime_threshold if settings else 8.0

        # Get all work entries
        query = self.db.query(TimeEntry).filter(
            TimeEntry.user_id == user_id,
            TimeEntry.entry_type.in_([
                EntryType.WORK.value,
                EntryType.DOCTOR_VISIT.value,
            ]),
            TimeEntry.check_in.isnot(None),
            TimeEntry.check_out.isnot(None),
        )
        if company_id:
            query = query.filter(TimeEntry.company_id == company_id)

        entries = query.all()

        # Group by date and calculate daily overtime
        daily_hours: dict[date, float] = {}
        for entry in entries:
            hours = (entry.gross_minutes or 0) / 60
            if entry.date in daily_hours:
                daily_hours[entry.date] += hours
            else:
                daily_hours[entry.date] = hours

        # Calculate total overtime
        total_overtime = 0.0
        for entry_date, hours in daily_hours.items():
            if hours > daily_threshold:
                overtime = hours - daily_threshold
                # Check for Sunday/holiday multiplier
                is_holiday = self.validator.is_public_holiday(entry_date)
                weekday = entry_date.weekday()
                if weekday == 6 or is_holiday:  # Sunday
                    overtime *= 2.0
                total_overtime += overtime

        # Subtract comp time taken
        comp_days = self.db.query(func.count(TimeEntry.id)).filter(
            TimeEntry.user_id == user_id,
            TimeEntry.entry_type == EntryType.COMP_TIME.value,
        ).scalar() or 0

        total_taken = float(comp_days) * daily_threshold

        return total_overtime - total_taken


# --- Company Settings Service ---


class CompanySettingsService:
    """Service for managing company time settings."""

    def __init__(self, db: Session) -> None:
        """Initialize the service.

        Args:
            db: Database session.
        """
        self.db = db

    def get_settings(self, company_id: UUID) -> CompanyTimeSettings | None:
        """Get time settings for a company.

        Args:
            company_id: The company ID.

        Returns:
            The company settings, or None if not found.
        """
        return self.db.query(CompanyTimeSettings).filter(
            CompanyTimeSettings.company_id == company_id
        ).first()

    def get_or_create_settings(self, company_id: UUID) -> CompanyTimeSettings:
        """Get or create time settings for a company.

        Args:
            company_id: The company ID.

        Returns:
            The company settings.
        """
        settings = self.get_settings(company_id)
        if not settings:
            settings = CompanyTimeSettings(company_id=company_id)
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)
        return settings

    def update_settings(
        self,
        company_id: UUID,
        **kwargs: Any,
    ) -> CompanyTimeSettings:
        """Update company time settings.

        Args:
            company_id: The company ID.
            **kwargs: Fields to update.

        Returns:
            The updated settings.
        """
        settings = self.get_or_create_settings(company_id)

        for key, value in kwargs.items():
            if value is not None and hasattr(settings, key):
                setattr(settings, key, value)

        self.db.commit()
        self.db.refresh(settings)
        return settings


# --- Holiday Service ---


class HolidayService:
    """Service for managing holidays."""

    def __init__(self, db: Session) -> None:
        """Initialize the service.

        Args:
            db: Database session.
        """
        self.db = db
        self.validator = AustrianComplianceValidator()

    def get_public_holidays(
        self,
        year: int,
        country_code: str = "AT",
        region: str | None = None,
    ) -> dict[date, str]:
        """Get public holidays for a year.

        Args:
            year: The year.
            country_code: ISO country code.
            region: Optional region/state code.

        Returns:
            Dictionary of date to holiday name.
        """
        return self.validator.get_public_holidays(year, region)

    def get_custom_holidays(
        self,
        user_id: UUID,
        year: int,
        company_id: UUID | None = None,
    ) -> list[CustomHoliday]:
        """Get user's custom holidays for a year.

        Args:
            user_id: The user ID.
            year: The year.
            company_id: Optional company filter.

        Returns:
            List of custom holidays.
        """
        query = self.db.query(CustomHoliday).filter(
            CustomHoliday.user_id == user_id,
            func.extract("year", CustomHoliday.date) == year,
        )

        if company_id:
            query = query.filter(
                (CustomHoliday.company_id == company_id)
                | (CustomHoliday.company_id.is_(None))
            )
        else:
            query = query.filter(CustomHoliday.company_id.is_(None))

        return query.all()

    def create_custom_holiday(
        self,
        user_id: UUID,
        holiday_date: date,
        name: str,
        company_id: UUID | None = None,
    ) -> CustomHoliday:
        """Create a custom holiday.

        Args:
            user_id: The user ID.
            holiday_date: The date.
            name: The holiday name.
            company_id: Optional company ID.

        Returns:
            The created holiday.
        """
        holiday = CustomHoliday(
            user_id=user_id,
            date=holiday_date,
            name=name,
            company_id=company_id,
        )
        self.db.add(holiday)
        self.db.commit()
        self.db.refresh(holiday)
        return holiday

    def is_holiday(
        self,
        check_date: date,
        user_id: UUID | None = None,
        company_id: UUID | None = None,
        country_code: str = "AT",
    ) -> tuple[bool, str | None]:
        """Check if a date is a holiday.

        Args:
            check_date: The date to check.
            user_id: Optional user for custom holidays.
            company_id: Optional company for custom holidays.
            country_code: ISO country code.

        Returns:
            Tuple of (is_holiday, holiday_name).
        """
        # Check public holidays first
        holiday_name = self.validator.get_holiday_name(check_date)
        if holiday_name:
            return True, holiday_name

        # Check custom holidays
        if user_id:
            custom = self.db.query(CustomHoliday).filter(
                CustomHoliday.user_id == user_id,
                CustomHoliday.date == check_date,
            )
            if company_id:
                custom = custom.filter(
                    (CustomHoliday.company_id == company_id)
                    | (CustomHoliday.company_id.is_(None))
                )
            custom = custom.first()
            if custom:
                return True, custom.name

        return False, None
