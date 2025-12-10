# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Plugin system for HomeOffice Assistant.

This module provides the infrastructure for loading, managing, and
running plugins that extend the application's functionality.
"""

from src.plugins.base import (
    BasePlugin,
    Permission,
    PluginCapability,
    PluginConfig,
    PluginManifest,
)
from src.plugins.events import AppEvent, EventPayload, event_bus
from src.plugins.loader import (
    PluginLoader,
    PluginLoadError,
    PluginValidationError,
)
from src.plugins.permissions import PermissionChecker
from src.plugins.registry import PluginRegistry

__all__ = [  # noqa: RUF022
    # Base classes
    "BasePlugin",
    "PluginManifest",
    "PluginConfig",
    "PluginCapability",
    "Permission",
    # Events
    "AppEvent",
    "EventPayload",
    "event_bus",
    # Loader
    "PluginLoader",
    "PluginLoadError",
    "PluginValidationError",
    # Registry
    "PluginRegistry",
    # Permissions
    "PermissionChecker",
]
