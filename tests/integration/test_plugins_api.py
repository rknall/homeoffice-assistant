# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Integration tests for plugin API endpoints."""

import io
import json
import zipfile

import pytest

from src.models.plugin_config import PluginConfigModel
from src.plugins.loader import PLUGIN_MANIFEST_FILE
from src.plugins.registry import PluginRegistry


class TestPluginListEndpoint:
    """Tests for GET /api/v1/plugins endpoint."""

    def test_requires_authentication(self, client):
        """Test that endpoint requires authentication."""
        response = client.get("/api/v1/plugins")
        assert response.status_code == 401

    def test_list_empty(self, authenticated_client):
        """Test listing plugins when none installed."""
        response = authenticated_client.get("/api/v1/plugins")
        assert response.status_code == 200
        data = response.json()
        assert data["plugins"] == []

    def test_list_with_plugins(self, authenticated_client, db_session):
        """Test listing installed plugins."""
        # Add a plugin config to database
        config = PluginConfigModel(
            plugin_id="test-plugin",
            plugin_version="1.0.0",
            is_enabled=True,
        )
        db_session.add(config)
        db_session.commit()

        response = authenticated_client.get("/api/v1/plugins")
        assert response.status_code == 200
        data = response.json()
        assert len(data["plugins"]) == 1
        assert data["plugins"][0]["plugin_id"] == "test-plugin"


class TestPluginDetailEndpoint:
    """Tests for GET /api/v1/plugins/{plugin_id} endpoint."""

    def test_requires_authentication(self, client):
        """Test that endpoint requires authentication."""
        response = client.get("/api/v1/plugins/test-plugin")
        assert response.status_code == 401

    def test_not_found(self, authenticated_client):
        """Test getting non-existent plugin."""
        response = authenticated_client.get("/api/v1/plugins/nonexistent")
        assert response.status_code == 404

    def test_get_plugin_details(self, authenticated_client, db_session):
        """Test getting plugin details."""
        config = PluginConfigModel(
            plugin_id="detail-plugin",
            plugin_version="1.0.0",
            is_enabled=True,
        )
        config.set_encrypted_settings({"api_key": "secret"})
        db_session.add(config)
        db_session.commit()

        response = authenticated_client.get("/api/v1/plugins/detail-plugin")
        assert response.status_code == 200
        data = response.json()
        assert data["plugin_id"] == "detail-plugin"
        assert data["plugin_version"] == "1.0.0"
        assert data["is_enabled"] is True
        assert data["settings"]["api_key"] == "secret"


class TestPluginInstallEndpoint:
    """Tests for POST /api/v1/plugins/install endpoint."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset plugin registry before each test."""
        PluginRegistry.reset_instance()
        yield
        PluginRegistry.reset_instance()

    def create_plugin_zip(self, plugin_id: str, manifest_data: dict) -> bytes:
        """Create a plugin ZIP file in memory."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            zf.writestr(PLUGIN_MANIFEST_FILE, json.dumps(manifest_data))
            zf.writestr(
                "backend/plugin.py",
                """
from src.plugins.base import BasePlugin

class TestPlugin(BasePlugin):
    @classmethod
    def get_config_schema(cls):
        return {}

    def get_router(self):
        return None

    def get_models(self):
        return []
""",
            )
        buffer.seek(0)
        return buffer.read()

    def test_requires_authentication(self, client):
        """Test that endpoint requires authentication."""
        response = client.post(
            "/api/v1/plugins/install",
            files={"file": ("test.zip", b"fake", "application/zip")},
        )
        assert response.status_code == 401

    def test_requires_admin(self, authenticated_client):
        """Test that endpoint requires admin privileges."""
        response = authenticated_client.post(
            "/api/v1/plugins/install",
            files={"file": ("test.zip", b"fake", "application/zip")},
        )
        assert response.status_code == 403

    def test_rejects_non_zip(self, admin_client):
        """Test that non-ZIP files are rejected."""
        response = admin_client.post(
            "/api/v1/plugins/install",
            files={"file": ("test.txt", b"not a zip", "text/plain")},
        )
        assert response.status_code == 400
        assert "ZIP" in response.json()["detail"]

    def test_rejects_invalid_zip(self, admin_client):
        """Test that invalid ZIP files are rejected."""
        response = admin_client.post(
            "/api/v1/plugins/install",
            files={"file": ("test.zip", b"not a valid zip", "application/zip")},
        )
        assert response.status_code == 400


class TestPluginUninstallEndpoint:
    """Tests for DELETE /api/v1/plugins/{plugin_id} endpoint."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset plugin registry before each test."""
        PluginRegistry.reset_instance()
        yield
        PluginRegistry.reset_instance()

    def test_requires_authentication(self, client):
        """Test that endpoint requires authentication."""
        response = client.delete("/api/v1/plugins/test-plugin")
        assert response.status_code == 401

    def test_requires_admin(self, authenticated_client):
        """Test that endpoint requires admin privileges."""
        response = authenticated_client.delete("/api/v1/plugins/test-plugin")
        assert response.status_code == 403

    def test_not_found(self, admin_client):
        """Test uninstalling non-existent plugin."""
        response = admin_client.delete("/api/v1/plugins/nonexistent")
        assert response.status_code == 404


