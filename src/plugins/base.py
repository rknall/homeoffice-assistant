# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Base classes and interfaces for the plugin system."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import APIRouter
    from sqlalchemy.orm import DeclarativeBase


class PluginCapability(str, Enum):
    """Capabilities a plugin can declare."""

    BACKEND = "backend"
    FRONTEND = "frontend"
    CONFIG = "config"


class Permission(str, Enum):
    """Available plugin permissions."""

    # User permissions
    USER_READ = "user.read"
    USER_WRITE_SELF = "user.write.self"
    USER_WRITE_ALL = "user.write.all"

    # Event permissions
    EVENT_READ = "event.read"
    EVENT_WRITE = "event.write"
    EVENT_DELETE = "event.delete"

    # Company permissions
    COMPANY_READ = "company.read"
    COMPANY_WRITE = "company.write"

    # Expense permissions
    EXPENSE_READ = "expense.read"
    EXPENSE_WRITE = "expense.write"

    # Calendar permissions (for future use)
    CALENDAR_READ = "calendar.read"
    CALENDAR_WRITE = "calendar.write"

    # Integration permissions
    INTEGRATION_USE = "integration.use"
    INTEGRATION_CONFIG = "integration.config"

    # System permissions
    SYSTEM_SETTINGS_READ = "system.settings.read"
    SYSTEM_SETTINGS_WRITE = "system.settings.write"


@dataclass
class ProvidedPermission:
    """A permission provided by a plugin.

    Plugin-provided permissions allow plugins to define their own permission
    codes that can be assigned to roles. The code must start with the plugin
    ID prefix (e.g., 'example.notes.read' for plugin 'example').
    """

    code: str
    description: str


@dataclass
class PluginManifest:
    """Plugin manifest containing metadata and requirements.

    Permissions are split into two categories:
    - required_permissions: Permissions the plugin needs from the host app
    - provided_permissions: New permission codes the plugin adds to the system

    For backward compatibility, 'permissions' maps to required_permissions.
    """

    id: str
    name: str
    version: str
    description: str
    author: str = ""
    homepage: str = ""
    license: str = ""
    min_host_version: str = "0.1.0"
    max_host_version: str | None = None
    capabilities: set[PluginCapability] = field(default_factory=set)
    # Permissions the plugin requires from the host application
    required_permissions: set[Permission] = field(default_factory=set)
    # Permissions the plugin provides (adds to the system)
    provided_permissions: list[ProvidedPermission] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    # Python package dependencies (e.g., ["holidays>=0.62"])
    python_dependencies: list[str] = field(default_factory=list)

    # Backward compatibility: alias 'permissions' to 'required_permissions'
    @property
    def permissions(self) -> set[Permission]:
        """Alias for required_permissions (backward compatibility)."""
        return self.required_permissions


@dataclass
class PluginConfig:
    """Runtime configuration for a plugin instance."""

    enabled: bool = True
    settings: dict[str, Any] = field(default_factory=dict)


class BasePlugin(ABC):
    """Base class that all plugins must extend.

    Plugins implement this interface to integrate with the host application.
    The plugin system will call lifecycle methods at appropriate times.
    """

    def __init__(
        self,
        manifest: PluginManifest,
        config: PluginConfig,
        plugin_path: str,
    ) -> None:
        """Initialize plugin with manifest and configuration.

        Args:
            manifest: Parsed plugin manifest
            config: Runtime configuration from database
            plugin_path: Absolute path to plugin directory
        """
        self.manifest = manifest
        self.config = config
        self.plugin_path = plugin_path

    @property
    def id(self) -> str:
        """Plugin unique identifier."""
        return self.manifest.id

    @property
    def name(self) -> str:
        """Plugin display name."""
        return self.manifest.name

    @property
    def version(self) -> str:
        """Plugin version string."""
        return self.manifest.version

    @classmethod
    @abstractmethod
    def get_config_schema(cls) -> dict[str, Any]:
        """Return JSON Schema for plugin configuration.

        This schema is used to generate the configuration UI in the admin panel.
        Return an empty dict if the plugin has no configurable settings.

        Returns:
            JSON Schema dictionary describing the configuration options.
        """
        ...

    @abstractmethod
    def get_router(self) -> APIRouter | None:
        """Return FastAPI router for plugin API endpoints.

        Routes will be mounted at /api/v1/plugins/{plugin_id}/
        Return None if plugin has no backend routes.

        Returns:
            FastAPI APIRouter instance or None.
        """
        ...

    @abstractmethod
    def get_models(self) -> list[type[DeclarativeBase]]:
        """Return SQLAlchemy model classes for this plugin.

        Models will be registered with the application's metadata.
        Tables are created via plugin-specific Alembic migrations.
        Return an empty list if plugin has no database tables.

        Returns:
            List of SQLAlchemy model classes.
        """
        ...

    def get_event_handlers(self) -> dict[str, Callable]:
        """Return event handlers for application events.

        Keys are event names (from AppEvent enum values), values are
        handler functions that receive EventPayload.

        Override this method to subscribe to application events.

        Returns:
            Dictionary mapping event names to handler functions.
        """
        return {}

    def get_services(self) -> dict[str, type]:
        """Return service classes that can be injected.

        Override to provide services that can be used by other plugins
        or accessed through the plugin context.

        Returns:
            Dictionary mapping service names to service classes.
        """
        return {}

    async def on_install(self) -> None:  # noqa: B027
        """Called when plugin is first installed.

        Use for one-time setup tasks like creating default data.
        Database migrations are run before this method is called.
        """

    async def on_enable(self) -> None:  # noqa: B027
        """Called when plugin is enabled.

        Called on application startup for enabled plugins,
        and when an admin enables a previously disabled plugin.
        """

    async def on_disable(self) -> None:  # noqa: B027
        """Called when plugin is disabled.

        Use to clean up resources, cancel background tasks, etc.
        The plugin's routes will be unmounted after this method returns.
        """

    async def on_uninstall(self) -> None:  # noqa: B027
        """Called before plugin is uninstalled.

        Use for cleanup tasks. Note that database tables are NOT
        dropped automatically - use the drop_tables option when
        uninstalling to remove plugin tables.
        """

    async def on_upgrade(self, from_version: str) -> None:  # noqa: B027
        """Called when plugin is upgraded from a previous version.

        Args:
            from_version: Previous version string
        """

    def has_permission(self, permission: Permission) -> bool:
        """Check if plugin has a specific required permission.

        Args:
            permission: Permission to check

        Returns:
            True if plugin has the permission
        """
        return permission in self.manifest.required_permissions

    def has_all_permissions(self, permissions: set[Permission]) -> bool:
        """Check if plugin has all specified required permissions.

        Args:
            permissions: Set of permissions to check

        Returns:
            True if plugin has all the permissions
        """
        return permissions.issubset(self.manifest.required_permissions)
