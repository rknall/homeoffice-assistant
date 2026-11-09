# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Time Tracking plugin main class."""

import json
from typing import Any

from fastapi import APIRouter
from sqlalchemy.orm import DeclarativeBase

from src.plugins.base import BasePlugin

from .models import (
    CompanyTimeSettings,
    CustomHoliday,
    LeaveBalance,
    TimeEntry,
    TimesheetSubmission,
    UserTimePreferences,
)
from .routes import router as time_tracking_router
from .services import MANIFEST_PATH


class TimeTrackingPlugin(BasePlugin):
    """Time tracking plugin with Austrian labor law compliance.

    This plugin provides:
    - Daily time record tracking with check-in/check-out
    - Automatic break calculation and time rounding
    - Austrian labor law compliance validation
    - Vacation and comp time balance tracking
    - Monthly report generation and submission
    - Company-specific time settings
    """

    @classmethod
    def get_config_schema(cls) -> dict[str, Any]:
        """Return JSON Schema for plugin configuration.

        The manifest is the single source of the schema.

        Returns:
            Configuration schema dictionary.
        """
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        return manifest.get("config_schema", {})

    def get_router(self) -> APIRouter | None:
        """Return FastAPI router with plugin endpoints.

        Returns:
            The plugin's API router.
        """
        return time_tracking_router

    def get_models(self) -> list[type[DeclarativeBase]]:
        """Return SQLAlchemy models for this plugin.

        Returns:
            List of model classes.
        """
        return [
            TimeEntry,
            LeaveBalance,
            TimesheetSubmission,
            CompanyTimeSettings,
            CustomHoliday,
            UserTimePreferences,
        ]
