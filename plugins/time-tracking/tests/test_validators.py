# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for compliance validators.

These tests verify the Austrian compliance validation logic.
"""

from dataclasses import dataclass
from datetime import date, datetime, time
from unittest.mock import MagicMock

import holidays
import pytest

# --- Simplified implementations for testing ---


@dataclass
class ComplianceWarning:
    """Schema for compliance warnings."""

    level: str
    code: str
    message: str
    requires_explanation: bool = False
    law_reference: str | None = None


class AustrianComplianceValidator:
    """Austrian labor law (Arbeitszeitgesetz) validator."""

    DAILY_NORMAL_HOURS = 8.0
    DAILY_MAX_HOURS = 10.0
    WEEKLY_NORMAL_HOURS = 40.0
    WEEKLY_MAX_HOURS = 50.0
    MIN_REST_HOURS = 11.0

    def validate_daily_hours(self, record: MagicMock) -> list[ComplianceWarning]:
        """Check daily hour limits per Austrian law."""
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
        current: MagicMock,
        previous: MagicMock | None,
    ) -> list[ComplianceWarning]:
        """Check 11-hour rest requirement."""
        warnings: list[ComplianceWarning] = []

        if previous is None:
            return warnings

        if previous.check_out is None or current.check_in is None:
            return warnings

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
        records: list,
    ) -> list[ComplianceWarning]:
        """Check weekly hour limits."""
        warnings: list[ComplianceWarning] = []

        total_hours = sum(
            r.net_hours or 0.0
            for r in records
            if r.day_type in ["work", "doctor_visit"]
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
        """Get Austrian public holidays for a year."""
        at_holidays = holidays.Austria(years=year, subdiv=region)
        return dict(at_holidays.items())

    def is_public_holiday(
        self,
        check_date: date,
        region: str | None = None,
    ) -> bool:
        """Check if a date is a public holiday."""
        at_holidays = holidays.Austria(years=check_date.year, subdiv=region)
        return check_date in at_holidays

    def get_holiday_name(
        self,
        check_date: date,
        region: str | None = None,
    ) -> str | None:
        """Get the name of a holiday on a date."""
        at_holidays = holidays.Austria(years=check_date.year, subdiv=region)
        return at_holidays.get(check_date)

    def _calculate_rest_hours(self, previous: MagicMock, current: MagicMock) -> float:
        """Calculate rest hours between two shifts."""
        if previous.check_out is None or current.check_in is None:
            return float("inf")

        prev_end = datetime.combine(previous.date, previous.check_out)
        curr_start = datetime.combine(current.date, current.check_in)

        rest_delta = curr_start - prev_end
        return rest_delta.total_seconds() / 3600


def get_validator(country_code: str = "AT") -> AustrianComplianceValidator:
    """Get the appropriate compliance validator for a country."""
    validators = {
        "AT": AustrianComplianceValidator,
    }

    validator_class = validators.get(country_code)
    if validator_class is None:
        raise ValueError(f"No compliance validator for country: {country_code}")

    return validator_class()


# --- Tests ---


class TestAustrianComplianceValidator:
    """Tests for AustrianComplianceValidator."""

    @pytest.fixture
    def validator(self) -> AustrianComplianceValidator:
        """Create a validator instance."""
        return AustrianComplianceValidator()

    def test_validate_daily_hours_within_limit(
        self, validator: AustrianComplianceValidator
    ) -> None:
        """No warnings for hours within 8h limit."""
        record = MagicMock()
        record.net_hours = 8.0

        warnings = validator.validate_daily_hours(record)
        assert len(warnings) == 0

    def test_validate_daily_hours_overtime(
        self, validator: AustrianComplianceValidator
    ) -> None:
        """Info warning for hours between 8h and 10h."""
        record = MagicMock()
        record.net_hours = 9.5

        warnings = validator.validate_daily_hours(record)
        assert len(warnings) == 1
        assert warnings[0].level == "info"
        assert warnings[0].code == "OVERTIME"

    def test_validate_daily_hours_exceeds_max(
        self, validator: AustrianComplianceValidator
    ) -> None:
        """Error warning for hours over 10h."""
        record = MagicMock()
        record.net_hours = 11.0

        warnings = validator.validate_daily_hours(record)
        assert len(warnings) == 1
        assert warnings[0].level == "error"
        assert warnings[0].code == "EXCEEDS_DAILY_MAX"
        assert warnings[0].requires_explanation is True

    def test_validate_daily_hours_none(
        self, validator: AustrianComplianceValidator
    ) -> None:
        """No warnings when net_hours is None."""
        record = MagicMock()
        record.net_hours = None

        warnings = validator.validate_daily_hours(record)
        assert len(warnings) == 0

    def test_validate_rest_period_sufficient(
        self, validator: AustrianComplianceValidator
    ) -> None:
        """No warning when rest period is >= 11 hours."""
        previous = MagicMock()
        previous.date = date(2025, 1, 1)
        previous.check_out = time(17, 0)

        current = MagicMock()
        current.date = date(2025, 1, 2)
        current.check_in = time(8, 0)  # 15 hours rest

        warnings = validator.validate_rest_period(current, previous)
        assert len(warnings) == 0

    def test_validate_rest_period_insufficient(
        self, validator: AustrianComplianceValidator
    ) -> None:
        """Warning when rest period is < 11 hours."""
        previous = MagicMock()
        previous.date = date(2025, 1, 1)
        previous.check_out = time(22, 0)  # Late check-out

        current = MagicMock()
        current.date = date(2025, 1, 2)
        current.check_in = time(6, 0)  # Only 8 hours rest

        warnings = validator.validate_rest_period(current, previous)
        assert len(warnings) == 1
        assert warnings[0].level == "warning"
        assert warnings[0].code == "INSUFFICIENT_REST"
        assert warnings[0].requires_explanation is True

    def test_validate_rest_period_no_previous(
        self, validator: AustrianComplianceValidator
    ) -> None:
        """No warning when there's no previous record."""
        current = MagicMock()
        current.check_in = time(8, 0)

        warnings = validator.validate_rest_period(current, None)
        assert len(warnings) == 0

    def test_validate_rest_period_missing_times(
        self, validator: AustrianComplianceValidator
    ) -> None:
        """No warning when times are missing."""
        previous = MagicMock()
        previous.date = date(2025, 1, 1)
        previous.check_out = None  # No check-out

        current = MagicMock()
        current.date = date(2025, 1, 2)
        current.check_in = time(8, 0)

        warnings = validator.validate_rest_period(current, previous)
        assert len(warnings) == 0

    def test_validate_weekly_hours_within_limit(
        self, validator: AustrianComplianceValidator
    ) -> None:
        """No warnings for weekly hours within 40h limit."""
        records = []
        for _i in range(5):
            record = MagicMock()
            record.day_type = "work"
            record.net_hours = 8.0
            records.append(record)

        warnings = validator.validate_weekly_hours(records)
        assert len(warnings) == 0

    def test_validate_weekly_hours_overtime(
        self, validator: AustrianComplianceValidator
    ) -> None:
        """Info warning for weekly hours between 40h and 50h."""
        records = []
        for _i in range(5):
            record = MagicMock()
            record.day_type = "work"
            record.net_hours = 9.0  # 45h total
            records.append(record)

        warnings = validator.validate_weekly_hours(records)
        assert len(warnings) == 1
        assert warnings[0].level == "info"
        assert warnings[0].code == "WEEKLY_OVERTIME"

    def test_validate_weekly_hours_exceeds_max(
        self, validator: AustrianComplianceValidator
    ) -> None:
        """Error warning for weekly hours over 50h."""
        records = []
        for _i in range(5):
            record = MagicMock()
            record.day_type = "work"
            record.net_hours = 11.0  # 55h total
            records.append(record)

        warnings = validator.validate_weekly_hours(records)
        assert len(warnings) == 1
        assert warnings[0].level == "error"
        assert warnings[0].code == "EXCEEDS_WEEKLY_MAX"

    def test_get_public_holidays_austria_2025(
        self, validator: AustrianComplianceValidator
    ) -> None:
        """Get Austrian public holidays for 2025."""
        holidays_dict = validator.get_public_holidays(2025)

        # Check some known Austrian holidays
        assert date(2025, 1, 1) in holidays_dict  # Neujahr
        assert date(2025, 1, 6) in holidays_dict  # Heilige Drei Könige
        assert date(2025, 5, 1) in holidays_dict  # Staatsfeiertag
        assert date(2025, 12, 25) in holidays_dict  # Weihnachten

    def test_is_public_holiday_christmas(
        self, validator: AustrianComplianceValidator
    ) -> None:
        """Christmas is a public holiday."""
        assert validator.is_public_holiday(date(2025, 12, 25)) is True

    def test_is_public_holiday_regular_day(
        self, validator: AustrianComplianceValidator
    ) -> None:
        """Regular day is not a holiday."""
        assert validator.is_public_holiday(date(2025, 3, 15)) is False

    def test_get_holiday_name(self, validator: AustrianComplianceValidator) -> None:
        """Get the name of a holiday."""
        name = validator.get_holiday_name(date(2025, 12, 25))
        assert name is not None
        # Austrian holidays library uses "Christtag" for December 25th
        assert "Christ" in name or "Weihnacht" in name


class TestGetValidator:
    """Tests for get_validator factory function."""

    def test_get_austrian_validator(self) -> None:
        """Get Austrian validator for AT code."""
        validator = get_validator("AT")
        assert isinstance(validator, AustrianComplianceValidator)

    def test_get_unknown_country_raises(self) -> None:
        """Unknown country code raises ValueError."""
        with pytest.raises(ValueError, match="No compliance validator"):
            get_validator("XX")
