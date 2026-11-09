# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Integration tests for plugin API endpoints."""

import io
import json
import zipfile
from collections.abc import Generator
from typing import Any

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.plugin_config import PluginConfigModel
from src.plugins.base import BasePlugin, PluginConfig, PluginManifest
from src.plugins.loader import PluginLoader, PluginLoadError
from src.plugins.manifest import PLUGIN_MANIFEST_FILE
from src.plugins.registry import PluginRegistry
from src.plugins.router_proxy import get_plugin_router_manager
from src.services.config_secrets import MASK

MASKED_PLUGIN_ID = "masked-plugin"
BROKEN_PLUGIN_ID = "broken-plugin"
STORED_VALUE = "stored-credential-value"
NEW_VALUE = "replacement-credential"


class SecretSchemaPlugin(BasePlugin):
    """Fixture plugin whose config schema declares a secret field."""

    @classmethod
    def get_config_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "api_token": {"type": "string", "format": "password"},
                "base_url": {"type": "string"},
            },
        }

    def get_router(self) -> APIRouter | None:
        router = APIRouter()

        @router.get("/ping")
        def ping() -> dict[str, str]:
            return {"status": "pong"}

        return router

    def get_models(self) -> list:
        return []


def _load_fixture_plugin(db: Session, settings: dict[str, Any]) -> BasePlugin:
    """Register the fixture plugin in the database and the registry."""
    config = PluginConfigModel(plugin_id=MASKED_PLUGIN_ID, plugin_version="1.0.0")
    config.set_encrypted_settings(settings)
    db.add(config)
    db.commit()
    manifest = PluginManifest(
        id=MASKED_PLUGIN_ID,
        name="Secret Plugin",
        version="1.0.0",
        description="Fixture",
    )
    plugin = SecretSchemaPlugin(manifest, PluginConfig(settings), "/nonexistent")
    PluginRegistry.get_instance()._plugins[MASKED_PLUGIN_ID] = plugin
    return plugin


def _stored_settings(db: Session) -> dict[str, Any]:
    db.expire_all()
    config = (
        db.query(PluginConfigModel)
        .filter(PluginConfigModel.plugin_id == MASKED_PLUGIN_ID)
        .one()
    )
    return config.get_decrypted_settings()


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
        """A registered plugin that is not loaded gets every value masked.

        Without a loaded plugin there is no config schema telling which
        values are secrets, so none is sent back.
        """
        config = PluginConfigModel(
            plugin_id="detail-plugin",
            plugin_version="1.0.0",
        )
        config.set_encrypted_settings({"api_key": "secret"})
        db_session.add(config)
        db_session.commit()

        response = authenticated_client.get("/api/v1/plugins/detail-plugin")
        assert response.status_code == 200
        data = response.json()
        assert data["plugin_id"] == "detail-plugin"
        assert data["plugin_version"] == "1.0.0"
        assert data["settings"] == {"api_key": MASK}
        assert data["secrets_set"] == ["api_key"]
        assert '"secret"' not in response.text


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

    def test_load_failure_hides_raw_error(self, admin_client, monkeypatch):
        """A plugin that fails to load gives a generic message, not its text."""

        async def fail(_self, *_args):
            raise PluginLoadError("secret-path /srv/x exploded")

        monkeypatch.setattr(PluginRegistry, "install_plugin", fail)
        response = admin_client.post(
            "/api/v1/plugins/install",
            files={"file": ("p.zip", b"zip", "application/zip")},
        )
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to load plugin: see server log"
        assert "secret-path" not in response.text


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

    def test_update_settings_of_unloaded_plugin_is_rejected(
        self, admin_client, db_session
    ):
        """Without a loaded plugin (no schema) the stored settings are kept."""
        config = PluginConfigModel(
            plugin_id="settings-plugin",
            plugin_version="1.0.0",
        )
        config.set_encrypted_settings({"api_key": "stored-key", "timeout": 30})
        db_session.add(config)
        db_session.commit()

        response = admin_client.put(
            "/api/v1/plugins/settings-plugin/settings",
            json={"settings": {"api_key": "", "timeout": 60}},
        )
        assert response.status_code == 409

        db_session.expire_all()
        updated_config = (
            db_session.query(PluginConfigModel)
            .filter(PluginConfigModel.plugin_id == "settings-plugin")
            .first()
        )
        assert updated_config.get_decrypted_settings() == {
            "api_key": "stored-key",
            "timeout": 30,
        }


