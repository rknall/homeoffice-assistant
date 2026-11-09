# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Monthly report service."""

from calendar import monthrange
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.user import User

from ..models import (
    EntryType,
    TimeEntry,
)
from ..schemas import (
    DailySummary,
    MonthlyReportResponse,
    TimeEntryResponse,
)
from .calc import (
    calculate_break_minutes,
    company_name_map,
    count_effective_leave_days,
    entry_to_response,
)
from .config import TimeTrackingConfig
from .entries import TimeEntryService


class ReportService:
    """Service building the monthly report."""

    def __init__(self, db: Session, config: TimeTrackingConfig | None = None) -> None:
        """Initialize the service.

        Args:
            db: Database session.
            config: Plugin settings; the built-in defaults when omitted.
        """
        self.db = db
        self.config = config or TimeTrackingConfig()
        self.entries = TimeEntryService(db, self.config)

    def monthly_report(
        self,
        user: User,
        year: int,
        month: int,
        company_id: UUID | None = None,
    ) -> MonthlyReportResponse:
        """Build the monthly report of a user.

        Args:
            user: The reporting user.
            year: The report year.
            month: The report month (1-12).
            company_id: Optional company filter.

        Returns:
            The monthly report with entries and daily summaries.
        """
        company_map = company_name_map(self.db)
        _, last_day = monthrange(year, month)
        entries = self.entries.list_entries(
            user_id=user.id,
            from_date=date(year, month, 1),
            to_date=date(year, month, last_day),
            company_id=company_id,
        )

        work_dates: set[date] = set()
        total_gross_minutes = 0
        comp_time_days = 0
        holiday_days = 0
        for entry in entries:
            if entry.entry_type == EntryType.WORK.value:
                if entry.gross_minutes:
                    work_dates.add(entry.date)
                    total_gross_minutes += entry.gross_minutes
            elif entry.entry_type == EntryType.COMP_TIME.value:
                comp_time_days += 1
            elif entry.entry_type == EntryType.PUBLIC_HOLIDAY.value:
                holiday_days += 1

        holidays_set = self.config.holiday_dates(year)
        effective_leave = count_effective_leave_days(entries, holidays_set, year, month)

        # Weekdays minus public holidays
        base_work_days = sum(
            1
            for day in range(1, last_day + 1)
            if date(year, month, day).weekday() < 5
            and date(year, month, day) not in holidays_set
        )
        expected_work_days = base_work_days - effective_leave.total_leave_days

        total_work_days = len(work_dates)
        total_gross_hours = total_gross_minutes / 60
        avg_hours_per_day = total_gross_hours / max(total_work_days, 1)
        daily_break = calculate_break_minutes(
            avg_hours_per_day, self.config.default_break_minutes
        )
        break_minutes = daily_break * total_work_days
        total_net_hours = total_gross_hours - (break_minutes / 60)
        expected_hours = expected_work_days * self.config.default_work_hours
        overtime_hours = max(0, total_net_hours - expected_hours)

        def to_response(entry: TimeEntry) -> TimeEntryResponse:
            return entry_to_response(
                entry,
                company_map.get(str(entry.company_id)) if entry.company_id else None,
                self.entries.is_entry_locked(entry),
            )

        daily_summaries = []
        for d in sorted({e.date for e in entries}):
            summary = self.entries.get_daily_summary(user.id, d, company_id)
            daily_summaries.append(
                DailySummary(
                    date=summary["date"],
                    entries=[to_response(e) for e in summary["entries"]],
                    total_gross_hours=summary["total_gross_hours"],
                    total_net_hours=summary["total_net_hours"],
                    break_minutes=summary["break_minutes"],
                    entry_count=summary["entry_count"],
                    has_open_entry=summary["has_open_entry"],
                    warnings=summary["warnings"],
                )
            )

        return MonthlyReportResponse(
            year=year,
            month=month,
            company_id=str(company_id) if company_id else None,
            company_name=company_map.get(str(company_id)) if company_id else None,
            user_name=user.username,
            total_work_days=total_work_days,
            expected_work_days=expected_work_days,
            total_gross_hours=round(total_gross_hours, 2),
            total_net_hours=round(total_net_hours, 2),
            total_break_minutes=break_minutes,
            overtime_hours=round(overtime_hours, 2),
            vacation_days=effective_leave.total_vacation_equivalent,
            sick_days=effective_leave.sick_days,
            comp_time_days=comp_time_days,
            public_holiday_days=holiday_days,
            entries=[to_response(e) for e in entries],
            daily_summaries=daily_summaries,
        )
