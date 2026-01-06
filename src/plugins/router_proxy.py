# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Plugin router proxy for dynamic route dispatch.

FastAPI compiles routes at startup, before the lifespan context runs.
This means routes added via app.include_router() during lifespan don't work.

This module provides a Starlette Router-based approach that allows dynamic
route registration after the app has started.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from starlette.routing import Mount, Router

if TYPE_CHECKING:
    from fastapi import APIRouter, FastAPI

logger = logging.getLogger(__name__)


class PluginRouterManager:
    """Manages plugin routers using Starlette's Router for dynamic mounting.

    This class creates a Starlette Router that can be mounted on the FastAPI app
    at startup. Plugin routers are then dynamically added to this router at
    runtime, which Starlette supports.
    """

    def __init__(self) -> None:
        """Initialize the plugin router manager."""
        self._router = Router()
        self._plugin_mounts: dict[str, Mount] = {}

    def get_router(self) -> Router:
        """Get the underlying Starlette router.

        This should be mounted on the FastAPI app at startup.
        """
        return self._router

    def add_plugin_router(
        self, plugin_id: str, router: APIRouter, app: FastAPI
    ) -> None:
        """Add a plugin's router dynamically.

        Args:
            plugin_id: Plugin identifier
            router: FastAPI APIRouter from the plugin
            app: Main FastAPI app (for dependency resolution)
        """
        if plugin_id in self._plugin_mounts:
            logger.warning(f"Plugin {plugin_id} router already mounted, replacing")
            self.remove_plugin_router(plugin_id)

        # Create a mini FastAPI app to hold the router (for proper FastAPI routing)
        from fastapi import FastAPI

        plugin_app = FastAPI(openapi_url=None)
        plugin_app.include_router(router)

        # Copy dependency overrides from main app
        plugin_app.dependency_overrides = app.dependency_overrides

        # Create mount at /{plugin_id}
        mount = Mount(f"/{plugin_id}", app=plugin_app)
        self._plugin_mounts[plugin_id] = mount
        self._router.routes.append(mount)

        logger.info(f"Mounted plugin router: {plugin_id}")

    def remove_plugin_router(self, plugin_id: str) -> None:
        """Remove a plugin's router.

        Args:
            plugin_id: Plugin identifier
        """
        mount = self._plugin_mounts.pop(plugin_id, None)
        if mount and mount in self._router.routes:
            self._router.routes.remove(mount)
            logger.info(f"Unmounted plugin router: {plugin_id}")


# Global singleton instance
_manager: PluginRouterManager | None = None


def get_plugin_router_manager() -> PluginRouterManager:
    """Get the global plugin router manager singleton."""
    global _manager
    if _manager is None:
        _manager = PluginRouterManager()
    return _manager


def reset_plugin_router_manager() -> None:
    """Reset the plugin router manager (for testing)."""
    global _manager
    _manager = None
