# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Time Tracking plugin compliance validators."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime

import holidays

from .models import DayType, TimeRecord
from .schemas import ComplianceWarning


@dataclass
class ComplianceResult:
    """Result of compliance validation."""

    is_valid: bool
    warnings: list[ComplianceWarning]


class ComplianceValidator(ABC):
    """Base class for country-specific labor law validation."""

    @abstractmethod
    def validate_daily_hours(
        self, record: TimeRecord
    ) -> list[ComplianceWarning]:
        """Check daily hour limits."""
        ...

    @abstractmethod
    def validate_rest_period(
        self,
        current: TimeRecord,
        previous: TimeRecord | None,
    ) -> list[ComplianceWarning]:
        """Check rest between shifts."""
        ...

    @abstractmethod
    def validate_weekly_hours(
        self,
        records: list[TimeRecord],
    ) -> list[ComplianceWarning]:
        """Check weekly limits."""
        ...

    @abstractmethod
    def get_public_holidays(
        self,
        year: int,
        region: str | None = None,
    ) -> dict[date, str]:
        """Return public holidays."""
        ...


class AustrianComplianceValidator(ComplianceValidator):
    """Austrian labor law (Arbeitszeitgesetz) validator.

    Key rules:
    - Maximum 10 hours per day
    - Maximum 50 hours per week (with exceptions)
    - Minimum 11 hours rest between shifts
    - Mandatory 30-minute break after 6 hours
    """

    # Austrian legal limits
    DAILY_NORMAL_HOURS = 8.0
    DAILY_MAX_HOURS = 10.0
    WEEKLY_NORMAL_HOURS = 40.0
    WEEKLY_MAX_HOURS = 50.0
    MIN_REST_HOURS = 11.0
    BREAK_THRESHOLD_HOURS = 6.0
    BREAK_MINUTES_REQUIRED = 30

    def validate_daily_hours(
        self, record: TimeRecord
    ) -> list[ComplianceWarning]:
        """Check daily hour limits per Austrian law.

        Args:
            record: The time record to validate.

        Returns:
            List of compliance warnings.
        """
        warnings: list[ComplianceWarning] = []

        if record.net_hours is None:
            return warnings

        if record.net_hours > self.DAILY_MAX_HOURS:
            warnings.append(
                ComplianceWarning(
                    level="error",
                    code="EXCEEDS_DAILY_MAX",
                    message=(
                        f"Exceeds {self.DAILY_MAX_HOURS}h/day legal maximum "
                        f"({record.net_hours:.1f}h worked)"
                    ),
                    requires_explanation=True,
                    law_reference="Arbeitszeitgesetz §3",
                )
            )
        elif record.net_hours > self.DAILY_NORMAL_HOURS:
            warnings.append(
                ComplianceWarning(
                    level="info",
                    code="OVERTIME",
                    message=(
                        f"Overtime: exceeds {self.DAILY_NORMAL_HOURS}h/day "
                        f"normal hours ({record.net_hours:.1f}h worked)"
                    ),
                    requires_explanation=False,
                    law_reference="Arbeitszeitgesetz §3",
                )
            )

        return warnings

    def validate_rest_period(
        self,
        current: TimeRecord,
        previous: TimeRecord | None,
    ) -> list[ComplianceWarning]:
        """Check 11-hour rest requirement.

        Args:
            current: The current time record.
            previous: The previous time record (if any).

        Returns:
            List of compliance warnings.
        """
        warnings: list[ComplianceWarning] = []

        if previous is None:
            return warnings

        if previous.check_out is None or current.check_in is None:
            return warnings

        # Calculate rest hours between shifts
        rest_hours = self._calculate_rest_hours(previous, current)

        if rest_hours < self.MIN_REST_HOURS:
            warnings.append(
                ComplianceWarning(
                    level="warning",
                    code="INSUFFICIENT_REST",
                    message=(
                        f"Only {rest_hours:.1f}h rest since last shift "
                        f"({self.MIN_REST_HOURS}h required by law)"
                    ),
                    requires_explanation=True,
                    law_reference="Arbeitszeitgesetz §12",
                )
            )

        return warnings

    def validate_weekly_hours(
        self,
        records: list[TimeRecord],
    ) -> list[ComplianceWarning]:
        """Check weekly hour limits.

        Args:
            records: List of time records for the week.

        Returns:
            List of compliance warnings.
        """
        warnings: list[ComplianceWarning] = []

        total_hours = sum(
            r.net_hours or 0.0
            for r in records
            if r.day_type in [DayType.WORK.value, DayType.DOCTOR_VISIT.value]
        )

        if total_hours > self.WEEKLY_MAX_HOURS:
            warnings.append(
                ComplianceWarning(
                    level="error",
                    code="EXCEEDS_WEEKLY_MAX",
                    message=(
                        f"Exceeds {self.WEEKLY_MAX_HOURS}h/week legal maximum "
                        f"({total_hours:.1f}h worked)"
                    ),
                    requires_explanation=True,
                    law_reference="Arbeitszeitgesetz §9",
                )
            )
        elif total_hours > self.WEEKLY_NORMAL_HOURS:
            warnings.append(
                ComplianceWarning(
                    level="info",
                    code="WEEKLY_OVERTIME",
                    message=(
                        f"Weekly overtime: exceeds {self.WEEKLY_NORMAL_HOURS}h/week "
                        f"normal hours ({total_hours:.1f}h worked)"
                    ),
                    requires_explanation=False,
                    law_reference="Arbeitszeitgesetz §9",
                )
            )

        return warnings

    def get_public_holidays(
        self,
        year: int,
        region: str | None = None,
    ) -> dict[date, str]:
        """Get Austrian public holidays for a year.

        Args:
            year: The year to get holidays for.
            region: Optional state/region code (e.g., "W" for Vienna).

        Returns:
            Dictionary mapping dates to holiday names.
        """
        at_holidays = holidays.Austria(years=year, subdiv=region)
        return dict(at_holidays.items())

    def is_public_holiday(
        self,
        check_date: date,
        region: str | None = None,
    ) -> bool:
        """Check if a date is a public holiday.

        Args:
            check_date: The date to check.
            region: Optional state/region code.

        Returns:
            True if the date is a public holiday.
        """
        at_holidays = holidays.Austria(years=check_date.year, subdiv=region)
        return check_date in at_holidays

    def get_holiday_name(
        self,
        check_date: date,
        region: str | None = None,
    ) -> str | None:
        """Get the name of a holiday on a date.

        Args:
            check_date: The date to check.
            region: Optional state/region code.

        Returns:
            The holiday name, or None if not a holiday.
        """
        at_holidays = holidays.Austria(years=check_date.year, subdiv=region)
        return at_holidays.get(check_date)

    def _calculate_rest_hours(
        self,
        previous: TimeRecord,
        current: TimeRecord,
    ) -> float:
        """Calculate rest hours between two shifts.

        Args:
            previous: The previous time record.
            current: The current time record.

        Returns:
            Number of rest hours.
        """
        if previous.check_out is None or current.check_in is None:
            return float("inf")

        # Combine date and time for accurate calculation
        prev_end = datetime.combine(previous.date, previous.check_out)
        curr_start = datetime.combine(current.date, current.check_in)

        # Handle timezone differences if needed
        # For now, assume same timezone for simplicity
        rest_delta = curr_start - prev_end
        return rest_delta.total_seconds() / 3600


def get_validator(country_code: str = "AT") -> ComplianceValidator:
    """Get the appropriate compliance validator for a country.

    Args:
        country_code: ISO 2-letter country code.

    Returns:
        The appropriate compliance validator.

    Raises:
        ValueError: If no validator exists for the country.
    """
    validators = {
        "AT": AustrianComplianceValidator,
    }

    validator_class = validators.get(country_code)
    if validator_class is None:
        raise ValueError(f"No compliance validator for country: {country_code}")

    return validator_class()
