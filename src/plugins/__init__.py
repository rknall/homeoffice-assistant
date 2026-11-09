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
from src.plugins.loader import PluginLoader, PluginLoadError
from src.plugins.manifest import PluginValidationError
from src.plugins.permissions import PermissionChecker
from src.plugins.registry import PluginRegistry
from src.plugins.router_proxy import (
    PluginRouterManager,
    get_plugin_router_manager,
    reset_plugin_router_manager,
)

__all__ = [
    "AppEvent",
    "BasePlugin",
    "EventPayload",
    "Permission",
    "PermissionChecker",
    "PluginCapability",
    "PluginConfig",
    "PluginLoadError",
    "PluginLoader",
    "PluginManifest",
    "PluginRegistry",
    "PluginRouterManager",
    "PluginValidationError",
    "event_bus",
    "get_plugin_router_manager",
    "reset_plugin_router_manager",
]
