# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for plugin loader."""

import json
import zipfile
from pathlib import Path

import pytest

from src.plugins.base import Permission, PluginCapability, PluginConfig, PluginManifest
from src.plugins.loader import (
    PLUGIN_MANIFEST_FILE,
    PluginLoader,
    PluginLoadError,
    PluginValidationError,
    parse_manifest,
)


class TestParseManifest:
    """Tests for parse_manifest function."""

    @pytest.fixture
    def manifest_dir(self, tmp_path):
        """Create a temporary directory for manifest files."""
        return tmp_path

    def write_manifest(self, path: Path, data: dict):
        """Helper to write manifest JSON."""
        manifest_path = path / PLUGIN_MANIFEST_FILE
        manifest_path.write_text(json.dumps(data))
        return manifest_path

    def test_parse_minimal_manifest(self, manifest_dir):
        """Test parsing a minimal valid manifest."""
        manifest_path = self.write_manifest(manifest_dir, {
            "id": "test-plugin",
            "name": "Test Plugin",
            "version": "1.0.0",
            "description": "A test plugin",
        })

        manifest = parse_manifest(manifest_path)

        assert manifest.id == "test-plugin"
        assert manifest.name == "Test Plugin"
        assert manifest.version == "1.0.0"
        assert manifest.description == "A test plugin"

    def test_parse_full_manifest(self, manifest_dir):
        """Test parsing a fully specified manifest."""
        manifest_path = self.write_manifest(manifest_dir, {
            "id": "full-plugin",
            "name": "Full Plugin",
            "version": "2.0.0",
            "description": "A full plugin",
            "author": "Test Author",
            "homepage": "https://example.com",
            "license": "MIT",
            "min_host_version": "0.2.0",
            "max_host_version": "1.0.0",
            "capabilities": {"backend": True, "frontend": True, "config": False},
            "permissions": ["user.read", "event.write"],
            "dependencies": ["other-plugin"],
        })

        manifest = parse_manifest(manifest_path)

        assert manifest.author == "Test Author"
        assert manifest.homepage == "https://example.com"
        assert manifest.license == "MIT"
        assert manifest.min_host_version == "0.2.0"
        assert manifest.max_host_version == "1.0.0"
        assert PluginCapability.BACKEND in manifest.capabilities
        assert PluginCapability.FRONTEND in manifest.capabilities
        assert PluginCapability.CONFIG not in manifest.capabilities
        assert Permission.USER_READ in manifest.permissions
        assert Permission.EVENT_WRITE in manifest.permissions
        assert "other-plugin" in manifest.dependencies

    def test_parse_capabilities_as_list(self, manifest_dir):
        """Test parsing capabilities in list format."""
        manifest_path = self.write_manifest(manifest_dir, {
            "id": "test-plugin",
            "name": "Test",
            "version": "1.0.0",
            "description": "Test",
            "capabilities": ["backend", "frontend"],
        })

        manifest = parse_manifest(manifest_path)

        assert PluginCapability.BACKEND in manifest.capabilities
        assert PluginCapability.FRONTEND in manifest.capabilities

    def test_parse_missing_required_field(self, manifest_dir):
        """Test that missing required fields raise error."""
        manifest_path = self.write_manifest(manifest_dir, {
            "id": "test-plugin",
            "name": "Test",
            # Missing version and description
        })

        with pytest.raises(PluginValidationError, match="Missing required field"):
            parse_manifest(manifest_path)

    def test_parse_empty_plugin_id(self, manifest_dir):
        """Test that empty plugin ID raises error."""
        manifest_path = self.write_manifest(manifest_dir, {
            "id": "",
            "name": "Test",
            "version": "1.0.0",
            "description": "Test",
        })

        with pytest.raises(PluginValidationError, match="cannot be empty"):
            parse_manifest(manifest_path)

    def test_parse_invalid_plugin_id(self, manifest_dir):
        """Test that invalid plugin ID raises error."""
        manifest_path = self.write_manifest(manifest_dir, {
            "id": "invalid plugin id!",
            "name": "Test",
            "version": "1.0.0",
            "description": "Test",
        })

        with pytest.raises(PluginValidationError, match="Invalid plugin ID"):
            parse_manifest(manifest_path)

    def test_parse_valid_plugin_id_formats(self, manifest_dir):
        """Test that valid plugin ID formats are accepted."""
        for plugin_id in ["my-plugin", "my_plugin", "MyPlugin123", "plugin-123_test"]:
            manifest_path = self.write_manifest(manifest_dir, {
                "id": plugin_id,
                "name": "Test",
                "version": "1.0.0",
                "description": "Test",
            })
            manifest = parse_manifest(manifest_path)
            assert manifest.id == plugin_id

    def test_parse_invalid_json(self, manifest_dir):
        """Test that invalid JSON raises error."""
        manifest_path = manifest_dir / PLUGIN_MANIFEST_FILE
        manifest_path.write_text("not valid json {")

        with pytest.raises(PluginValidationError, match="Invalid JSON"):
            parse_manifest(manifest_path)

    def test_parse_nonexistent_file(self, manifest_dir):
        """Test that nonexistent file raises error."""
        manifest_path = manifest_dir / PLUGIN_MANIFEST_FILE

        with pytest.raises(PluginValidationError, match="Could not read"):
            parse_manifest(manifest_path)

    def test_parse_unknown_capability_ignored(self, manifest_dir):
        """Test that unknown capabilities are ignored but valid ones kept."""
        manifest_path = self.write_manifest(manifest_dir, {
            "id": "test-plugin",
            "name": "Test",
            "version": "1.0.0",
            "description": "Test",
            "capabilities": {"backend": True, "unknown_cap": True},
        })

        manifest = parse_manifest(manifest_path)

        # Valid capability should be present
        assert PluginCapability.BACKEND in manifest.capabilities
        # Unknown capability should be ignored (only valid ones in set)
        assert len(manifest.capabilities) == 1

    def test_parse_unknown_permission_ignored(self, manifest_dir):
        """Test that unknown permissions are ignored but valid ones kept."""
        manifest_path = self.write_manifest(manifest_dir, {
            "id": "test-plugin",
            "name": "Test",
            "version": "1.0.0",
            "description": "Test",
            "permissions": ["user.read", "unknown.permission"],
        })

        manifest = parse_manifest(manifest_path)

        # Valid permission should be present
        assert Permission.USER_READ in manifest.permissions
        # Unknown permission should be ignored (only valid ones in set)
        assert len(manifest.permissions) == 1


