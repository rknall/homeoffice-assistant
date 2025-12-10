# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Example plugin main class."""

import logging
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter
from sqlalchemy.orm import DeclarativeBase

from src.plugins.base import BasePlugin, PluginConfig, PluginManifest
from src.plugins.events import AppEvent, EventPayload

from .models import ExampleNote
from .routes import router as example_router

logger = logging.getLogger(__name__)


class ExamplePlugin(BasePlugin):
    """Example plugin demonstrating all plugin capabilities.

    This plugin shows how to:
    - Define API routes
    - Create database models
    - Subscribe to application events
    - Use configuration settings
    """

    def __init__(self, manifest: PluginManifest, config: PluginConfig) -> None:
        """Initialize the example plugin."""
        super().__init__(manifest, config)
        self._greeting = config.settings.get("greeting_message", "Hello!")
        self._notifications_enabled = config.settings.get("enable_notifications", True)

    @classmethod
    def get_config_schema(cls) -> dict[str, Any]:
        """Return JSON Schema for plugin configuration."""
        return {
            "type": "object",
            "properties": {
                "greeting_message": {
                    "type": "string",
                    "title": "Greeting Message",
                    "description": (
                        "Custom greeting message displayed on the plugin page"
                    ),
                    "default": "Hello from the Example Plugin!",
                },
                "enable_notifications": {
                    "type": "boolean",
                    "title": "Enable Notifications",
                    "description": "Log events to console when they occur",
                    "default": True,
                },
            },
        }

    def get_router(self) -> APIRouter | None:
        """Return FastAPI router with plugin endpoints."""
        return example_router

    def get_models(self) -> list[type[DeclarativeBase]]:
        """Return SQLAlchemy models for this plugin."""
        return [ExampleNote]

    def get_event_handlers(self) -> dict[AppEvent, Callable[[EventPayload], Any]]:
        """Return event handlers for this plugin."""
        if not self._notifications_enabled:
            return {}

        return {
            AppEvent.USER_LOGIN: self._on_user_login,
            AppEvent.USER_LOGOUT: self._on_user_logout,
            AppEvent.EVENT_CREATED: self._on_event_created,
            AppEvent.EXPENSE_CREATED: self._on_expense_created,
        }

    def _on_user_login(self, payload: EventPayload) -> None:
        """Handle user login event."""
        user_id = payload.data.get("user_id")
        logger.info(f"[ExamplePlugin] User logged in: {user_id}")

    def _on_user_logout(self, payload: EventPayload) -> None:
        """Handle user logout event."""
        user_id = payload.data.get("user_id")
        logger.info(f"[ExamplePlugin] User logged out: {user_id}")

    def _on_event_created(self, payload: EventPayload) -> None:
        """Handle event created."""
        event_name = payload.data.get("name")
        logger.info(f"[ExamplePlugin] New event created: {event_name}")

    def _on_expense_created(self, payload: EventPayload) -> None:
        """Handle expense created."""
        amount = payload.data.get("amount")
        currency = payload.data.get("currency")
        logger.info(f"[ExamplePlugin] New expense: {amount} {currency}")

    async def on_install(self) -> None:
        """Called when the plugin is installed."""
        logger.info("[ExamplePlugin] Plugin installed!")

    async def on_enable(self) -> None:
        """Called when the plugin is enabled."""
        logger.info(f"[ExamplePlugin] Plugin enabled with greeting: {self._greeting}")

    async def on_disable(self) -> None:
        """Called when the plugin is disabled."""
        logger.info("[ExamplePlugin] Plugin disabled")

    async def on_uninstall(self) -> None:
        """Called when the plugin is uninstalled."""
        logger.info("[ExamplePlugin] Plugin uninstalled - goodbye!")