class TestPluginEnableEndpoint:
    """Tests for POST /api/v1/plugins/{plugin_id}/enable endpoint."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset plugin registry before each test."""
        PluginRegistry.reset_instance()
        yield
        PluginRegistry.reset_instance()

    def test_requires_authentication(self, client):
        """Test that endpoint requires authentication."""
        response = client.post("/api/v1/plugins/test-plugin/enable")
        assert response.status_code == 401

    def test_requires_admin(self, authenticated_client):
        """Test that endpoint requires admin privileges."""
        response = authenticated_client.post("/api/v1/plugins/test-plugin/enable")
        assert response.status_code == 403

    def test_not_found(self, admin_client):
        """Test enabling non-existent plugin."""
        response = admin_client.post("/api/v1/plugins/nonexistent/enable")
        assert response.status_code == 404

    def test_enable_already_enabled(self, admin_client, db_session):
        """Test enabling an already enabled plugin."""
        config = PluginConfigModel(
            plugin_id="enabled-plugin",
            plugin_version="1.0.0",
            is_enabled=True,
        )
        db_session.add(config)
        db_session.commit()

        response = admin_client.post("/api/v1/plugins/enabled-plugin/enable")
        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] is True
        assert "already enabled" in data["message"]


class TestPluginDisableEndpoint:
    """Tests for POST /api/v1/plugins/{plugin_id}/disable endpoint."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset plugin registry before each test."""
        PluginRegistry.reset_instance()
        yield
        PluginRegistry.reset_instance()

    def test_requires_authentication(self, client):
        """Test that endpoint requires authentication."""
        response = client.post("/api/v1/plugins/test-plugin/disable")
        assert response.status_code == 401

    def test_requires_admin(self, authenticated_client):
        """Test that endpoint requires admin privileges."""
        response = authenticated_client.post("/api/v1/plugins/test-plugin/disable")
        assert response.status_code == 403

    def test_not_found(self, admin_client):
        """Test disabling non-existent plugin."""
        response = admin_client.post("/api/v1/plugins/nonexistent/disable")
        assert response.status_code == 404

    def test_disable_already_disabled(self, admin_client, db_session):
        """Test disabling an already disabled plugin."""
        config = PluginConfigModel(
            plugin_id="disabled-plugin",
            plugin_version="1.0.0",
            is_enabled=False,
        )
        db_session.add(config)
        db_session.commit()

        response = admin_client.post("/api/v1/plugins/disabled-plugin/disable")
        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] is False
        assert "already disabled" in data["message"]

    def test_disable_enabled_plugin(self, admin_client, db_session):
        """Test disabling an enabled plugin."""
        config = PluginConfigModel(
            plugin_id="to-disable",
            plugin_version="1.0.0",
            is_enabled=True,
        )
        db_session.add(config)
        db_session.commit()

        response = admin_client.post("/api/v1/plugins/to-disable/disable")
        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] is False
        assert data["success"] is True

        # Verify database was updated
        db_session.refresh(config)
        assert config.is_enabled is False


class TestPluginSettingsEndpoint:
    """Tests for PUT /api/v1/plugins/{plugin_id}/settings endpoint."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset plugin registry before each test."""
        PluginRegistry.reset_instance()
        yield
        PluginRegistry.reset_instance()

    def test_requires_authentication(self, client):
        """Test that endpoint requires authentication."""
        response = client.put(
            "/api/v1/plugins/test-plugin/settings",
            json={"settings": {}},
        )
        assert response.status_code == 401

    def test_requires_admin(self, authenticated_client):
        """Test that endpoint requires admin privileges."""
        response = authenticated_client.put(
            "/api/v1/plugins/test-plugin/settings",
            json={"settings": {}},
        )
        assert response.status_code == 403

    def test_not_found(self, admin_client):
        """Test updating settings for non-existent plugin."""
        response = admin_client.put(
            "/api/v1/plugins/nonexistent/settings",
            json={"settings": {"key": "value"}},
        )
        assert response.status_code == 404

    def test_update_settings(self, admin_client, db_session):
        """Test updating plugin settings."""
        config = PluginConfigModel(
            plugin_id="settings-plugin",
            plugin_version="1.0.0",
            is_enabled=True,
        )
        db_session.add(config)
        db_session.commit()

        response = admin_client.put(
            "/api/v1/plugins/settings-plugin/settings",
            json={"settings": {"api_key": "new-key", "timeout": 60}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify settings were saved (need to refresh from DB)
        db_session.expire_all()
        updated_config = (
            db_session.query(PluginConfigModel)
            .filter(PluginConfigModel.plugin_id == "settings-plugin")
            .first()
        )
        settings = updated_config.get_decrypted_settings()
        assert settings["api_key"] == "new-key"
        assert settings["timeout"] == 60