class TestPluginLoader:
    """Tests for PluginLoader class."""

    @pytest.fixture
    def plugins_dir(self, tmp_path):
        """Create a temporary plugins directory."""
        plugins = tmp_path / "plugins"
        plugins.mkdir()
        return plugins

    @pytest.fixture
    def loader(self, plugins_dir):
        """Create a PluginLoader instance."""
        return PluginLoader(plugins_dir)

    def create_plugin_structure(
        self, plugins_dir: Path, plugin_id: str, manifest_data: dict
    ) -> Path:
        """Helper to create a plugin directory structure."""
        plugin_dir = plugins_dir / plugin_id
        plugin_dir.mkdir(parents=True)

        # Write manifest
        manifest_path = plugin_dir / PLUGIN_MANIFEST_FILE
        manifest_path.write_text(json.dumps(manifest_data))

        # Create backend directory with plugin.py
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

    def test_loader_creates_plugins_dir(self, tmp_path):
        """Test that loader creates plugins directory if missing."""
        plugins_dir = tmp_path / "new_plugins"
        assert not plugins_dir.exists()

        PluginLoader(plugins_dir)

        assert plugins_dir.exists()

    def test_discover_plugins_empty(self, loader, plugins_dir):
        """Test discovering plugins in empty directory."""
        discovered = loader.discover_plugins()
        assert len(discovered) == 0

    def test_discover_plugins_with_plugin(self, loader, plugins_dir):
        """Test discovering a valid plugin."""
        self.create_plugin_structure(plugins_dir, "test-plugin", {
            "id": "test-plugin",
            "name": "Test Plugin",
            "version": "1.0.0",
            "description": "A test plugin",
        })

        discovered = loader.discover_plugins()

        assert len(discovered) == 1
        path, manifest = discovered[0]
        assert manifest.id == "test-plugin"
        assert path == plugins_dir / "test-plugin"

    def test_discover_plugins_skips_hidden(self, loader, plugins_dir):
        """Test that discovery skips hidden directories."""
        # Create hidden directory with valid plugin
        hidden_dir = plugins_dir / ".hidden-plugin"
        hidden_dir.mkdir()
        (hidden_dir / PLUGIN_MANIFEST_FILE).write_text(json.dumps({
            "id": "hidden",
            "name": "Hidden",
            "version": "1.0.0",
            "description": "Hidden",
        }))

        discovered = loader.discover_plugins()
        assert len(discovered) == 0

    def test_discover_plugins_skips_pycache(self, loader, plugins_dir):
        """Test that discovery skips __pycache__ directories."""
        pycache = plugins_dir / "__pycache__"
        pycache.mkdir()

        discovered = loader.discover_plugins()
        assert len(discovered) == 0

    def test_discover_plugins_skips_no_manifest(self, loader, plugins_dir):
        """Test that discovery skips directories without manifest."""
        (plugins_dir / "no-manifest").mkdir()

        discovered = loader.discover_plugins()

        # Directory without manifest should be skipped
        assert len(discovered) == 0

    def test_get_plugin_path_exists(self, loader, plugins_dir):
        """Test getting path for existing plugin."""
        self.create_plugin_structure(plugins_dir, "test-plugin", {
            "id": "test-plugin",
            "name": "Test",
            "version": "1.0.0",
            "description": "Test",
        })

        path = loader.get_plugin_path("test-plugin")

        assert path == plugins_dir / "test-plugin"

    def test_get_plugin_path_not_exists(self, loader):
        """Test getting path for non-existent plugin."""
        path = loader.get_plugin_path("nonexistent")
        assert path is None

    def test_has_frontend(self, loader, plugins_dir):
        """Test checking for frontend assets."""
        plugin_dir = self.create_plugin_structure(plugins_dir, "test-plugin", {
            "id": "test-plugin",
            "name": "Test",
            "version": "1.0.0",
            "description": "Test",
        })

        # Initially no frontend
        assert loader.has_frontend("test-plugin") is False

        # Add frontend
        frontend_dir = plugin_dir / "frontend"
        frontend_dir.mkdir()
        (frontend_dir / "index.js").write_text("// Frontend code")

        assert loader.has_frontend("test-plugin") is True

    def test_has_backend(self, loader, plugins_dir):
        """Test checking for backend code."""
        self.create_plugin_structure(plugins_dir, "test-plugin", {
            "id": "test-plugin",
            "name": "Test",
            "version": "1.0.0",
            "description": "Test",
        })

        assert loader.has_backend("test-plugin") is True

    def test_has_backend_no_plugin_py(self, loader, plugins_dir):
        """Test has_backend when plugin.py is missing."""
        plugin_dir = plugins_dir / "no-backend"
        plugin_dir.mkdir()
        (plugin_dir / PLUGIN_MANIFEST_FILE).write_text(json.dumps({
            "id": "no-backend",
            "name": "No Backend",
            "version": "1.0.0",
            "description": "Test",
        }))

        assert loader.has_backend("no-backend") is False

    def test_uninstall_removes_directory(self, loader, plugins_dir):
        """Test that uninstall removes plugin directory."""
        self.create_plugin_structure(plugins_dir, "test-plugin", {
            "id": "test-plugin",
            "name": "Test",
            "version": "1.0.0",
            "description": "Test",
        })

        assert (plugins_dir / "test-plugin").exists()

        loader.uninstall("test-plugin")

        assert not (plugins_dir / "test-plugin").exists()

    def test_uninstall_nonexistent(self, loader, plugins_dir):
        """Test uninstalling non-existent plugin doesn't raise."""
        # Should not raise an error
        loader.uninstall("nonexistent")
        # Directory should still not exist
        assert not (plugins_dir / "nonexistent").exists()


