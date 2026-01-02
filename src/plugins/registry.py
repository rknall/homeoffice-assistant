# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Plugin registry for managing loaded plugins."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from src.plugins.base import BasePlugin, PluginConfig, PluginManifest
from src.plugins.events import AppEvent, event_bus
from src.plugins.loader import (
    PluginLoader,
)
from src.plugins.router_proxy import get_plugin_router_manager

if TYPE_CHECKING:
    from fastapi import FastAPI
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Central registry for all loaded plugins.

    This is a singleton that manages the lifecycle of all plugins:
    loading, enabling, disabling, and uninstalling.
    """

    _instance: ClassVar[PluginRegistry | None] = None

    def __init__(self) -> None:
        """Initialize the plugin registry."""
        self._plugins: dict[str, BasePlugin] = {}
        self._loader = PluginLoader()
        self._app: FastAPI | None = None
        self._initialized = False

    @classmethod
    def get_instance(cls) -> PluginRegistry:
        """Get the singleton instance of the registry."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        cls._instance = None

    def set_app(self, app: FastAPI) -> None:
        """Set the FastAPI app for route mounting.

        Args:
            app: FastAPI application instance
        """
        self._app = app

    def get_plugin(self, plugin_id: str) -> BasePlugin | None:
        """Get a loaded plugin by ID.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Plugin instance or None if not loaded
        """
        return self._plugins.get(plugin_id)

    def get_all_plugins(self) -> list[BasePlugin]:
        """Get all loaded plugins.

        Returns:
            List of all loaded plugin instances
        """
        return list(self._plugins.values())

    def is_plugin_loaded(self, plugin_id: str) -> bool:
        """Check if a plugin is loaded.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if plugin is loaded
        """
        return plugin_id in self._plugins

    async def load_all_plugins(self, db: Session) -> None:
        """Discover and load all installed plugins.

        Args:
            db: Database session
        """
        from src.models.plugin_config import PluginConfigModel

        if self._initialized:
            logger.warning("Plugin registry already initialized")
            return

        discovered = self._loader.discover_plugins()
        logger.info(f"Discovered {len(discovered)} plugins")

        for plugin_path, manifest in discovered:
            # Get config from database
            db_config = (
                db.query(PluginConfigModel)
                .filter(PluginConfigModel.plugin_id == manifest.id)
                .first()
            )

            if db_config is None:
                # Plugin on disk but not in database - skip
                logger.info(f"Skipping unregistered plugin: {manifest.id}")
                continue

            config = PluginConfig(
                settings=db_config.get_decrypted_settings(),
            )

            try:
                await self._load_single_plugin(plugin_path, manifest, config)
            except Exception as e:
                logger.error(f"Failed to load plugin {manifest.id}: {e}")

        self._initialized = True

    async def _load_single_plugin(
        self,
        plugin_path: Path,
        manifest: PluginManifest,
        config: PluginConfig,
    ) -> BasePlugin:
        """Load a single plugin.

        Args:
            plugin_path: Path to plugin directory
            manifest: Plugin manifest
            config: Plugin configuration

        Returns:
            Loaded plugin instance
        """
        plugin = self._loader.load_plugin(plugin_path, manifest, config)

        # Mount routes if plugin provides them
        router = plugin.get_router()
        if router and self._app:
            # Use the router proxy manager for dynamic route registration
            router_manager = get_plugin_router_manager()
            router_manager.add_plugin_router(manifest.id, router, self._app)
            logger.debug(f"Mounted routes for {manifest.id}")

        # Register event handlers
        handlers = plugin.get_event_handlers()
        for event_name, handler in handlers.items():
            try:
                event_type = AppEvent(event_name)
                event_bus.subscribe(event_type, handler, manifest.id)
            except ValueError:
                logger.warning(
                    f"Plugin {manifest.id} subscribed to unknown event: {event_name}"
                )

        # Call on_enable lifecycle hook
        await plugin.on_enable()

        self._plugins[manifest.id] = plugin
        logger.info(f"Loaded plugin: {manifest.id} v{manifest.version}")

        return plugin

    async def install_plugin(
        self,
        zip_path: Path,
        db: Session,
    ) -> BasePlugin:
        """Install and enable a new plugin from ZIP.

        Args:
            zip_path: Path to the plugin ZIP file
            db: Database session

        Returns:
            Installed and loaded plugin instance
        """
        from src.models.plugin_config import PluginConfigModel
        from src.plugins.migrations import PluginMigrationRunner
        from src.services.rbac_service import register_plugin_permissions

        # Extract and validate
        manifest = self._loader.install_from_zip(zip_path, db)

        # Run migrations if plugin has them
        plugin_path = self._loader.plugins_dir / manifest.id
        migration_runner = PluginMigrationRunner(plugin_path, manifest.id)
        if migration_runner.has_migrations():
            migration_runner.run_migrations()

        # Register plugin-provided permissions
        if manifest.provided_permissions:
            register_plugin_permissions(db, manifest.id, manifest.provided_permissions)
            logger.info(
                f"Registered {len(manifest.provided_permissions)} permissions "
                f"for plugin {manifest.id}"
            )

        # Create database config record
        db_config = PluginConfigModel(
            plugin_id=manifest.id,
            plugin_version=manifest.version,
            settings_encrypted=None,
        )
        db.add(db_config)
        db.commit()

        # Load the plugin
        config = PluginConfig(settings={})
        plugin = await self._load_single_plugin(plugin_path, manifest, config)

        # Call on_install lifecycle hook
        await plugin.on_install()

        # Publish event
        await event_bus.publish(
            AppEvent.PLUGIN_INSTALLED,
            {"plugin_id": manifest.id, "version": manifest.version},
        )

        return plugin

    async def uninstall_plugin(
        self,
        plugin_id: str,
        db: Session,
        drop_tables: bool = False,
        remove_permissions: bool = False,
        keep_files: bool = False,
    ) -> None:
        """Uninstall a plugin.

        Args:
            plugin_id: Plugin to uninstall
            db: Database session
            drop_tables: Whether to drop plugin's database tables
            remove_permissions: Whether to remove plugin-provided permissions
            keep_files: If True, keep plugin files on disk (for dev workflow)
        """
        from src.models.plugin_config import PluginConfigModel
        from src.plugins.migrations import PluginMigrationRunner
        from src.services.rbac_service import unregister_plugin_permissions

        plugin = self._plugins.get(plugin_id)

        if plugin:
            # Call lifecycle hook
            await plugin.on_uninstall()
            # Remove event handlers
            event_bus.unsubscribe_plugin(plugin_id)
            # Remove router
            router_manager = get_plugin_router_manager()
            router_manager.remove_plugin_router(plugin_id)
            # Remove from registry
            del self._plugins[plugin_id]

        # Drop tables if requested
        if drop_tables:
            plugin_path = self._loader.plugins_dir / plugin_id
            if plugin_path.exists():
                migration_runner = PluginMigrationRunner(plugin_path, plugin_id)
                migration_runner.downgrade_all()

        # Remove plugin-provided permissions if requested
        if remove_permissions:
            removed_count = unregister_plugin_permissions(db, plugin_id)
            if removed_count > 0:
                logger.info(
                    f"Removed {removed_count} permissions for plugin {plugin_id}"
                )

        # Remove from database
        db.query(PluginConfigModel).filter(
            PluginConfigModel.plugin_id == plugin_id
        ).delete()
        db.commit()

        # Remove files (unless keep_files is True for dev workflow)
        if not keep_files:
            self._loader.uninstall(plugin_id)
        else:
            logger.info(
                "Keeping files for plugin %s (dev mode): plugin files remain on disk, "
                "any previously installed Python dependencies are not removed, and "
                "the plugin may be rediscovered on restart but will not be auto-loaded "
                "because its database configuration was deleted.",
                plugin_id,
            )

        # Publish event
        await event_bus.publish(
            AppEvent.PLUGIN_UNINSTALLED,
            {"plugin_id": plugin_id},
        )

        logger.info(f"Uninstalled plugin {plugin_id}")

    async def update_plugin_settings(
        self,
        plugin_id: str,
        settings: dict,
        db: Session,
    ) -> None:
        """Update a plugin's settings.

        Args:
            plugin_id: Plugin to update
            settings: New settings dictionary
            db: Database session
        """
        from src.models.plugin_config import PluginConfigModel

        db_config = (
            db.query(PluginConfigModel)
            .filter(PluginConfigModel.plugin_id == plugin_id)
            .first()
        )

        if not db_config:
            raise ValueError(f"Plugin {plugin_id} not found")

        db_config.set_encrypted_settings(settings)
        db.commit()

        # Update loaded plugin's config
        plugin = self._plugins.get(plugin_id)
        if plugin:
            plugin.config.settings = settings

        logger.info(f"Updated settings for plugin {plugin_id}")
