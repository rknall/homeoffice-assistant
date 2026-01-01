# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for leave balance calculations.

These tests verify vacation balance, comp time accrual, and year-end rollover logic.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum

# --- Simplified implementations for testing ---


class DayType(str, Enum):
    """Day type for time records."""

    WORK = "work"
    VACATION = "vacation"
    SICK = "sick"
    DOCTOR_VISIT = "doctor_visit"
    PUBLIC_HOLIDAY = "public_holiday"
    COMP_TIME = "comp_time"
    UNPAID_LEAVE = "unpaid_leave"
    WEEKEND = "weekend"


@dataclass
class LeaveBalance:
    """Represents a leave balance for tracking."""

    user_id: str
    company_id: str
    year: int
    leave_type: str  # "vacation" or "comp_time"
    entitled_days: Decimal
    carried_over: Decimal
    used_days: Decimal
    pending_days: Decimal

    @property
    def available_days(self) -> Decimal:
        """Calculate available days."""
        return (
            self.entitled_days + self.carried_over - self.used_days - self.pending_days
        )


@dataclass
class TimeRecord:
    """Simplified time record for testing."""

    day_type: DayType
    net_hours: float | None
    date: date


def calculate_comp_time_earned(
    net_hours: float,
    standard_hours: float,
    is_sunday: bool = False,
    is_holiday: bool = False,
) -> float:
    """Calculate compensatory time earned for overtime work.

    Returns the comp time hours earned:
    - Sunday/Holiday work: 2x multiplier (per Austrian law)
    - Regular overtime: 1x the overtime hours
    """
    if net_hours <= standard_hours:
        return 0.0

    overtime_hours = net_hours - standard_hours

    if is_sunday or is_holiday:
        # 2x multiplier for Sunday/Holiday work
        return overtime_hours * 2.0

    return overtime_hours


def calculate_vacation_used(records: list[TimeRecord]) -> Decimal:
    """Calculate vacation days used from time records."""
    vacation_days = Decimal("0")
    for record in records:
        if record.day_type == DayType.VACATION:
            vacation_days += Decimal("1")
    return vacation_days


def calculate_comp_time_used(records: list[TimeRecord]) -> Decimal:
    """Calculate comp time days used from time records."""
    comp_time_days = Decimal("0")
    for record in records:
        if record.day_type == DayType.COMP_TIME:
            comp_time_days += Decimal("1")
    return comp_time_days


def calculate_year_end_carryover(
    balance: LeaveBalance,
    max_carryover_days: Decimal = Decimal("5"),
) -> Decimal:
    """Calculate how many days can be carried over to next year.

    Austrian law allows carrying over unused vacation days,
    typically up to a maximum limit set by the company.
    """
    remaining = balance.available_days
    if remaining <= Decimal("0"):
        return Decimal("0")
    return min(remaining, max_carryover_days)


def create_new_year_balance(
    previous_balance: LeaveBalance,
    new_year: int,
    entitled_days: Decimal,
    max_carryover: Decimal = Decimal("5"),
) -> LeaveBalance:
    """Create a new year's balance with carryover from previous year."""
    carryover = calculate_year_end_carryover(previous_balance, max_carryover)
    return LeaveBalance(
        user_id=previous_balance.user_id,
        company_id=previous_balance.company_id,
        year=new_year,
        leave_type=previous_balance.leave_type,
        entitled_days=entitled_days,
        carried_over=carryover,
        used_days=Decimal("0"),
        pending_days=Decimal("0"),
    )


# --- Tests ---


class TestLeaveBalance:
    """Tests for LeaveBalance calculations."""

    def test_available_days_calculation(self):
        """Available days = entitled + carried_over - used - pending."""
        balance = LeaveBalance(
            user_id="user1",
            company_id="company1",
            year=2025,
            leave_type="vacation",
            entitled_days=Decimal("25"),
            carried_over=Decimal("3"),
            used_days=Decimal("5"),
            pending_days=Decimal("2"),
        )
        assert balance.available_days == Decimal("21")

    def test_available_days_with_no_carryover(self):
        """Available days when no days carried over."""
        balance = LeaveBalance(
            user_id="user1",
            company_id="company1",
            year=2025,
            leave_type="vacation",
            entitled_days=Decimal("25"),
            carried_over=Decimal("0"),
            used_days=Decimal("10"),
            pending_days=Decimal("0"),
        )
        assert balance.available_days == Decimal("15")

    def test_available_days_can_be_zero(self):
        """Available days can be zero when all used."""
        balance = LeaveBalance(
            user_id="user1",
            company_id="company1",
            year=2025,
            leave_type="vacation",
            entitled_days=Decimal("25"),
            carried_over=Decimal("0"),
            used_days=Decimal("25"),
            pending_days=Decimal("0"),
        )
        assert balance.available_days == Decimal("0")

    def test_available_days_can_be_negative(self):
        """Available days can go negative (overdraft)."""
        balance = LeaveBalance(
            user_id="user1",
            company_id="company1",
            year=2025,
            leave_type="vacation",
            entitled_days=Decimal("25"),
            carried_over=Decimal("0"),
            used_days=Decimal("27"),
            pending_days=Decimal("0"),
        )
        assert balance.available_days == Decimal("-2")


