# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for plugin base classes and interfaces."""

import pytest

from src.plugins.base import (
    BasePlugin,
    Permission,
    PluginCapability,
    PluginConfig,
    PluginManifest,
)


class TestPluginCapability:
    """Tests for PluginCapability enum."""

    def test_capability_values(self):
        """Test that all capability values are correct."""
        assert PluginCapability.BACKEND.value == "backend"
        assert PluginCapability.FRONTEND.value == "frontend"
        assert PluginCapability.CONFIG.value == "config"

    def test_capability_is_string_enum(self):
        """Test that capabilities are string enums."""
        assert isinstance(PluginCapability.BACKEND, str)
        assert PluginCapability.BACKEND == "backend"


class TestPermission:
    """Tests for Permission enum."""

    def test_user_permissions(self):
        """Test user permission values."""
        assert Permission.USER_READ.value == "user.read"
        assert Permission.USER_WRITE_SELF.value == "user.write.self"
        assert Permission.USER_WRITE_ALL.value == "user.write.all"

    def test_event_permissions(self):
        """Test event permission values."""
        assert Permission.EVENT_READ.value == "event.read"
        assert Permission.EVENT_WRITE.value == "event.write"
        assert Permission.EVENT_DELETE.value == "event.delete"

    def test_company_permissions(self):
        """Test company permission values."""
        assert Permission.COMPANY_READ.value == "company.read"
        assert Permission.COMPANY_WRITE.value == "company.write"

    def test_expense_permissions(self):
        """Test expense permission values."""
        assert Permission.EXPENSE_READ.value == "expense.read"
        assert Permission.EXPENSE_WRITE.value == "expense.write"

    def test_calendar_permissions(self):
        """Test calendar permission values."""
        assert Permission.CALENDAR_READ.value == "calendar.read"
        assert Permission.CALENDAR_WRITE.value == "calendar.write"

    def test_integration_permissions(self):
        """Test integration permission values."""
        assert Permission.INTEGRATION_USE.value == "integration.use"
        assert Permission.INTEGRATION_CONFIG.value == "integration.config"

    def test_system_permissions(self):
        """Test system permission values."""
        assert Permission.SYSTEM_SETTINGS_READ.value == "system.settings.read"
        assert Permission.SYSTEM_SETTINGS_WRITE.value == "system.settings.write"


class TestPluginManifest:
    """Tests for PluginManifest dataclass."""

    def test_create_minimal_manifest(self):
        """Test creating a manifest with minimal required fields."""
        manifest = PluginManifest(
            id="test-plugin",
            name="Test Plugin",
            version="1.0.0",
            description="A test plugin",
        )
        assert manifest.id == "test-plugin"
        assert manifest.name == "Test Plugin"
        assert manifest.version == "1.0.0"
        assert manifest.description == "A test plugin"
        assert manifest.author == ""
        assert manifest.homepage == ""
        assert manifest.license == ""
        assert manifest.min_host_version == "0.1.0"
        assert manifest.max_host_version is None
        assert manifest.capabilities == set()
        assert manifest.required_permissions == set()
        assert manifest.permissions == set()  # property alias
        assert manifest.provided_permissions == []
        assert manifest.dependencies == []

    def test_create_full_manifest(self):
        """Test creating a manifest with all fields."""
        manifest = PluginManifest(
            id="full-plugin",
            name="Full Plugin",
            version="2.0.0",
            description="A fully configured plugin",
            author="Test Author",
            homepage="https://example.com",
            license="MIT",
            min_host_version="0.2.0",
            max_host_version="1.0.0",
            capabilities={PluginCapability.BACKEND, PluginCapability.FRONTEND},
            required_permissions={Permission.USER_READ, Permission.EVENT_READ},
            dependencies=["other-plugin"],
        )
        assert manifest.author == "Test Author"
        assert manifest.homepage == "https://example.com"
        assert manifest.license == "MIT"
        assert manifest.min_host_version == "0.2.0"
        assert manifest.max_host_version == "1.0.0"
        assert PluginCapability.BACKEND in manifest.capabilities
        assert PluginCapability.FRONTEND in manifest.capabilities
        assert Permission.USER_READ in manifest.required_permissions
        assert Permission.USER_READ in manifest.permissions  # property alias
        assert "other-plugin" in manifest.dependencies


