# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for time calculation functions.

These tests verify the time rounding and calculation logic.
"""

from datetime import time

import pytest


# --- Simplified implementations for testing ---


def round_time_employer_favor(t: time, is_check_in: bool) -> time:
    """Round time to 5 minutes in employer's favor.

    - Check-in: rounds UP (if 08:03 → 08:05)
    - Check-out: rounds DOWN (if 17:43 → 17:40)
    """
    minute = t.minute
    remainder = minute % 5

    if remainder == 0:
        return t

    if is_check_in:
        # Round up
        new_minute = minute + (5 - remainder)
        new_hour = t.hour
        if new_minute >= 60:
            new_minute -= 60
            new_hour = (new_hour + 1) % 24
        return time(new_hour, new_minute, 0)
    else:
        # Round down
        new_minute = minute - remainder
        return time(t.hour, new_minute, 0)


def calculate_break_minutes(gross_hours: float) -> int:
    """Calculate required break based on Austrian law.

    - Over 6 hours: 30 minutes break required
    - 6 hours or less: no break required
    """
    if gross_hours > 6.0:
        return 30
    return 0


def calculate_gross_hours(check_in: time, check_out: time) -> float:
    """Calculate gross hours between check-in and check-out."""
    in_minutes = check_in.hour * 60 + check_in.minute
    out_minutes = check_out.hour * 60 + check_out.minute

    # Handle overnight shifts
    if out_minutes < in_minutes:
        out_minutes += 24 * 60

    diff_minutes = out_minutes - in_minutes
    return diff_minutes / 60.0


def calculate_net_hours(
    check_in: time,
    check_out: time,
    break_override: int | None = None,
) -> tuple[float, int, float]:
    """Calculate net working hours.

    Returns (net_hours, break_minutes, gross_hours).
    """
    gross = calculate_gross_hours(check_in, check_out)

    if break_override is not None:
        break_mins = break_override
    else:
        break_mins = calculate_break_minutes(gross)

    net = gross - (break_mins / 60.0)
    return (net, break_mins, gross)


# --- Tests ---


class TestRoundTimeEmployerFavor:
    """Tests for round_time_employer_favor function."""

    def test_check_in_rounds_up_from_03(self):
        """Check-in at 08:03 rounds up to 08:05."""
        result = round_time_employer_favor(time(8, 3), is_check_in=True)
        assert result == time(8, 5)

    def test_check_in_rounds_up_from_07(self):
        """Check-in at 08:07 rounds up to 08:10."""
        result = round_time_employer_favor(time(8, 7), is_check_in=True)
        assert result == time(8, 10)

    def test_check_in_exact_5_unchanged(self):
        """Check-in at 08:05 stays at 08:05."""
        result = round_time_employer_favor(time(8, 5), is_check_in=True)
        assert result == time(8, 5)

    def test_check_in_exact_0_unchanged(self):
        """Check-in at 08:00 stays at 08:00."""
        result = round_time_employer_favor(time(8, 0), is_check_in=True)
        assert result == time(8, 0)

    def test_check_out_rounds_down_from_43(self):
        """Check-out at 17:43 rounds down to 17:40."""
        result = round_time_employer_favor(time(17, 43), is_check_in=False)
        assert result == time(17, 40)

    def test_check_out_rounds_down_from_47(self):
        """Check-out at 17:47 rounds down to 17:45."""
        result = round_time_employer_favor(time(17, 47), is_check_in=False)
        assert result == time(17, 45)

    def test_check_out_exact_5_unchanged(self):
        """Check-out at 17:45 stays at 17:45."""
        result = round_time_employer_favor(time(17, 45), is_check_in=False)
        assert result == time(17, 45)

    def test_check_out_exact_0_unchanged(self):
        """Check-out at 17:00 stays at 17:00."""
        result = round_time_employer_favor(time(17, 0), is_check_in=False)
        assert result == time(17, 0)

    def test_check_in_at_01(self):
        """Check-in at 08:01 rounds up to 08:05."""
        result = round_time_employer_favor(time(8, 1), is_check_in=True)
        assert result == time(8, 5)

    def test_check_out_at_59(self):
        """Check-out at 17:59 rounds down to 17:55."""
        result = round_time_employer_favor(time(17, 59), is_check_in=False)
        assert result == time(17, 55)


class TestCalculateBreakMinutes:
    """Tests for calculate_break_minutes function."""

    def test_over_6_hours_gets_30_min_break(self):
        """Working over 6 hours requires 30 minute break."""
        assert calculate_break_minutes(7.0) == 30
        assert calculate_break_minutes(8.0) == 30
        assert calculate_break_minutes(9.5) == 30

    def test_exactly_6_hours_no_break(self):
        """Working exactly 6 hours needs no break."""
        assert calculate_break_minutes(6.0) == 0

    def test_under_6_hours_no_break(self):
        """Working under 6 hours needs no break."""
        assert calculate_break_minutes(5.0) == 0
        assert calculate_break_minutes(4.5) == 0
        assert calculate_break_minutes(1.0) == 0

    def test_just_over_6_hours_gets_break(self):
        """Working just over 6 hours gets 30 min break."""
        assert calculate_break_minutes(6.01) == 30
        assert calculate_break_minutes(6.1) == 30


class TestCalculateGrossHours:
    """Tests for calculate_gross_hours function."""

    def test_standard_8_hour_day(self):
        """8:00 to 17:00 is 9 gross hours."""
        result = calculate_gross_hours(time(8, 0), time(17, 0))
        assert result == 9.0

    def test_8_30_to_17_30(self):
        """8:30 to 17:30 is 9 gross hours."""
        result = calculate_gross_hours(time(8, 30), time(17, 30))
        assert result == 9.0

    def test_short_day(self):
        """9:00 to 12:00 is 3 gross hours."""
        result = calculate_gross_hours(time(9, 0), time(12, 0))
        assert result == 3.0

    def test_with_minutes(self):
        """8:15 to 16:45 is 8.5 gross hours."""
        result = calculate_gross_hours(time(8, 15), time(16, 45))
        assert result == 8.5

    def test_overnight_shift(self):
        """22:00 to 06:00 (overnight) is 8 gross hours."""
        result = calculate_gross_hours(time(22, 0), time(6, 0))
        assert result == 8.0


class TestCalculateNetHours:
    """Tests for calculate_net_hours function."""

    def test_standard_day_with_auto_break(self):
        """8:00 to 17:00 = 9h gross, 30m auto break, 8.5h net."""
        net, break_mins, gross = calculate_net_hours(time(8, 0), time(17, 0))
        assert gross == 9.0
        assert break_mins == 30
        assert net == 8.5

    def test_short_day_no_break(self):
        """9:00 to 14:00 = 5h gross, no break, 5h net."""
        net, break_mins, gross = calculate_net_hours(time(9, 0), time(14, 0))
        assert gross == 5.0
        assert break_mins == 0
        assert net == 5.0

    def test_with_manual_break_override(self):
        """Manual break override of 45 minutes."""
        net, break_mins, gross = calculate_net_hours(
            time(8, 0), time(17, 0), break_override=45
        )
        assert gross == 9.0
        assert break_mins == 45
        assert net == 8.25

    def test_exactly_6_hours_no_auto_break(self):
        """Exactly 6 hours = no automatic break."""
        net, break_mins, gross = calculate_net_hours(time(8, 0), time(14, 0))
        assert gross == 6.0
        assert break_mins == 0
        assert net == 6.0

    def test_just_over_6_hours_gets_break(self):
        """Just over 6 hours = 30 min break."""
        net, break_mins, gross = calculate_net_hours(time(8, 0), time(14, 5))
        assert gross == pytest.approx(6.083, rel=0.01)
        assert break_mins == 30
        assert net == pytest.approx(5.583, rel=0.01)
