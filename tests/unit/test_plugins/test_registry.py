# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for plugin registry."""

import json
from pathlib import Path

import pytest

from src.plugins.base import BasePlugin, PluginConfig, PluginManifest
from src.plugins.loader import PLUGIN_MANIFEST_FILE
from src.plugins.registry import PluginRegistry


class ConcretePlugin(BasePlugin):
    """Concrete plugin implementation for testing."""

    @classmethod
    def get_config_schema(cls):
        return {"type": "object", "properties": {"key": {"type": "string"}}}

    def get_router(self):
        return None

    def get_models(self):
        return []


class TestPluginRegistry:
    """Tests for PluginRegistry singleton."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset registry before each test."""
        PluginRegistry.reset_instance()
        yield
        PluginRegistry.reset_instance()

    def test_singleton_instance(self):
        """Test that registry is a singleton."""
        registry1 = PluginRegistry.get_instance()
        registry2 = PluginRegistry.get_instance()
        assert registry1 is registry2

    def test_reset_instance(self):
        """Test resetting singleton instance."""
        registry1 = PluginRegistry.get_instance()
        PluginRegistry.reset_instance()
        registry2 = PluginRegistry.get_instance()
        assert registry1 is not registry2

    def test_get_plugin_not_loaded(self):
        """Test getting plugin that isn't loaded."""
        registry = PluginRegistry.get_instance()
        plugin = registry.get_plugin("nonexistent")
        assert plugin is None

    def test_get_all_plugins_empty(self):
        """Test getting all plugins when none loaded."""
        registry = PluginRegistry.get_instance()
        plugins = registry.get_all_plugins()
        assert plugins == []

    def test_is_plugin_loaded_false(self):
        """Test is_plugin_loaded when not loaded."""
        registry = PluginRegistry.get_instance()
        assert registry.is_plugin_loaded("test") is False

    def test_register_and_get_plugin(self):
        """Test registering and retrieving a plugin."""
        registry = PluginRegistry.get_instance()

        manifest = PluginManifest(
            id="test-plugin",
            name="Test Plugin",
            version="1.0.0",
            description="Test",
        )
        config = PluginConfig()
        plugin = ConcretePlugin(manifest, config, "/path/to/plugin")

        # Directly add to registry (normally done via load_all_plugins)
        registry._plugins["test-plugin"] = plugin

        assert registry.is_plugin_loaded("test-plugin") is True
        assert registry.get_plugin("test-plugin") is plugin

    def test_get_all_plugins(self):
        """Test getting all loaded plugins."""
        registry = PluginRegistry.get_instance()

        # Add multiple plugins
        for i in range(3):
            manifest = PluginManifest(
                id=f"plugin-{i}",
                name=f"Plugin {i}",
                version="1.0.0",
                description="Test",
            )
            config = PluginConfig()
            plugin = ConcretePlugin(manifest, config, f"/path/{i}")
            registry._plugins[f"plugin-{i}"] = plugin

        all_plugins = registry.get_all_plugins()
        assert len(all_plugins) == 3

    def test_set_app(self):
        """Test setting FastAPI app."""
        registry = PluginRegistry.get_instance()
        mock_app = object()

        registry.set_app(mock_app)

        assert registry._app is mock_app


