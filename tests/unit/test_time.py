# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for the time helpers."""

from datetime import UTC, datetime

from src.utils.time import utc_now


def test_utc_now_is_naive() -> None:
    """The helper returns a naive datetime."""
    assert utc_now().tzinfo is None


def test_utc_now_matches_utc_clock() -> None:
    """The helper is within two seconds of the aware UTC clock."""
    expected = datetime.now(UTC).replace(tzinfo=None)

    assert abs((utc_now() - expected).total_seconds()) < 2
