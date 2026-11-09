# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Time Tracking plugin business logic services."""

from .calc import (
    EffectiveLeaveDays,
    calculate_break_minutes,
    calculate_gross_minutes,
    company_name_map,
    count_effective_leave_days,
    entry_to_response,
    round_time_employer_favor,
    times_overlap,
)
from .config import (
    DEFAULT_BREAK_MINUTES,
    DEFAULT_COUNTRY,
    DEFAULT_WORK_HOURS,
    MANIFEST_PATH,
    TimeTrackingConfig,
    plugin_name,
    plugin_version,
)
from .entries import TimeEntryService
from .holidays import HolidayService
from .leave import LeaveBalanceService
from .reports import ReportService
from .settings import CompanySettingsService

__all__ = [
    "DEFAULT_BREAK_MINUTES",
    "DEFAULT_COUNTRY",
    "DEFAULT_WORK_HOURS",
    "MANIFEST_PATH",
    "CompanySettingsService",
    "EffectiveLeaveDays",
    "HolidayService",
    "LeaveBalanceService",
    "ReportService",
    "TimeEntryService",
    "TimeTrackingConfig",
    "calculate_break_minutes",
    "calculate_gross_minutes",
    "company_name_map",
    "count_effective_leave_days",
    "entry_to_response",
    "plugin_name",
    "plugin_version",
    "round_time_employer_favor",
    "times_overlap",
]
