# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Time Tracking plugin main class."""

import logging
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter
from sqlalchemy.orm import DeclarativeBase

from src.plugins.base import BasePlugin, PluginConfig, PluginManifest
from src.plugins.events import AppEvent, EventPayload

from .models import (
    CompanyTimeSettings,
    CustomHoliday,
    LeaveBalance,
    TimeAllocation,
    TimeRecord,
    TimeRecordAudit,
    TimesheetSubmission,
    UserTimePreferences,
)
from .routes import router as time_tracking_router

logger = logging.getLogger(__name__)


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

    def __init__(
        self, manifest: PluginManifest, config: PluginConfig, plugin_path: str
    ) -> None:
        """Initialize the time tracking plugin.

        Args:
            manifest: Plugin manifest.
            config: Plugin configuration.
            plugin_path: Path to the plugin directory.
        """
        super().__init__(manifest, config, plugin_path)
        self._default_work_hours = config.settings.get("default_work_hours", 8.0)
        self._default_break_minutes = config.settings.get("default_break_minutes", 30)
        self._enable_allocation = config.settings.get("enable_project_allocation", True)
        self._default_country = config.settings.get("default_country", "AT")

    @classmethod
    def get_config_schema(cls) -> dict[str, Any]:
        """Return JSON Schema for plugin configuration.

        Returns:
            Configuration schema dictionary.
        """
        return {
            "type": "object",
            "properties": {
                "default_work_hours": {
                    "type": "number",
                    "title": "Default Work Hours",
                    "description": "Default daily work hours for new records",
                    "default": 8.0,
                },
                "default_break_minutes": {
                    "type": "integer",
                    "title": "Default Break Minutes",
                    "description": "Default break duration in minutes",
                    "default": 30,
                },
                "enable_project_allocation": {
                    "type": "boolean",
                    "title": "Enable Project Allocation",
                    "description": "Allow splitting hours across projects",
                    "default": True,
                },
                "default_country": {
                    "type": "string",
                    "title": "Default Country",
                    "description": "Default country for compliance validation",
                    "default": "AT",
                },
            },
        }

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
            TimeRecord,
            TimeAllocation,
            LeaveBalance,
            TimesheetSubmission,
            CompanyTimeSettings,
            TimeRecordAudit,
            CustomHoliday,
            UserTimePreferences,
        ]

    def get_event_handlers(self) -> dict[AppEvent, Callable[[EventPayload], Any]]:
        """Return event handlers for this plugin.

        Returns:
            Dictionary mapping events to handlers.
        """
        return {
            AppEvent.USER_LOGIN: self._on_user_login,
            AppEvent.USER_LOGOUT: self._on_user_logout,
        }

    def _on_user_login(self, payload: EventPayload) -> None:
        """Handle user login event.

        Args:
            payload: Event payload.
        """
        user_id = payload.data.get("user_id")
        logger.info(
            f"[TimeTracking] User logged in: {user_id} - "
            "Consider checking in if starting work"
        )

    def _on_user_logout(self, payload: EventPayload) -> None:
        """Handle user logout event.

        Args:
            payload: Event payload.
        """
        user_id = payload.data.get("user_id")
        logger.info(
            f"[TimeTracking] User logged out: {user_id} - "
            "Consider checking out if ending work"
        )

    async def on_install(self) -> None:
        """Called when the plugin is installed."""
        logger.info(
            "[TimeTracking] Plugin installed! "
            "Run migrations to create database tables."
        )

    async def on_enable(self) -> None:
        """Called when the plugin is enabled."""
        logger.info(
            f"[TimeTracking] Plugin enabled with settings: "
            f"work_hours={self._default_work_hours}, "
            f"break_minutes={self._default_break_minutes}, "
            f"country={self._default_country}"
        )

    async def on_disable(self) -> None:
        """Called when the plugin is disabled."""
        logger.info("[TimeTracking] Plugin disabled")

    async def on_uninstall(self) -> None:
        """Called when the plugin is uninstalled."""
        logger.info(
            "[TimeTracking] Plugin uninstalled. "
            "Time records are preserved in the database."
        )