class TestPluginRegistryWithDatabase:
    """Tests for PluginRegistry that require database."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset registry before each test."""
        PluginRegistry.reset_instance()
        yield
        PluginRegistry.reset_instance()

    @pytest.fixture
    def plugins_dir(self, tmp_path):
        """Create a temporary plugins directory."""
        plugins = tmp_path / "plugins"
        plugins.mkdir()
        return plugins

    def create_plugin_structure(
        self, plugins_dir: Path, plugin_id: str, manifest_data: dict
    ) -> Path:
        """Helper to create a plugin directory structure."""
        plugin_dir = plugins_dir / plugin_id
        plugin_dir.mkdir(parents=True)

        manifest_path = plugin_dir / PLUGIN_MANIFEST_FILE
        manifest_path.write_text(json.dumps(manifest_data))

        backend_dir = plugin_dir / "backend"
        backend_dir.mkdir()

        plugin_py = backend_dir / "plugin.py"
        plugin_py.write_text("""
from src.plugins.base import BasePlugin

class TestPlugin(BasePlugin):
    @classmethod
    def get_config_schema(cls):
        return {}

    def get_router(self):
        return None

    def get_models(self):
        return []
""")

        return plugin_dir

    @pytest.mark.asyncio
    async def test_load_all_plugins_empty(self, db_session, plugins_dir, monkeypatch):
        """Test loading plugins when none exist."""
        from src.plugins.loader import PluginLoader

        # Monkeypatch the loader to use our temp directory
        original_init = PluginLoader.__init__

        def patched_init(self, plugins_dir_arg=None):
            original_init(self, plugins_dir)

        monkeypatch.setattr(PluginLoader, "__init__", patched_init)

        registry = PluginRegistry.get_instance()
        await registry.load_all_plugins(db_session)

        assert registry.get_all_plugins() == []

    @pytest.mark.asyncio
    async def test_load_all_plugins_skips_unregistered(
        self, db_session, plugins_dir, monkeypatch
    ):
        """Test that unregistered plugins are skipped."""
        from src.plugins.loader import PluginLoader

        # Create plugin on disk but not in database
        self.create_plugin_structure(
            plugins_dir,
            "unregistered",
            {
                "id": "unregistered",
                "name": "Unregistered",
                "version": "1.0.0",
                "description": "Not in DB",
            },
        )

        original_init = PluginLoader.__init__

        def patched_init(self, plugins_dir_arg=None):
            original_init(self, plugins_dir)

        monkeypatch.setattr(PluginLoader, "__init__", patched_init)

        registry = PluginRegistry.get_instance()
        await registry.load_all_plugins(db_session)

        # Plugin not in database should not be loaded
        assert registry.get_plugin("unregistered") is None

    @pytest.mark.asyncio
    async def test_load_all_plugins_skips_disabled(
        self, db_session, plugins_dir, monkeypatch
    ):
        """Test that disabled plugins are skipped."""
        from src.models.plugin_config import PluginConfigModel
        from src.plugins.loader import PluginLoader

        # Create plugin on disk
        self.create_plugin_structure(
            plugins_dir,
            "disabled-plugin",
            {
                "id": "disabled-plugin",
                "name": "Disabled",
                "version": "1.0.0",
                "description": "Disabled plugin",
            },
        )

        # Register as disabled in database
        db_config = PluginConfigModel(
            plugin_id="disabled-plugin",
            plugin_version="1.0.0",
        )
        db_session.add(db_config)
        db_session.commit()

        original_init = PluginLoader.__init__

        def patched_init(self, plugins_dir_arg=None):
            original_init(self, plugins_dir)

        monkeypatch.setattr(PluginLoader, "__init__", patched_init)

        registry = PluginRegistry.get_instance()
        await registry.load_all_plugins(db_session)

        # Disabled plugin should not be loaded
        assert registry.get_plugin("disabled-plugin") is None

    @pytest.mark.asyncio
    async def test_update_plugin_settings_not_found(self, db_session):
        """Test updating settings for non-existent plugin."""
        registry = PluginRegistry.get_instance()

        with pytest.raises(ValueError, match="not found"):
            await registry.update_plugin_settings(
                "nonexistent", {"key": "value"}, db_session
            )

    @pytest.mark.asyncio
    async def test_update_plugin_settings(self, db_session):
        """Test updating plugin settings."""
        from src.models.plugin_config import PluginConfigModel

        # Create plugin config in database
        db_config = PluginConfigModel(
            plugin_id="test-plugin",
            plugin_version="1.0.0",
        )
        db_session.add(db_config)
        db_session.commit()

        registry = PluginRegistry.get_instance()

        # Add a mock plugin to registry
        manifest = PluginManifest(
            id="test-plugin",
            name="Test",
            version="1.0.0",
            description="Test",
        )
        config = PluginConfig(settings={})
        plugin = ConcretePlugin(manifest, config, "/path")
        registry._plugins["test-plugin"] = plugin

        await registry.update_plugin_settings(
            "test-plugin",
            {"new_key": "new_value"},
            db_session,
        )

        # Check plugin's config was updated
        assert plugin.config.settings["new_key"] == "new_value"

    @pytest.mark.asyncio
    async def test_uninstall_plugin(self, db_session, plugins_dir, monkeypatch):
        """Test uninstalling a plugin."""
        from src.models.plugin_config import PluginConfigModel
        from src.plugins.loader import PluginLoader

        # Create plugin on disk
        self.create_plugin_structure(
            plugins_dir,
            "to-uninstall",
            {
                "id": "to-uninstall",
                "name": "To Uninstall",
                "version": "1.0.0",
                "description": "Will be uninstalled",
            },
        )

        # Create plugin config in database
        db_config = PluginConfigModel(
            plugin_id="to-uninstall",
            plugin_version="1.0.0",
        )
        db_session.add(db_config)
        db_session.commit()

        original_init = PluginLoader.__init__

        def patched_init(self, plugins_dir_arg=None):
            original_init(self, plugins_dir)

        monkeypatch.setattr(PluginLoader, "__init__", patched_init)

        registry = PluginRegistry.get_instance()

        # Add plugin to registry
        manifest = PluginManifest(
            id="to-uninstall",
            name="To Uninstall",
            version="1.0.0",
            description="Test",
        )
        config = PluginConfig()
        plugin = ConcretePlugin(manifest, config, str(plugins_dir / "to-uninstall"))
        registry._plugins["to-uninstall"] = plugin

        await registry.uninstall_plugin("to-uninstall", db_session)

        # Plugin should be removed from registry
        assert registry.get_plugin("to-uninstall") is None

        # Plugin should be removed from database
        remaining = (
            db_session.query(PluginConfigModel)
            .filter(PluginConfigModel.plugin_id == "to-uninstall")
            .first()
        )
        assert remaining is None

        # Plugin directory should be removed
        assert not (plugins_dir / "to-uninstall").exists()
