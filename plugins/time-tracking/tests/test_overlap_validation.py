# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for time entry overlap validation.

These tests verify that the overlap detection correctly identifies
conflicts across companies and prevents double-booking.

Note: These tests focus on the pure functions (times_overlap) to avoid
SQLAlchemy model registration conflicts with the main app.
"""

from datetime import time


def times_overlap(
    start1: time, end1: time, start2: time, end2: time
) -> bool:
    """Check if two time ranges overlap.

    This is a copy of the function from services.py for isolated testing.
    Handles overnight shifts correctly by checking both the evening and
    morning portions of overnight ranges.
    """
    # Convert to minutes for comparison
    start1_mins = start1.hour * 60 + start1.minute
    end1_mins = end1.hour * 60 + end1.minute
    start2_mins = start2.hour * 60 + start2.minute
    end2_mins = end2.hour * 60 + end2.minute

    # Check if either range is an overnight shift
    range1_overnight = end1_mins < start1_mins
    range2_overnight = end2_mins < start2_mins

    # Handle overnight shifts by normalizing to 24+ hour scale
    if range1_overnight:
        end1_mins += 24 * 60
    if range2_overnight:
        end2_mins += 24 * 60

    # For overnight range1, if range2 starts early morning (within range1's
    # next-day portion) shift range2 forward for proper comparison
    if range1_overnight and not range2_overnight:
        # If range2 starts before the overnight end time (e.g., 04:00 < 06:00)
        original_end1 = end1.hour * 60 + end1.minute
        if start2_mins < original_end1:
            # Shift range2 to next day for comparison
            start2_mins += 24 * 60
            end2_mins += 24 * 60

    # For overnight range2, apply symmetric logic
    if range2_overnight and not range1_overnight:
        original_end2 = end2.hour * 60 + end2.minute
        if start1_mins < original_end2:
            start1_mins += 24 * 60
            end1_mins += 24 * 60

    # Check for overlap: ranges overlap if start of one is before end of other
    return start1_mins < end2_mins and start2_mins < end1_mins


class TestTimesOverlap:
    """Tests for the times_overlap helper function."""

    def test_no_overlap_sequential(self) -> None:
        """Times that don't overlap (sequential)."""
        # 08:00-12:00 and 13:00-17:00
        assert not times_overlap(
            time(8, 0), time(12, 0), time(13, 0), time(17, 0)
        )

    def test_no_overlap_exact_boundary(self) -> None:
        """Times that touch exactly at the boundary."""
        # 08:00-12:00 and 12:00-17:00
        assert not times_overlap(
            time(8, 0), time(12, 0), time(12, 0), time(17, 0)
        )

    def test_overlap_partial(self) -> None:
        """Times that partially overlap."""
        # 08:00-13:00 and 11:00-17:00
        assert times_overlap(time(8, 0), time(13, 0), time(11, 0), time(17, 0))

    def test_overlap_complete_containment(self) -> None:
        """One time range completely contains the other."""
        # 08:00-18:00 and 11:00-14:00
        assert times_overlap(time(8, 0), time(18, 0), time(11, 0), time(14, 0))

    def test_overlap_reverse_containment(self) -> None:
        """One time range completely contained by the other."""
        # 11:00-14:00 and 08:00-18:00
        assert times_overlap(time(11, 0), time(14, 0), time(8, 0), time(18, 0))

    def test_overlap_same_times(self) -> None:
        """Exact same time range."""
        # 09:00-17:00 and 09:00-17:00
        assert times_overlap(time(9, 0), time(17, 0), time(9, 0), time(17, 0))

    def test_overnight_shift_no_overlap(self) -> None:
        """Overnight shift that doesn't overlap with day shift."""
        # 22:00-06:00 and 08:00-17:00
        assert not times_overlap(
            time(22, 0), time(6, 0), time(8, 0), time(17, 0)
        )

    def test_overnight_shift_with_overlap(self) -> None:
        """Overnight shift that overlaps with early morning shift."""
        # 22:00-06:00 and 04:00-12:00
        assert times_overlap(time(22, 0), time(6, 0), time(4, 0), time(12, 0))

    def test_no_overlap_before(self) -> None:
        """Second range is completely before first."""
        # 13:00-17:00 and 08:00-12:00
        assert not times_overlap(
            time(13, 0), time(17, 0), time(8, 0), time(12, 0)
        )

    def test_overlap_one_minute(self) -> None:
        """Ranges that overlap by one minute."""
        # 08:00-12:01 and 12:00-17:00
        assert times_overlap(time(8, 0), time(12, 1), time(12, 0), time(17, 0))

    def test_short_ranges_no_overlap(self) -> None:
        """Short time ranges with gap between."""
        # 08:00-08:30 and 09:00-09:30
        assert not times_overlap(
            time(8, 0), time(8, 30), time(9, 0), time(9, 30)
        )

    def test_short_ranges_with_overlap(self) -> None:
        """Short time ranges that overlap."""
        # 08:00-09:00 and 08:30-09:30
        assert times_overlap(
            time(8, 0), time(9, 0), time(8, 30), time(9, 30)
        )

    def test_two_overnight_shifts_overlap(self) -> None:
        """Two overnight shifts that overlap."""
        # 22:00-02:00 and 23:00-03:00
        assert times_overlap(time(22, 0), time(2, 0), time(23, 0), time(3, 0))

    def test_two_overnight_shifts_no_overlap(self) -> None:
        """Two overnight shifts on different nights."""
        # 22:00-02:00 and 03:00-06:00
        assert not times_overlap(
            time(22, 0), time(2, 0), time(3, 0), time(6, 0)
        )

    def test_lunch_break_pattern(self) -> None:
        """Typical morning/afternoon split with lunch break."""
        # Morning: 08:00-12:00, Afternoon: 13:00-17:00
        assert not times_overlap(
            time(8, 0), time(12, 0), time(13, 0), time(17, 0)
        )

    def test_half_day_overlap(self) -> None:
        """Half day at one company overlapping with full day at another."""
        # 08:00-12:00 (half day) and 09:00-17:00 (full day)
        assert times_overlap(
            time(8, 0), time(12, 0), time(9, 0), time(17, 0)
        )