class TestCompTimeEarned:
    """Tests for compensatory time accrual."""

    def test_no_comp_time_under_standard_hours(self):
        """No comp time earned when working standard hours or less."""
        assert calculate_comp_time_earned(8.0, 8.0) == 0.0
        assert calculate_comp_time_earned(7.0, 8.0) == 0.0
        assert calculate_comp_time_earned(4.0, 8.0) == 0.0

    def test_comp_time_for_regular_overtime(self):
        """Comp time earned for regular weekday overtime."""
        assert calculate_comp_time_earned(9.0, 8.0) == 1.0
        assert calculate_comp_time_earned(10.0, 8.0) == 2.0
        assert calculate_comp_time_earned(8.5, 8.0) == 0.5

    def test_comp_time_2x_for_sunday(self):
        """Sunday work earns 2x comp time."""
        assert calculate_comp_time_earned(9.0, 8.0, is_sunday=True) == 2.0
        assert calculate_comp_time_earned(10.0, 8.0, is_sunday=True) == 4.0
        assert calculate_comp_time_earned(8.5, 8.0, is_sunday=True) == 1.0

    def test_comp_time_2x_for_holiday(self):
        """Holiday work earns 2x comp time."""
        assert calculate_comp_time_earned(9.0, 8.0, is_holiday=True) == 2.0
        assert calculate_comp_time_earned(10.0, 8.0, is_holiday=True) == 4.0

    def test_comp_time_sunday_and_holiday(self):
        """Sunday that is also a holiday still earns 2x (not 4x)."""
        # When is_sunday=True AND is_holiday=True, the multiplier is still 2x
        assert (
            calculate_comp_time_earned(9.0, 8.0, is_sunday=True, is_holiday=True) == 2.0
        )

    def test_no_comp_time_on_sunday_without_overtime(self):
        """No extra comp time for working standard hours on Sunday."""
        assert calculate_comp_time_earned(8.0, 8.0, is_sunday=True) == 0.0


class TestVacationUsed:
    """Tests for vacation day calculations."""

    def test_count_vacation_days(self):
        """Count vacation days from records."""
        records = [
            TimeRecord(
                day_type=DayType.VACATION, net_hours=None, date=date(2025, 1, 6)
            ),
            TimeRecord(
                day_type=DayType.VACATION, net_hours=None, date=date(2025, 1, 7)
            ),
            TimeRecord(day_type=DayType.WORK, net_hours=8.0, date=date(2025, 1, 8)),
        ]
        assert calculate_vacation_used(records) == Decimal("2")

    def test_no_vacation_days(self):
        """Zero vacation days when none used."""
        records = [
            TimeRecord(day_type=DayType.WORK, net_hours=8.0, date=date(2025, 1, 6)),
            TimeRecord(day_type=DayType.WORK, net_hours=8.0, date=date(2025, 1, 7)),
        ]
        assert calculate_vacation_used(records) == Decimal("0")

    def test_sick_days_not_counted_as_vacation(self):
        """Sick days should not count as vacation."""
        records = [
            TimeRecord(day_type=DayType.SICK, net_hours=None, date=date(2025, 1, 6)),
            TimeRecord(
                day_type=DayType.VACATION, net_hours=None, date=date(2025, 1, 7)
            ),
        ]
        assert calculate_vacation_used(records) == Decimal("1")


class TestCompTimeUsed:
    """Tests for comp time usage calculations."""

    def test_count_comp_time_days(self):
        """Count comp time days from records."""
        records = [
            TimeRecord(
                day_type=DayType.COMP_TIME, net_hours=None, date=date(2025, 1, 6)
            ),
            TimeRecord(day_type=DayType.WORK, net_hours=8.0, date=date(2025, 1, 7)),
            TimeRecord(
                day_type=DayType.COMP_TIME, net_hours=None, date=date(2025, 1, 8)
            ),
        ]
        assert calculate_comp_time_used(records) == Decimal("2")

    def test_no_comp_time_used(self):
        """Zero comp time when none used."""
        records = [
            TimeRecord(day_type=DayType.WORK, net_hours=8.0, date=date(2025, 1, 6)),
        ]
        assert calculate_comp_time_used(records) == Decimal("0")