class TestPluginConfig:
    """Tests for PluginConfig dataclass."""

    def test_create_default_config(self):
        """Test creating a config with defaults."""
        config = PluginConfig()
        assert config.enabled is True
        assert config.settings == {}

    def test_create_custom_config(self):
        """Test creating a config with custom values."""
        config = PluginConfig(
            enabled=False,
            settings={"api_key": "secret", "timeout": 30},
        )
        assert config.enabled is False
        assert config.settings["api_key"] == "secret"
        assert config.settings["timeout"] == 30


class ConcretePlugin(BasePlugin):
    """Concrete implementation of BasePlugin for testing."""

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "api_key": {"type": "string"},
            },
        }

    def get_router(self):
        return None

    def get_models(self):
        return []


class TestBasePlugin:
    """Tests for BasePlugin abstract class."""

    @pytest.fixture
    def manifest(self):
        """Create a test manifest."""
        return PluginManifest(
            id="test-plugin",
            name="Test Plugin",
            version="1.0.0",
            description="A test plugin",
            required_permissions={Permission.USER_READ, Permission.EVENT_READ},
        )

    @pytest.fixture
    def config(self):
        """Create a test config."""
        return PluginConfig(enabled=True, settings={"key": "value"})

    @pytest.fixture
    def plugin(self, manifest, config):
        """Create a test plugin instance."""
        return ConcretePlugin(manifest, config, "/path/to/plugin")

    def test_plugin_initialization(self, plugin, manifest, config):
        """Test plugin initialization."""
        assert plugin.manifest == manifest
        assert plugin.config == config
        assert plugin.plugin_path == "/path/to/plugin"

    def test_plugin_id_property(self, plugin):
        """Test plugin id property."""
        assert plugin.id == "test-plugin"

    def test_plugin_name_property(self, plugin):
        """Test plugin name property."""
        assert plugin.name == "Test Plugin"

    def test_plugin_version_property(self, plugin):
        """Test plugin version property."""
        assert plugin.version == "1.0.0"

    def test_get_config_schema(self, plugin):
        """Test get_config_schema method."""
        schema = plugin.get_config_schema()
        assert schema["type"] == "object"
        assert "api_key" in schema["properties"]

    def test_get_router_returns_none(self, plugin):
        """Test get_router method returns None for simple plugin."""
        assert plugin.get_router() is None

    def test_get_models_returns_empty(self, plugin):
        """Test get_models method returns empty list."""
        assert plugin.get_models() == []

    def test_get_event_handlers_default(self, plugin):
        """Test get_event_handlers returns empty dict by default."""
        assert plugin.get_event_handlers() == {}

    def test_get_services_default(self, plugin):
        """Test get_services returns empty dict by default."""
        assert plugin.get_services() == {}

    def test_has_permission_true(self, plugin):
        """Test has_permission returns True for granted permission."""
        assert plugin.has_permission(Permission.USER_READ) is True
        assert plugin.has_permission(Permission.EVENT_READ) is True

    def test_has_permission_false(self, plugin):
        """Test has_permission returns False for non-granted permission."""
        assert plugin.has_permission(Permission.USER_WRITE_ALL) is False
        assert plugin.has_permission(Permission.EXPENSE_WRITE) is False

    def test_has_all_permissions_true(self, plugin):
        """Test has_all_permissions returns True when all granted."""
        assert plugin.has_all_permissions({Permission.USER_READ}) is True
        assert plugin.has_all_permissions(
            {Permission.USER_READ, Permission.EVENT_READ}
        ) is True

    def test_has_all_permissions_false(self, plugin):
        """Test has_all_permissions returns False when some missing."""
        assert plugin.has_all_permissions(
            {Permission.USER_READ, Permission.EXPENSE_WRITE}
        ) is False

    @pytest.mark.asyncio
    async def test_lifecycle_hooks_are_async(self, plugin):
        """Test that lifecycle hooks are async and can be awaited."""
        # These should not raise
        await plugin.on_install()
        await plugin.on_enable()
        await plugin.on_disable()
        await plugin.on_uninstall()
        await plugin.on_upgrade("0.9.0")
