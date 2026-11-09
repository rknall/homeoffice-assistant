# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Time entry service."""

from calendar import monthrange
from datetime import date, time, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import (
    CompanyTimeSettings,
    EntryType,
    TimeEntry,
)
from ..validators import AustrianComplianceValidator
from .calc import calculate_break_minutes, round_time_employer_favor
from .config import TimeTrackingConfig
from .entry_rules import EntryRulesMixin
from .timeclock import TimeClockMixin


class TimeEntryService(TimeClockMixin, EntryRulesMixin):
    """Service for managing time entries."""

    def __init__(self, db: Session, config: TimeTrackingConfig | None = None) -> None:
        """Initialize the service.

        Args:
            db: Database session.
            config: Plugin settings; the built-in defaults when omitted.
        """
        self.db = db
        self.config = config or TimeTrackingConfig()
        self.validator = AustrianComplianceValidator()

    def count_entries(self, user_id: UUID) -> int:
        """Return the number of time entries a user has."""
        return (
            self.db.query(func.count(TimeEntry.id))
            .filter(TimeEntry.user_id == user_id)
            .scalar()
            or 0
        )

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

        # is_half_day cannot be used with multi-day entries
        if is_half_day and end_date and end_date != entry_date:
            raise ValueError("Half-day vacation cannot span multiple days")

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
        entry = (
            self.db.query(TimeEntry)
            .filter(
                TimeEntry.id == entry_id,
                TimeEntry.user_id == user_id,
            )
            .first()
        )

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
                user_id,
                entry.date,
                entry.check_in,
                entry.check_out,
                exclude_entry_id=entry_id,
            )

        # Validate: is_half_day cannot be used with multi-day entries
        if entry.is_half_day and entry.end_date and entry.end_date != entry.date:
            raise ValueError("Half-day vacation cannot span multiple days")

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
        entry = (
            self.db.query(TimeEntry)
            .filter(
                TimeEntry.id == entry_id,
                TimeEntry.user_id == user_id,
            )
            .first()
        )

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
        return (
            self.db.query(TimeEntry)
            .filter(
                TimeEntry.id == entry_id,
                TimeEntry.user_id == user_id,
            )
            .first()
        )

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
            settings = (
                self.db.query(CompanyTimeSettings)
                .filter(CompanyTimeSettings.company_id == entry.company_id)
                .first()
            )

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
        break_minutes = calculate_break_minutes(
            gross_hours, self.config.default_break_minutes
        )
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
