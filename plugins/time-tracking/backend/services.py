# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Time Tracking plugin business logic services."""

import json
from calendar import monthrange
from datetime import date, time, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import (
    CompanyTimeSettings,
    CustomHoliday,
    DayType,
    LeaveBalance,
    TimeRecord,
    TimeRecordAudit,
    UserTimePreferences,
)
from .schemas import ComplianceWarning
from .validators import AustrianComplianceValidator

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


def calculate_gross_hours(check_in: time, check_out: time) -> float:
    """Calculate gross hours between check-in and check-out.

    Args:
        check_in: Check-in time.
        check_out: Check-out time.

    Returns:
        Gross hours as a float.
    """
    # Convert to minutes for calculation
    in_minutes = check_in.hour * 60 + check_in.minute
    out_minutes = check_out.hour * 60 + check_out.minute

    # Handle overnight shifts
    if out_minutes < in_minutes:
        out_minutes += 24 * 60

    return (out_minutes - in_minutes) / 60


def calculate_net_hours(
    check_in: time,
    check_out: time,
    break_override: int | None = None,
) -> tuple[float, int, float]:
    """Calculate net hours, break time, and gross hours.

    Args:
        check_in: Check-in time.
        check_out: Check-out time.
        break_override: Optional manual break override in minutes.

    Returns:
        Tuple of (net_hours, break_minutes, gross_hours).
    """
    gross_hours = calculate_gross_hours(check_in, check_out)
    break_minutes = (
        break_override
        if break_override is not None
        else calculate_break_minutes(gross_hours)
    )
    net_hours = gross_hours - (break_minutes / 60)

    return net_hours, break_minutes, gross_hours


def calculate_comp_time_earned(
    record: TimeRecord,
    settings: CompanyTimeSettings | None,
    is_public_holiday: bool = False,
) -> float:
    """Calculate comp time earned for a day.

    Args:
        record: The time record.
        settings: Company time settings.
        is_public_holiday: Whether the day is a public holiday.

    Returns:
        Comp time hours earned.
    """
    if record.day_type not in [DayType.WORK.value, DayType.DOCTOR_VISIT.value]:
        return 0.0

    if record.net_hours is None:
        return 0.0

    daily_threshold = settings.daily_overtime_threshold if settings else 8.0
    overtime_threshold = settings.overtime_threshold_hours if settings else 0.0

    # Calculate overtime (hours beyond daily threshold)
    overtime = max(0.0, record.net_hours - daily_threshold)

    # Apply threshold (first X hours don't count)
    if overtime <= overtime_threshold:
        return 0.0

    overtime -= overtime_threshold

    # Apply multipliers for Sunday/holiday work
    multiplier = 1.0
    if record.date:
        weekday = record.date.weekday()
        if weekday == 6 or is_public_holiday:  # Sunday
            multiplier = 2.0

    return overtime * multiplier


# --- Time Record Service ---


