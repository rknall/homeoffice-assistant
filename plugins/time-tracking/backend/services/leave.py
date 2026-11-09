# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Leave balance service."""

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import (
    CompanyTimeSettings,
    EntryType,
    LeaveBalance,
    TimeEntry,
)
from ..schemas import (
    LeaveBalanceResponse,
)
from .calc import count_effective_leave_days
from .config import TimeTrackingConfig
from .entries import TimeEntryService


class LeaveBalanceService:
    """Service for managing leave balances."""

    def __init__(self, db: Session, config: TimeTrackingConfig | None = None) -> None:
        """Initialize the service.

        Args:
            db: Database session.
            config: Plugin settings; the built-in defaults when omitted.
        """
        self.db = db
        self.config = config or TimeTrackingConfig()

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
            carryover = 0.0

            if company_id:
                settings = (
                    self.db.query(CompanyTimeSettings)
                    .filter(CompanyTimeSettings.company_id == company_id)
                    .first()
                )
                if settings:
                    entitled = settings.vacation_days_per_year

            # Check for carryover from previous year
            prev_balance = (
                self.db.query(LeaveBalance)
                .filter(
                    LeaveBalance.user_id == user_id,
                    LeaveBalance.company_id == company_id,
                    LeaveBalance.year == year - 1,
                )
                .first()
            )

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

    def planned_vacation(
        self, user_id: UUID, year: int, company_id: UUID | None
    ) -> float:
        """Calculate effective planned vacation days for a user.

        Counts vacation entries of the year from today on (a later year in full),
        accounting for multi-day entries, half-days, weekends and holidays.

        Args:
            user_id: The user ID.
            year: The year to calculate for.
            company_id: Optional company filter.

        Returns:
            Total effective planned vacation days.
        """
        today = date.today()
        if year < today.year:
            return 0.0
        # A later year counts in full; the current year from today on.
        first_month = today.month if year == today.year else 1
        future_vacation = TimeEntryService(self.db, self.config).list_entries(
            user_id=user_id,
            from_date=today if year == today.year else date(year, 1, 1),
            to_date=date(year, 12, 31),
            company_id=company_id,
            entry_type=EntryType.VACATION.value,
        )
        holidays_set = self.config.holiday_dates(year)

        vacation_planned = 0.0
        for month in range(first_month, 13):
            # For the current month, only count days from today onwards
            is_today_month = year == today.year and month == today.month
            effective = count_effective_leave_days(
                future_vacation,
                holidays_set,
                year,
                month,
                from_date=today if is_today_month else None,
            )
            vacation_planned += effective.total_vacation_equivalent

        return vacation_planned

    def used_vacation(self, user_id: UUID, year: int, company_id: UUID | None) -> float:
        """Calculate effective used (past) vacation days for a user.

        Counts vacation entries up to yesterday, accounting for multi-day
        entries, half-days, weekends and holidays.

        Args:
            user_id: The user ID.
            year: The year to calculate for.
            company_id: Optional company filter.

        Returns:
            Total effective used vacation days.
        """
        today = date.today()
        year_start = date(year, 1, 1)
        yesterday = today - timedelta(days=1)

        # If we're before the target year, no used vacation yet
        if yesterday < year_start:
            return 0.0

        past_vacation = TimeEntryService(self.db, self.config).list_entries(
            user_id=user_id,
            from_date=year_start,
            to_date=yesterday,
            company_id=company_id,
            entry_type=EntryType.VACATION.value,
        )
        holidays_set = self.config.holiday_dates(year)

        vacation_used = 0.0
        for month in range(1, today.month + 1):
            # For the current month, only count days up to yesterday
            up_to = yesterday if month == today.month else None
            effective = count_effective_leave_days(
                past_vacation, holidays_set, year, month, up_to_date=up_to
            )
            vacation_used += effective.total_vacation_equivalent

        return vacation_used

    def to_response(self, balance: LeaveBalance) -> LeaveBalanceResponse:
        """Build the balance response with the dynamic vacation figures.

        Remaining vacation is entitled plus carryover minus taken and planned.

        Args:
            balance: The stored balance.

        Returns:
            The response schema.
        """
        vacation_taken = self.used_vacation(
            balance.user_id, balance.year, balance.company_id
        )
        vacation_planned = self.planned_vacation(
            balance.user_id, balance.year, balance.company_id
        )
        vacation_remaining = (
            balance.vacation_entitled
            + balance.vacation_carryover
            - vacation_taken
            - vacation_planned
        )
        return LeaveBalanceResponse(
            id=str(balance.id),
            user_id=str(balance.user_id),
            company_id=str(balance.company_id) if balance.company_id else None,
            year=balance.year,
            vacation_entitled=balance.vacation_entitled,
            vacation_carryover=balance.vacation_carryover,
            vacation_taken=vacation_taken,
            vacation_planned=vacation_planned,
            vacation_remaining=vacation_remaining,
            comp_time_balance=balance.comp_time_balance,
            sick_days_taken=balance.sick_days_taken,
            created_at=balance.created_at,
            updated_at=balance.updated_at,
        )

    def find_current_balance(self, user_id: UUID) -> LeaveBalance | None:
        """Return the user's stored balance for the current year, if any."""
        return (
            self.db.query(LeaveBalance)
            .filter(
                LeaveBalance.user_id == user_id,
                LeaveBalance.year == date.today().year,
            )
            .first()
        )

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
            settings = (
                self.db.query(CompanyTimeSettings)
                .filter(CompanyTimeSettings.company_id == company_id)
                .first()
            )

        daily_threshold = (
            settings.daily_overtime_threshold
            if settings
            else self.config.default_work_hours
        )

        # Get all work entries
        query = self.db.query(TimeEntry).filter(
            TimeEntry.user_id == user_id,
            TimeEntry.entry_type.in_(
                [
                    EntryType.WORK.value,
                    EntryType.DOCTOR_VISIT.value,
                ]
            ),
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
        holidays_by_year: dict[int, set[date]] = {}
        for entry_date, hours in daily_hours.items():
            if hours > daily_threshold:
                overtime = hours - daily_threshold
                # Check for Sunday/holiday multiplier
                year_holidays = holidays_by_year.setdefault(
                    entry_date.year, self.config.holiday_dates(entry_date.year)
                )
                is_holiday = entry_date in year_holidays
                weekday = entry_date.weekday()
                if weekday == 6 or is_holiday:  # Sunday
                    overtime *= 2.0
                total_overtime += overtime

        # Subtract comp time taken
        comp_days = (
            self.db.query(func.count(TimeEntry.id))
            .filter(
                TimeEntry.user_id == user_id,
                TimeEntry.entry_type == EntryType.COMP_TIME.value,
            )
            .scalar()
            or 0
        )

        total_taken = float(comp_days) * daily_threshold

        return total_overtime - total_taken


# --- Company Settings Service ---