class TestPluginLoaderZipInstall:
    """Tests for ZIP installation functionality."""

    @pytest.fixture
    def plugins_dir(self, tmp_path):
        """Create a temporary plugins directory."""
        plugins = tmp_path / "plugins"
        plugins.mkdir()
        return plugins

    @pytest.fixture
    def loader(self, plugins_dir):
        """Create a PluginLoader instance."""
        return PluginLoader(plugins_dir)

    def create_plugin_zip(self, tmp_path: Path, plugin_id: str, manifest_data: dict):
        """Helper to create a plugin ZIP file."""
        zip_path = tmp_path / f"{plugin_id}.zip"

        with zipfile.ZipFile(zip_path, "w") as zf:
            # Add manifest
            zf.writestr(PLUGIN_MANIFEST_FILE, json.dumps(manifest_data))

            # Add backend plugin.py
            zf.writestr("backend/plugin.py", """
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

        return zip_path

    def test_install_from_zip(self, loader, plugins_dir, tmp_path):
        """Test installing a plugin from ZIP."""
        zip_path = self.create_plugin_zip(tmp_path, "zip-plugin", {
            "id": "zip-plugin",
            "name": "ZIP Plugin",
            "version": "1.0.0",
            "description": "Installed from ZIP",
        })

        manifest = loader.install_from_zip(zip_path)

        assert manifest.id == "zip-plugin"
        assert (plugins_dir / "zip-plugin").exists()
        assert (plugins_dir / "zip-plugin" / PLUGIN_MANIFEST_FILE).exists()

    def test_install_from_zip_subdirectory(self, loader, plugins_dir, tmp_path):
        """Test installing ZIP where content is in subdirectory."""
        zip_path = tmp_path / "subdir-plugin.zip"

        with zipfile.ZipFile(zip_path, "w") as zf:
            # Content in subdirectory
            zf.writestr("subdir-plugin/" + PLUGIN_MANIFEST_FILE, json.dumps({
                "id": "subdir-plugin",
                "name": "Subdir Plugin",
                "version": "1.0.0",
                "description": "In subdirectory",
            }))
            zf.writestr("subdir-plugin/backend/plugin.py", "# Plugin code")

        manifest = loader.install_from_zip(zip_path)

        assert manifest.id == "subdir-plugin"
        assert (plugins_dir / "subdir-plugin").exists()

    def test_install_from_zip_not_found(self, loader, tmp_path):
        """Test installing from non-existent ZIP."""
        zip_path = tmp_path / "nonexistent.zip"

        with pytest.raises(PluginValidationError, match="not found"):
            loader.install_from_zip(zip_path)

    def test_install_from_zip_invalid_file(self, loader, tmp_path):
        """Test installing from invalid ZIP file."""
        not_zip = tmp_path / "not_a_zip.zip"
        not_zip.write_text("This is not a ZIP file")

        with pytest.raises(PluginValidationError, match="Not a valid ZIP"):
            loader.install_from_zip(not_zip)

    def test_install_from_zip_no_manifest(self, loader, tmp_path):
        """Test installing ZIP without manifest."""
        zip_path = tmp_path / "no-manifest.zip"

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("backend/plugin.py", "# No manifest")

        with pytest.raises(PluginValidationError, match=r"No .* found"):
            loader.install_from_zip(zip_path)

    def test_install_from_zip_already_installed(self, loader, plugins_dir, tmp_path):
        """Test installing plugin that already exists."""
        # First install
        zip_path = self.create_plugin_zip(tmp_path, "dup-plugin", {
            "id": "dup-plugin",
            "name": "Dup Plugin",
            "version": "1.0.0",
            "description": "Test",
        })
        loader.install_from_zip(zip_path)

        # Try to install again
        with pytest.raises(PluginValidationError, match="already installed"):
            loader.install_from_zip(zip_path)

    def test_install_from_zip_with_dangerous_permissions(
        self, loader, plugins_dir, tmp_path
    ):
        """Test that plugins with dangerous permissions can still be installed."""
        zip_path = self.create_plugin_zip(tmp_path, "dangerous-plugin", {
            "id": "dangerous-plugin",
            "name": "Dangerous Plugin",
            "version": "1.0.0",
            "description": "Has dangerous permissions",
            "permissions": ["user.write.all", "system.settings.write"],
        })

        manifest = loader.install_from_zip(zip_path)

        # Plugin should still be installed
        assert manifest.id == "dangerous-plugin"
        assert (plugins_dir / "dangerous-plugin").exists()
        # Dangerous permissions should be in manifest
        assert Permission.USER_WRITE_ALL in manifest.permissions
        assert Permission.SYSTEM_SETTINGS_WRITE in manifest.permissions


class TestLoadPluginClass:
    """Tests for loading plugin classes."""

    @pytest.fixture
    def plugins_dir(self, tmp_path):
        """Create a temporary plugins directory."""
        plugins = tmp_path / "plugins"
        plugins.mkdir()
        return plugins

    @pytest.fixture
    def loader(self, plugins_dir):
        """Create a PluginLoader instance."""
        return PluginLoader(plugins_dir)

    def test_load_plugin_no_module(self, loader, plugins_dir):
        """Test loading plugin without plugin.py raises error."""
        plugin_dir = plugins_dir / "no-module"
        plugin_dir.mkdir()
        (plugin_dir / "backend").mkdir()
        # No plugin.py created

        manifest = PluginManifest(
            id="no-module",
            name="No Module",
            version="1.0.0",
            description="Test",
        )

        with pytest.raises(PluginLoadError, match="not found"):
            loader.load_plugin(plugin_dir, manifest, PluginConfig())
