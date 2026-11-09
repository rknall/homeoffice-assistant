# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Time helpers."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current UTC time as a naive datetime.

    SQLite DateTime columns store and load naive values, so every value
    written to or compared with a column must be naive UTC.
    """
    return datetime.now(UTC).replace(tzinfo=None)