class TimeRecordService:
    """Service for managing time records."""

    def __init__(self, db: Session) -> None:
        """Initialize the service.

        Args:
            db: Database session.
        """
        self.db = db
        self.validator = AustrianComplianceValidator()

    def create_record(
        self,
        user_id: UUID,
        record_date: date,
        day_type: str,
        company_id: UUID | None = None,
        check_in: time | None = None,
        check_out: time | None = None,
        check_in_timezone: str | None = None,
        check_out_timezone: str | None = None,
        partial_absence_type: str | None = None,
        partial_absence_hours: float | None = None,
        work_location: str | None = None,
        notes: str | None = None,
    ) -> TimeRecord:
        """Create a new time record.

        Args:
            user_id: The user ID.
            record_date: The date of the record.
            day_type: Type of day (work, vacation, etc.).
            company_id: Optional company ID.
            check_in: Check-in time.
            check_out: Check-out time.
            check_in_timezone: Timezone for check-in.
            check_out_timezone: Timezone for check-out.
            partial_absence_type: Type of partial absence.
            partial_absence_hours: Hours of partial absence.
            work_location: Work location.
            notes: Notes.

        Returns:
            The created time record.
        """
        # Round times if provided
        if check_in:
            check_in = round_time_employer_favor(check_in, is_check_in=True)
        if check_out:
            check_out = round_time_employer_favor(check_out, is_check_in=False)

        # Calculate hours if check-in and check-out provided
        gross_hours = None
        break_minutes = None
        net_hours = None

        if check_in and check_out:
            net_hours, break_minutes, gross_hours = calculate_net_hours(
                check_in, check_out
            )

        # Create the record
        record = TimeRecord(
            user_id=user_id,
            date=record_date,
            day_type=day_type,
            company_id=company_id,
            check_in=check_in,
            check_out=check_out,
            check_in_timezone=check_in_timezone,
            check_out_timezone=check_out_timezone,
            partial_absence_type=partial_absence_type,
            partial_absence_hours=partial_absence_hours,
            gross_hours=gross_hours,
            break_minutes=break_minutes,
            net_hours=net_hours,
            work_location=work_location,
            notes=notes,
        )

        # Validate compliance
        warnings = self._validate_record(record, user_id)
        if warnings:
            record.compliance_warnings = json.dumps(
                [w.model_dump() for w in warnings]
            )

        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        # Create audit entry
        self._create_audit(record, user_id, "created")

        # Update user preferences
        self._update_preferences(user_id, record)

        # Update leave balance if needed
        self._update_leave_balance(user_id, company_id, record_date.year, day_type)

        return record

    def update_record(
        self,
        record_id: UUID,
        user_id: UUID,
        **kwargs: Any,
    ) -> TimeRecord | None:
        """Update an existing time record.

        Args:
            record_id: The record ID.
            user_id: The user ID (for audit).
            **kwargs: Fields to update.

        Returns:
            The updated record, or None if not found.
        """
        record = self.db.query(TimeRecord).filter(
            TimeRecord.id == record_id,
            TimeRecord.user_id == user_id,
        ).first()

        if not record:
            return None

        # Check if record is locked
        if self.is_record_locked(record):
            raise ValueError("Cannot edit locked record")

        # Store old values for audit
        old_values = self._record_to_dict(record)

        # Update fields
        for key, value in kwargs.items():
            if value is not None and hasattr(record, key):
                if key == "check_in" and value:
                    value = round_time_employer_favor(value, is_check_in=True)
                elif key == "check_out" and value:
                    value = round_time_employer_favor(value, is_check_in=False)
                setattr(record, key, value)

        # Recalculate hours if times changed
        if record.check_in and record.check_out:
            net_hours, break_minutes, gross_hours = calculate_net_hours(
                record.check_in, record.check_out
            )
            record.gross_hours = gross_hours
            record.break_minutes = break_minutes
            record.net_hours = net_hours

        # Re-validate compliance
        warnings = self._validate_record(record, user_id)
        record.compliance_warnings = (
            json.dumps([w.model_dump() for w in warnings]) if warnings else None
        )

        self.db.commit()
        self.db.refresh(record)

        # Create audit entry
        self._create_audit(record, user_id, "updated", old_values)

        return record

    def delete_record(
        self,
        record_id: UUID,
        user_id: UUID,
        reason: str | None = None,
    ) -> bool:
        """Delete a time record.

        Args:
            record_id: The record ID.
            user_id: The user ID.
            reason: Optional reason for deletion.

        Returns:
            True if deleted, False if not found.
        """
        record = self.db.query(TimeRecord).filter(
            TimeRecord.id == record_id,
            TimeRecord.user_id == user_id,
        ).first()

        if not record:
            return False

        # Check if record is locked
        if self.is_record_locked(record):
            raise ValueError("Cannot delete locked record")

        # Store values for audit
        old_values = self._record_to_dict(record)

        # Create audit entry before deletion
        audit = TimeRecordAudit(
            time_record_id=record.id,
            changed_by=user_id,
            change_type="deleted",
            old_values=json.dumps(old_values),
            new_values="{}",
            reason=reason,
        )
        self.db.add(audit)

        self.db.delete(record)
        self.db.commit()

        return True

    def get_record(
        self,
        record_id: UUID,
        user_id: UUID,
    ) -> TimeRecord | None:
        """Get a time record by ID.

        Args:
            record_id: The record ID.
            user_id: The user ID.

        Returns:
            The time record, or None if not found.
        """
        return self.db.query(TimeRecord).filter(
            TimeRecord.id == record_id,
            TimeRecord.user_id == user_id,
        ).first()

    def get_record_by_date(
        self,
        user_id: UUID,
        record_date: date,
    ) -> TimeRecord | None:
        """Get a time record for a specific date.

        Args:
            user_id: The user ID.
            record_date: The date.

        Returns:
            The time record, or None if not found.
        """
        return self.db.query(TimeRecord).filter(
            TimeRecord.user_id == user_id,
            TimeRecord.date == record_date,
        ).first()

    def list_records(
        self,
        user_id: UUID,
        from_date: date | None = None,
        to_date: date | None = None,
        company_id: UUID | None = None,
        day_type: str | None = None,
    ) -> list[TimeRecord]:
        """List time records with optional filters.

        Args:
            user_id: The user ID.
            from_date: Optional start date filter.
            to_date: Optional end date filter.
            company_id: Optional company filter.
            day_type: Optional day type filter.

        Returns:
            List of matching time records.
        """
        query = self.db.query(TimeRecord).filter(TimeRecord.user_id == user_id)

        if from_date:
            query = query.filter(TimeRecord.date >= from_date)
        if to_date:
            query = query.filter(TimeRecord.date <= to_date)
        if company_id:
            query = query.filter(TimeRecord.company_id == company_id)
        if day_type:
            query = query.filter(TimeRecord.day_type == day_type)

        return query.order_by(TimeRecord.date.desc()).all()

    def get_records_for_month(
        self,
        user_id: UUID,
        year: int,
        month: int,
        company_id: UUID | None = None,
    ) -> list[TimeRecord]:
        """Get all records for a specific month.

        Args:
            user_id: The user ID.
            year: The year.
            month: The month (1-12).
            company_id: Optional company filter.

        Returns:
            List of time records for the month.
        """
        _, last_day = monthrange(year, month)
        from_date = date(year, month, 1)
        to_date = date(year, month, last_day)

        return self.list_records(user_id, from_date, to_date, company_id)

    def is_record_locked(self, record: TimeRecord) -> bool:
        """Check if a record is locked for editing.

        Args:
            record: The time record.

        Returns:
            True if the record is locked.
        """
        if record.submission_id:
            return True

        # Get company settings for lock period
        settings = None
        if record.company_id:
            settings = self.db.query(CompanyTimeSettings).filter(
                CompanyTimeSettings.company_id == record.company_id
            ).first()

        lock_days = settings.lock_period_days if settings else 7

        # Calculate lock date (X days after month end)
        _, last_day = monthrange(record.date.year, record.date.month)
        month_end = date(record.date.year, record.date.month, last_day)
        lock_date = month_end + timedelta(days=lock_days)

        return date.today() > lock_date

    def _validate_record(
        self,
        record: TimeRecord,
        user_id: UUID,
    ) -> list[ComplianceWarning]:
        """Validate a record against compliance rules.

        Args:
            record: The time record.
            user_id: The user ID.

        Returns:
            List of compliance warnings.
        """
        warnings: list[ComplianceWarning] = []

        # Validate daily hours
        warnings.extend(self.validator.validate_daily_hours(record))

        # Validate rest period against previous record
        previous = self.db.query(TimeRecord).filter(
            TimeRecord.user_id == user_id,
            TimeRecord.date < record.date,
        ).order_by(TimeRecord.date.desc()).first()

        warnings.extend(self.validator.validate_rest_period(record, previous))

        return warnings

    def _create_audit(
        self,
        record: TimeRecord,
        user_id: UUID,
        change_type: str,
        old_values: dict | None = None,
    ) -> None:
        """Create an audit entry for a record change.

        Args:
            record: The time record.
            user_id: The user who made the change.
            change_type: Type of change (created, updated, deleted).
            old_values: Previous values (for updates).
        """
        audit = TimeRecordAudit(
            time_record_id=record.id,
            changed_by=user_id,
            change_type=change_type,
            old_values=json.dumps(old_values) if old_values else None,
            new_values=json.dumps(self._record_to_dict(record)),
        )
        self.db.add(audit)
        self.db.commit()

    def _record_to_dict(self, record: TimeRecord) -> dict:
        """Convert a record to a dictionary for audit purposes.

        Args:
            record: The time record.

        Returns:
            Dictionary representation.
        """
        return {
            "date": str(record.date),
            "day_type": record.day_type,
            "check_in": str(record.check_in) if record.check_in else None,
            "check_out": str(record.check_out) if record.check_out else None,
            "gross_hours": record.gross_hours,
            "break_minutes": record.break_minutes,
            "net_hours": record.net_hours,
            "work_location": record.work_location,
            "notes": record.notes,
        }

    def _update_preferences(
        self,
        user_id: UUID,
        record: TimeRecord,
    ) -> None:
        """Update user preferences from a record.

        Args:
            user_id: The user ID.
            record: The time record.
        """
        prefs = self.db.query(UserTimePreferences).filter(
            UserTimePreferences.user_id == user_id
        ).first()

        if not prefs:
            prefs = UserTimePreferences(user_id=user_id)
            self.db.add(prefs)

        prefs.last_company_id = record.company_id
        prefs.last_work_location = record.work_location
        prefs.last_check_in = record.check_in
        prefs.last_check_out = record.check_out
        self.db.commit()

    def _update_leave_balance(
        self,
        user_id: UUID,
        company_id: UUID | None,
        year: int,
        day_type: str,
    ) -> None:
        """Update leave balance based on day type.

        Args:
            user_id: The user ID.
            company_id: The company ID.
            year: The year.
            day_type: The day type.
        """
        # Get or create balance
        balance = self.db.query(LeaveBalance).filter(
            LeaveBalance.user_id == user_id,
            LeaveBalance.company_id == company_id,
            LeaveBalance.year == year,
        ).first()

        if not balance:
            # Get entitled days from company settings
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

        # Recalculate from records
        self._recalculate_balance(balance)

    def _recalculate_balance(self, balance: LeaveBalance) -> None:
        """Recalculate a leave balance from records.

        Args:
            balance: The leave balance to update.
        """
        year_start = date(balance.year, 1, 1)
        year_end = date(balance.year, 12, 31)

        # Count vacation days
        vacation_count = self.db.query(func.count(TimeRecord.id)).filter(
            TimeRecord.user_id == balance.user_id,
            TimeRecord.date >= year_start,
            TimeRecord.date <= year_end,
            TimeRecord.day_type == DayType.VACATION.value,
        ).scalar() or 0

        # Count sick days
        sick_count = self.db.query(func.count(TimeRecord.id)).filter(
            TimeRecord.user_id == balance.user_id,
            TimeRecord.date >= year_start,
            TimeRecord.date <= year_end,
            TimeRecord.day_type == DayType.SICK.value,
        ).scalar() or 0

        balance.vacation_taken = float(vacation_count)
        balance.sick_days_taken = sick_count
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
            # Get entitled days from company settings
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
        # Get all work records
        query = self.db.query(TimeRecord).filter(
            TimeRecord.user_id == user_id,
            TimeRecord.day_type.in_([
                DayType.WORK.value,
                DayType.DOCTOR_VISIT.value,
            ]),
        )
        if company_id:
            query = query.filter(TimeRecord.company_id == company_id)

        records = query.all()

        # Get company settings
        settings = None
        if company_id:
            settings = self.db.query(CompanyTimeSettings).filter(
                CompanyTimeSettings.company_id == company_id
            ).first()

        # Calculate earned comp time
        total_earned = 0.0
        for record in records:
            is_holiday = self.validator.is_public_holiday(record.date)
            earned = calculate_comp_time_earned(record, settings, is_holiday)
            total_earned += earned

        # Subtract comp time taken
        comp_days = self.db.query(func.count(TimeRecord.id)).filter(
            TimeRecord.user_id == user_id,
            TimeRecord.day_type == DayType.COMP_TIME.value,
        ).scalar() or 0

        # Assume 8 hours per comp time day
        daily_hours = settings.daily_overtime_threshold if settings else 8.0
        total_taken = float(comp_days) * daily_hours

        return total_earned - total_taken


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
