# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Check-in and check-out part of the entry service."""

from datetime import date, time
from uuid import UUID

from ..models import (
    EntryType,
    TimeEntry,
)
from .calc import round_time_employer_favor


class TimeClockMixin:
    """Open-entry lookup, check-in and check-out of the entry service.

    Expects ``db``, ``config`` and the entry CRUD methods on the host service.
    """

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
