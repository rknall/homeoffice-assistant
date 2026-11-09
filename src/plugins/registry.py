# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Plugin registry for managing loaded plugins."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from src.plugins.base import BasePlugin, PluginConfig, PluginManifest
from src.plugins.events import AppEvent, event_bus
from src.plugins.loader import PluginLoader
from src.plugins.manifest import (
    PLUGIN_MANIFEST_FILE,
    PluginValidationError,
    parse_manifest,
)
from src.plugins.migrations import PluginMigrationRunner
from src.plugins.router_proxy import get_plugin_router_manager
from src.services import config_secrets

if TYPE_CHECKING:
    from fastapi import FastAPI
    from sqlalchemy.orm import Session

    from src.models.plugin_config import PluginConfigModel

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

    def get_config_schema(self, plugin_id: str) -> dict:
        """Return the config schema of a loaded plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            The plugin's JSON schema, or an empty dict when it is not loaded
        """
        plugin = self._plugins.get(plugin_id)
        return plugin.get_config_schema() if plugin else {}

    def _registered_plugins(
        self, db: Session
    ) -> list[tuple[Path, PluginManifest, PluginConfigModel]]:
        """Return the plugins found on disk that have a database record.

        Args:
            db: Database session

        Returns:
            Tuples of plugin path, manifest and database config
        """
        from src.models.plugin_config import PluginConfigModel

        configs = {c.plugin_id: c for c in db.query(PluginConfigModel).all()}
        registered = []
        for plugin_path, manifest in self._loader.discover_plugins():
            db_config = configs.get(manifest.id)
            if db_config is None:
                logger.info("Skipping unregistered plugin: %s", manifest.id)
                continue
            registered.append((plugin_path, manifest, db_config))
        return registered

    @staticmethod
    def _migrate(plugin_path: Path, manifest: PluginManifest) -> bool:
        """Bring one plugin's schema to its head revision.

        Args:
            plugin_path: Path to plugin directory
            manifest: Plugin manifest

        Returns:
            True on success, False when the migrations failed (logged)
        """
        try:
            PluginMigrationRunner(plugin_path, manifest.id, manifest).run_migrations()
        except Exception:
            logger.exception(
                "Migrations failed for plugin %s; the plugin is not loaded",
                manifest.id,
            )
            return False
        return True

    def run_plugin_migrations(self, db: Session) -> list[str]:
        """Run pending migrations of every registered plugin.

        A failing plugin is logged and skipped, the others still migrate.

        Args:
            db: Database session

        Returns:
            IDs of the plugins whose migrations failed
        """
        return [
            manifest.id
            for plugin_path, manifest, _config in self._registered_plugins(db)
            if not self._migrate(plugin_path, manifest)
        ]

    async def load_all_plugins(self, db: Session) -> None:
        """Migrate and load all installed plugins.

        Each registered plugin is brought to its migration head before it is
        loaded, so a new image's bundled plugin migrations are applied at
        startup. A plugin whose migrations fail is skipped.

        Args:
            db: Database session
        """
        if self._initialized:
            logger.warning("Plugin registry already initialized")
            return

        for plugin_path, manifest, db_config in self._registered_plugins(db):
            # Sync version from manifest to database if changed
            if db_config.plugin_version != manifest.version:
                logger.info(
                    f"Plugin {manifest.id} version changed: "
                    f"{db_config.plugin_version} -> {manifest.version}"
                )
                db_config.plugin_version = manifest.version
                db.commit()

            if not self._migrate(plugin_path, manifest):
                continue

            config = PluginConfig(settings=db_config.get_decrypted_settings())

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
        upgrade: bool = False,
    ) -> tuple[BasePlugin, str | None]:
        """Install and enable a new plugin from ZIP, or upgrade an existing one.

        Args:
            zip_path: Path to the plugin ZIP file
            db: Database session
            upgrade: If True, allow replacing an existing plugin

        Returns:
            Tuple of (installed plugin instance, old version if upgraded else None)
        """
        # Extract and validate (may replace existing if upgrade=True)
        manifest, old_version = self._loader.install_from_zip(zip_path, db, upgrade)

        # If upgrading, we need to unload the old plugin first
        if old_version and await self._unload(manifest.id):
            logger.info(f"Unloaded old plugin {manifest.id} v{old_version}")

        plugin_path = self._loader.plugins_dir / manifest.id
        plugin = await self._activate(plugin_path, manifest, db)

        payload = {"plugin_id": manifest.id, "version": manifest.version}
        if old_version:
            payload["upgraded_from"] = old_version
        await event_bus.publish(AppEvent.PLUGIN_INSTALLED, payload)

        return plugin, old_version

    async def _unload(self, plugin_id: str) -> bool:
        """Stop a loaded plugin: lifecycle hook, event handlers, routes.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if the plugin was loaded
        """
        plugin = self._plugins.pop(plugin_id, None)
        if plugin is None:
            return False
        await plugin.on_uninstall()
        event_bus.unsubscribe_plugin(plugin_id)
        get_plugin_router_manager().remove_plugin_router(plugin_id)
        return True

    async def install_discovered(self, plugin_id: str, db: Session) -> BasePlugin:
        """Install a plugin that is on disk but not registered yet.

        Args:
            plugin_id: Plugin identifier
            db: Database session

        Returns:
            The loaded plugin instance

        Raises:
            PluginValidationError: The plugin is already installed.
            LookupError: No plugin with this ID is in the plugins directory.
        """
        from src.models.plugin_config import PluginConfigModel

        existing = (
            db.query(PluginConfigModel)
            .filter(PluginConfigModel.plugin_id == plugin_id)
            .first()
        )
        if existing:
            raise PluginValidationError(f"Plugin {plugin_id} is already installed")

        for plugin_path, manifest in self._loader.discover_plugins():
            if manifest.id == plugin_id:
                return await self._activate(plugin_path, manifest, db)

        raise LookupError(f"Plugin {plugin_id} not found in plugins directory")

    async def _activate(
        self, plugin_path: Path, manifest: PluginManifest, db: Session
    ) -> BasePlugin:
        """Migrate, register and load a plugin whose files are in place.

        Runs the plugin's migrations, registers its permissions, creates or
        updates its database record, loads it and calls ``on_install``.

        Args:
            plugin_path: Path to plugin directory
            manifest: Plugin manifest
            db: Database session

        Returns:
            The loaded plugin instance
        """
        from src.models.plugin_config import PluginConfigModel
        from src.services.rbac_service import register_plugin_permissions

        PluginMigrationRunner(plugin_path, manifest.id, manifest).run_migrations()

        if manifest.provided_permissions:
            register_plugin_permissions(db, manifest.id, manifest.provided_permissions)
            logger.info(
                f"Registered {len(manifest.provided_permissions)} permissions "
                f"for plugin {manifest.id}"
            )

        db_config = (
            db.query(PluginConfigModel)
            .filter(PluginConfigModel.plugin_id == manifest.id)
            .first()
        )
        created = db_config is None
        if db_config is None:
            db_config = PluginConfigModel(plugin_id=manifest.id)
            db.add(db_config)
        db_config.plugin_version = manifest.version
        db.commit()

        config = PluginConfig(settings=db_config.get_decrypted_settings())
        try:
            plugin = await self._load_single_plugin(plugin_path, manifest, config)
            await plugin.on_install()
        except Exception:
            # A new plugin that never started must not be listed as installed.
            self._plugins.pop(manifest.id, None)
            event_bus.unsubscribe_plugin(manifest.id)
            get_plugin_router_manager().remove_plugin_router(manifest.id)
            if created:
                db.delete(db_config)
                db.commit()
            raise
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
        from src.services.rbac_service import unregister_plugin_permissions

        await self._unload(plugin_id)

        if drop_tables:
            plugin_path = self._loader.plugins_dir / plugin_id
            if plugin_path.exists():
                # Try to load manifest for table_prefix, but don't fail if not available
                manifest = None
                try:
                    manifest_path = plugin_path / PLUGIN_MANIFEST_FILE
                    if manifest_path.exists():
                        manifest = parse_manifest(manifest_path)
                except Exception as e:
                    logger.warning(
                        f"Could not load manifest for plugin {plugin_id}: {e}. "
                        "Will use derived table prefix."
                    )

                PluginMigrationRunner(plugin_path, plugin_id, manifest).downgrade_all()

        if remove_permissions:
            removed_count = unregister_plugin_permissions(db, plugin_id)
            if removed_count > 0:
                logger.info(
                    f"Removed {removed_count} permissions for plugin {plugin_id}"
                )

        db.query(PluginConfigModel).filter(
            PluginConfigModel.plugin_id == plugin_id
        ).delete()
        db.commit()

        # Remove files (unless keep_files is True for dev workflow)
        if not keep_files:
            self._loader.uninstall(plugin_id)
        else:
            logger.info(
                "Keeping files for plugin %s (dev mode); it is discovered again "
                "but not loaded, its record is deleted",
                plugin_id,
            )

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
    ) -> dict:
        """Update a plugin's settings.

        Secret fields (``format: "password"`` in the plugin's config schema)
        that arrive blank, as the masked value sent back by the edit form,
        keep their stored value.

        Args:
            plugin_id: Plugin to update
            settings: New settings dictionary
            db: Database session

        Returns:
            The stored, unmasked settings

        Raises:
            ValueError: The plugin is not installed.
        """
        from src.models.plugin_config import PluginConfigModel

        db_config = (
            db.query(PluginConfigModel)
            .filter(PluginConfigModel.plugin_id == plugin_id)
            .first()
        )

        if not db_config:
            raise ValueError(f"Plugin {plugin_id} not found")

        merged = config_secrets.merge(
            db_config.get_decrypted_settings(),
            settings,
            self.get_config_schema(plugin_id),
        )
        db_config.set_encrypted_settings(merged)
        db.commit()

        plugin = self._plugins.get(plugin_id)
        if plugin:
            plugin.config.settings = merged

        logger.info(f"Updated settings for plugin {plugin_id}")
        return merged