class TestPluginSettingsMasking:
    """Secret plugin settings never leave the server."""

    @pytest.fixture(autouse=True)
    def reset_registry(self) -> Generator[None]:
        """Reset plugin registry around each test."""
        PluginRegistry.reset_instance()
        yield
        PluginRegistry.reset_instance()

    @pytest.fixture
    def secret_plugin(self, client: TestClient, db_session: Session) -> BasePlugin:
        """The fixture plugin, loaded, with a stored token."""
        return _load_fixture_plugin(
            db_session, {"api_token": STORED_VALUE, "base_url": "https://x.test"}
        )

    def test_non_admin_sees_mask(self, authenticated_client, secret_plugin):
        """A regular user gets the mask instead of the stored token."""
        response = authenticated_client.get(f"/api/v1/plugins/{MASKED_PLUGIN_ID}")
        assert response.status_code == 200
        settings = response.json()["settings"]
        assert settings["api_token"] == MASK
        assert settings["base_url"] == "https://x.test"
        assert STORED_VALUE not in response.text

    def test_secrets_set_lists_password_setting(self, admin_client, secret_plugin):
        """The info response names the stored secret, not its value."""
        response = admin_client.get(f"/api/v1/plugins/{MASKED_PLUGIN_ID}")
        assert response.status_code == 200
        assert response.json()["secrets_set"] == ["api_token"]
        assert response.json()["settings"]["api_token"] == MASK
        assert STORED_VALUE not in response.text

    def test_admin_sees_mask(self, admin_client, secret_plugin):
        """Admins get the mask as well."""
        response = admin_client.get(f"/api/v1/plugins/{MASKED_PLUGIN_ID}")
        assert response.status_code == 200
        assert response.json()["settings"]["api_token"] == MASK
        assert STORED_VALUE not in response.text

    def test_put_with_mask_keeps_stored_token(
        self, admin_client, db_session, secret_plugin
    ):
        """Sending the mask back keeps the stored secret."""
        response = admin_client.put(
            f"/api/v1/plugins/{MASKED_PLUGIN_ID}/settings",
            json={"settings": {"api_token": MASK, "base_url": "https://y.test"}},
        )
        assert response.status_code == 200
        assert STORED_VALUE not in response.text
        stored = _stored_settings(db_session)
        assert stored == {"api_token": STORED_VALUE, "base_url": "https://y.test"}
        assert secret_plugin.config.settings["api_token"] == STORED_VALUE

    def test_put_with_new_token_replaces_it(
        self, admin_client, db_session, secret_plugin
    ):
        """A new value replaces the stored secret."""
        response = admin_client.put(
            f"/api/v1/plugins/{MASKED_PLUGIN_ID}/settings",
            json={"settings": {"api_token": NEW_VALUE, "base_url": "https://x"}},
        )
        assert response.status_code == 200
        assert response.json()["settings"]["api_token"] == MASK
        assert _stored_settings(db_session)["api_token"] == NEW_VALUE


class TestDisabledPluginRoutes:
    """Routes of a plugin that is no longer active are gone."""

    @pytest.fixture(autouse=True)
    def reset_registry(self) -> Generator[None]:
        """Reset plugin registry and unmount the fixture router afterwards."""
        PluginRegistry.reset_instance()
        yield
        get_plugin_router_manager().remove_plugin_router(MASKED_PLUGIN_ID)
        PluginRegistry.reset_instance()

    def test_uninstalled_plugin_route_returns_404(self, admin_client, db_session):
        """A mounted plugin route answers until the plugin is removed."""
        plugin = _load_fixture_plugin(db_session, {})
        router = plugin.get_router()
        assert router is not None
        get_plugin_router_manager().add_plugin_router(
            MASKED_PLUGIN_ID, router, admin_client.app
        )
        route = f"/api/v1/plugin/{MASKED_PLUGIN_ID}/ping"
        assert admin_client.get(route).status_code == 200

        response = admin_client.delete(
            f"/api/v1/plugins/{MASKED_PLUGIN_ID}", params={"keep_files": True}
        )
        assert response.status_code == 200

        assert admin_client.get(route).status_code == 404


class FailingInstallPlugin(SecretSchemaPlugin):
    """Fixture plugin that loads but fails in its install hook."""

    async def on_install(self) -> None:
        raise RuntimeError("install hook failed")


class TestFailedDiscoveredInstall:
    """A discovered plugin that fails to start is not left installed."""

    @pytest.fixture(autouse=True)
    def reset_registry(self) -> Generator[None]:
        """Reset plugin registry around each test."""
        PluginRegistry.reset_instance()
        yield
        PluginRegistry.reset_instance()

    @pytest.fixture
    def broken_on_disk(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        """Make the loader discover the broken fixture plugin."""
        manifest = PluginManifest(
            id=BROKEN_PLUGIN_ID, name="Broken", version="1.0.0", description="x"
        )
        monkeypatch.setattr(
            PluginLoader, "discover_plugins", lambda _self: [(tmp_path, manifest)]
        )

    def _assert_not_installed(self, admin_client, db_session) -> None:
        db_session.expire_all()
        record = (
            db_session.query(PluginConfigModel)
            .filter(PluginConfigModel.plugin_id == BROKEN_PLUGIN_ID)
            .first()
        )
        assert record is None
        installed = admin_client.get("/api/v1/plugins").json()["plugins"]
        assert BROKEN_PLUGIN_ID not in [p["plugin_id"] for p in installed]
        discovered = admin_client.get("/api/v1/plugins/discovered").json()
        assert BROKEN_PLUGIN_ID in [p["plugin_id"] for p in discovered["plugins"]]
        assert not PluginRegistry.get_instance().is_plugin_loaded(BROKEN_PLUGIN_ID)

    def test_load_failure_leaves_no_record(
        self, admin_client, db_session, monkeypatch, broken_on_disk
    ):
        """A load error gives 500 and the plugin stays only discovered."""

        def fail(_self, *_args: Any) -> BasePlugin:
            raise PluginLoadError("requires a missing package")

        monkeypatch.setattr(PluginLoader, "load_plugin", fail)
        response = admin_client.post(
            f"/api/v1/plugins/discovered/{BROKEN_PLUGIN_ID}/install"
        )
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to install plugin"
        assert "missing package" not in response.text
        self._assert_not_installed(admin_client, db_session)

    def test_install_hook_failure_unloads_plugin(
        self, admin_client, db_session, monkeypatch, broken_on_disk
    ):
        """A failing on_install unloads the plugin and drops its record."""

        def load(_self, path: Any, manifest: PluginManifest, config: Any):
            return FailingInstallPlugin(manifest, config, str(path))

        monkeypatch.setattr(PluginLoader, "load_plugin", load)
        response = admin_client.post(
            f"/api/v1/plugins/discovered/{BROKEN_PLUGIN_ID}/install"
        )
        assert response.status_code == 500
        self._assert_not_installed(admin_client, db_session)
