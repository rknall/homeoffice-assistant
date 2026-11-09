# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Entry validation and balance bookkeeping for the entry service."""

from datetime import date, time, timedelta
from uuid import UUID

from ..models import (
    CompanyTimeSettings,
    EntryType,
    LeaveBalance,
    TimeEntry,
    UserTimePreferences,
)
from ..schemas import (
    ComplianceWarning,
)
from .calc import count_effective_leave_days, times_overlap


class EntryRulesMixin:
    """Overlap, compliance and bookkeeping steps of the entry service.

    Expects ``db``, ``config`` and ``validator`` on the host service.
    """

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
            warnings.append(
                ComplianceWarning(
                    level="error",
                    code="DAILY_MAX_EXCEEDED",
                    message=f"Daily maximum of 12 hours exceeded ({total_hours:.1f}h)",
                    law_reference="AZG §9",
                )
            )
        elif total_hours > 10:
            warnings.append(
                ComplianceWarning(
                    level="warning",
                    code="DAILY_OVERTIME",
                    message=f"Working more than 10 hours ({total_hours:.1f}h)",
                    law_reference="AZG §9",
                )
            )

        # Check half-vacation overtime rule
        # If a half-vacation is taken, work hours should not exceed 4h
        has_half_vacation = any(
            e.entry_type == EntryType.VACATION.value and e.is_half_day for e in entries
        )
        if has_half_vacation and total_hours > 4:
            warnings.append(
                ComplianceWarning(
                    level="warning",
                    code="HALF_VACATION_OVERTIME",
                    message=(
                        f"Half-vacation day with {total_hours:.1f}h of work. "
                        "Overtime not permitted on half-vacation days."
                    ),
                )
            )

        # Check rest period from previous day
        prev_entries = self.list_entries(
            user_id,
            from_date=entry_date - timedelta(days=1),
            to_date=entry_date - timedelta(days=1),
        )
        if prev_entries and entries:
            # Find latest checkout yesterday and earliest checkin today
            prev_checkouts = [
                e.check_out
                for e in prev_entries
                if e.check_out and e.entry_type == EntryType.WORK.value
            ]
            today_checkins = [
                e.check_in
                for e in entries
                if e.check_in and e.entry_type == EntryType.WORK.value
            ]

            if prev_checkouts and today_checkins:
                last_out = max(prev_checkouts)
                first_in = min(today_checkins)

                out_mins = last_out.hour * 60 + last_out.minute
                in_mins = first_in.hour * 60 + first_in.minute + (24 * 60)
                rest_hours = (in_mins - out_mins) / 60

                if rest_hours < 11:
                    warnings.append(
                        ComplianceWarning(
                            level="warning",
                            code="REST_PERIOD_SHORT",
                            message=(
                                f"Rest period of {rest_hours:.1f}h is less than "
                                f"required 11 hours"
                            ),
                            law_reference="AZG §12",
                        )
                    )

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
        prefs = (
            self.db.query(UserTimePreferences)
            .filter(UserTimePreferences.user_id == user_id)
            .first()
        )

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

        balance = (
            self.db.query(LeaveBalance)
            .filter(
                LeaveBalance.user_id == user_id,
                LeaveBalance.company_id == company_id,
                LeaveBalance.year == year,
            )
            .first()
        )

        if not balance:
            entitled = 25.0
            if company_id:
                settings = (
                    self.db.query(CompanyTimeSettings)
                    .filter(CompanyTimeSettings.company_id == company_id)
                    .first()
                )
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
        leave_entries = (
            self.db.query(TimeEntry)
            .filter(
                TimeEntry.user_id == balance.user_id,
                TimeEntry.date >= year_start,
                TimeEntry.date <= past_end,
                TimeEntry.entry_type.in_(
                    [
                        EntryType.VACATION.value,
                        EntryType.SICK.value,
                    ]
                ),
            )
            .all()
        )

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
