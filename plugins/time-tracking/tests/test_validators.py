# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for compliance validators.

These tests verify the Austrian compliance validation logic.
"""

import importlib
from datetime import date, time
from unittest.mock import MagicMock

import pytest

from src.services.holiday_calendar_service import get_public_holidays

validators = importlib.import_module("plugins.time-tracking.backend.validators")
AustrianComplianceValidator = validators.AustrianComplianceValidator
get_validator = validators.get_validator


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
            record.entry_type = "work"
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
            record.entry_type = "work"
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
            record.entry_type = "work"
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


def test_plugin_validator_shares_core_holidays() -> None:
    """The plugin's Austrian validator sees the same holidays as the core service."""
    real = importlib.import_module("plugins.time-tracking.backend.validators")
    expected = get_public_holidays("AT", 2025)

    assert real.AustrianComplianceValidator().get_public_holidays(2025) == expected
    assert real.get_validator("AT").is_public_holiday(date(2025, 12, 25)) is True