class TestYearEndCarryover:
    """Tests for year-end carryover calculations."""

    def test_carryover_within_limit(self):
        """Days under limit are fully carried over."""
        balance = LeaveBalance(
            user_id="user1",
            company_id="company1",
            year=2025,
            leave_type="vacation",
            entitled_days=Decimal("25"),
            carried_over=Decimal("0"),
            used_days=Decimal("22"),
            pending_days=Decimal("0"),
        )
        # 3 days available, limit is 5
        carryover = calculate_year_end_carryover(
            balance, max_carryover_days=Decimal("5")
        )
        assert carryover == Decimal("3")

    def test_carryover_at_limit(self):
        """Days at limit are fully carried over."""
        balance = LeaveBalance(
            user_id="user1",
            company_id="company1",
            year=2025,
            leave_type="vacation",
            entitled_days=Decimal("25"),
            carried_over=Decimal("0"),
            used_days=Decimal("20"),
            pending_days=Decimal("0"),
        )
        # 5 days available, limit is 5
        carryover = calculate_year_end_carryover(
            balance, max_carryover_days=Decimal("5")
        )
        assert carryover == Decimal("5")

    def test_carryover_over_limit_is_capped(self):
        """Days over limit are capped at max carryover."""
        balance = LeaveBalance(
            user_id="user1",
            company_id="company1",
            year=2025,
            leave_type="vacation",
            entitled_days=Decimal("25"),
            carried_over=Decimal("0"),
            used_days=Decimal("15"),
            pending_days=Decimal("0"),
        )
        # 10 days available, limit is 5
        carryover = calculate_year_end_carryover(
            balance, max_carryover_days=Decimal("5")
        )
        assert carryover == Decimal("5")

    def test_no_carryover_when_nothing_remaining(self):
        """No carryover when all days used."""
        balance = LeaveBalance(
            user_id="user1",
            company_id="company1",
            year=2025,
            leave_type="vacation",
            entitled_days=Decimal("25"),
            carried_over=Decimal("0"),
            used_days=Decimal("25"),
            pending_days=Decimal("0"),
        )
        carryover = calculate_year_end_carryover(
            balance, max_carryover_days=Decimal("5")
        )
        assert carryover == Decimal("0")

    def test_no_carryover_when_negative_balance(self):
        """No carryover when balance is negative."""
        balance = LeaveBalance(
            user_id="user1",
            company_id="company1",
            year=2025,
            leave_type="vacation",
            entitled_days=Decimal("25"),
            carried_over=Decimal("0"),
            used_days=Decimal("27"),
            pending_days=Decimal("0"),
        )
        carryover = calculate_year_end_carryover(
            balance, max_carryover_days=Decimal("5")
        )
        assert carryover == Decimal("0")


class TestNewYearBalance:
    """Tests for creating new year balances with carryover."""

    def test_create_new_year_with_carryover(self):
        """New year balance includes carryover from previous year."""
        previous = LeaveBalance(
            user_id="user1",
            company_id="company1",
            year=2025,
            leave_type="vacation",
            entitled_days=Decimal("25"),
            carried_over=Decimal("0"),
            used_days=Decimal("22"),
            pending_days=Decimal("0"),
        )
        # 3 days remaining, should carry over
        new_balance = create_new_year_balance(
            previous,
            new_year=2026,
            entitled_days=Decimal("25"),
            max_carryover=Decimal("5"),
        )

        assert new_balance.year == 2026
        assert new_balance.entitled_days == Decimal("25")
        assert new_balance.carried_over == Decimal("3")
        assert new_balance.used_days == Decimal("0")
        assert new_balance.pending_days == Decimal("0")
        assert new_balance.available_days == Decimal("28")

    def test_create_new_year_carryover_capped(self):
        """Carryover is capped at maximum when creating new year."""
        previous = LeaveBalance(
            user_id="user1",
            company_id="company1",
            year=2025,
            leave_type="vacation",
            entitled_days=Decimal("25"),
            carried_over=Decimal("0"),
            used_days=Decimal("10"),
            pending_days=Decimal("0"),
        )
        # 15 days remaining, should cap at 5
        new_balance = create_new_year_balance(
            previous,
            new_year=2026,
            entitled_days=Decimal("25"),
            max_carryover=Decimal("5"),
        )

        assert new_balance.carried_over == Decimal("5")
        assert new_balance.available_days == Decimal("30")

    def test_create_new_year_no_carryover_when_overdrawn(self):
        """No carryover when previous year was overdrawn."""
        previous = LeaveBalance(
            user_id="user1",
            company_id="company1",
            year=2025,
            leave_type="vacation",
            entitled_days=Decimal("25"),
            carried_over=Decimal("0"),
            used_days=Decimal("30"),
            pending_days=Decimal("0"),
        )
        # Overdrawn by 5 days
        new_balance = create_new_year_balance(
            previous,
            new_year=2026,
            entitled_days=Decimal("25"),
            max_carryover=Decimal("5"),
        )

        assert new_balance.carried_over == Decimal("0")
        assert new_balance.available_days == Decimal("25")
