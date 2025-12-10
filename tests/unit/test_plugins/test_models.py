# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for plugin database models."""

import pytest

from src.models.plugin_config import PluginConfigModel, PluginMigrationHistory


class TestPluginConfigModel:
    """Tests for PluginConfigModel."""

    def test_create_plugin_config(self, db_session):
        """Test creating a plugin config record."""
        config = PluginConfigModel(
            plugin_id="test-plugin",
            plugin_version="1.0.0",
            is_enabled=True,
        )
        db_session.add(config)
        db_session.commit()

        assert config.id is not None
        assert config.plugin_id == "test-plugin"
        assert config.plugin_version == "1.0.0"
        assert config.is_enabled is True
        assert config.created_at is not None
        assert config.updated_at is not None

    def test_plugin_id_unique(self, db_session):
        """Test that plugin_id is unique."""
        config1 = PluginConfigModel(
            plugin_id="unique-plugin",
            plugin_version="1.0.0",
            is_enabled=True,
        )
        db_session.add(config1)
        db_session.commit()

        config2 = PluginConfigModel(
            plugin_id="unique-plugin",
            plugin_version="2.0.0",
            is_enabled=False,
        )
        db_session.add(config2)

        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_set_and_get_encrypted_settings(self, db_session):
        """Test encrypting and decrypting settings."""
        config = PluginConfigModel(
            plugin_id="encrypted-plugin",
            plugin_version="1.0.0",
            is_enabled=True,
        )

        settings = {
            "api_key": "secret-key-123",
            "timeout": 30,
            "nested": {"value": "test"},
        }
        config.set_encrypted_settings(settings)

        db_session.add(config)
        db_session.commit()

        # Retrieve and decrypt
        retrieved = (
            db_session.query(PluginConfigModel)
            .filter(PluginConfigModel.plugin_id == "encrypted-plugin")
            .first()
        )

        decrypted = retrieved.get_decrypted_settings()

        assert decrypted["api_key"] == "secret-key-123"
        assert decrypted["timeout"] == 30
        assert decrypted["nested"]["value"] == "test"

    def test_get_decrypted_settings_empty(self, db_session):
        """Test getting settings when none are set."""
        config = PluginConfigModel(
            plugin_id="empty-settings",
            plugin_version="1.0.0",
            is_enabled=True,
        )
        db_session.add(config)
        db_session.commit()

        settings = config.get_decrypted_settings()
        assert settings == {}

    def test_set_empty_settings(self, db_session):
        """Test setting empty settings."""
        config = PluginConfigModel(
            plugin_id="empty-set",
            plugin_version="1.0.0",
            is_enabled=True,
        )
        config.set_encrypted_settings({})

        db_session.add(config)
        db_session.commit()

        settings = config.get_decrypted_settings()
        assert settings == {}

    def test_update_settings(self, db_session):
        """Test updating settings."""
        config = PluginConfigModel(
            plugin_id="update-settings",
            plugin_version="1.0.0",
            is_enabled=True,
        )
        config.set_encrypted_settings({"key1": "value1"})
        db_session.add(config)
        db_session.commit()

        # Update settings
        config.set_encrypted_settings({"key2": "value2"})
        db_session.commit()

        settings = config.get_decrypted_settings()
        assert "key1" not in settings
        assert settings["key2"] == "value2"

    def test_default_values(self, db_session):
        """Test default values for optional fields."""
        config = PluginConfigModel(
            plugin_id="defaults",
            plugin_version="1.0.0",
        )
        db_session.add(config)
        db_session.commit()

        assert config.is_enabled is True
        assert config.settings_encrypted is None
        assert config.migration_version is None
        assert config.permissions_granted is None

    def test_migration_version(self, db_session):
        """Test setting migration version."""
        config = PluginConfigModel(
            plugin_id="with-migration",
            plugin_version="1.0.0",
            is_enabled=True,
            migration_version="abc123",
        )
        db_session.add(config)
        db_session.commit()

        retrieved = (
            db_session.query(PluginConfigModel)
            .filter(PluginConfigModel.plugin_id == "with-migration")
            .first()
        )
        assert retrieved.migration_version == "abc123"

    def test_permissions_granted(self, db_session):
        """Test storing granted permissions."""
        config = PluginConfigModel(
            plugin_id="with-permissions",
            plugin_version="1.0.0",
            is_enabled=True,
            permissions_granted="user.read,event.write",
        )
        db_session.add(config)
        db_session.commit()

        retrieved = (
            db_session.query(PluginConfigModel)
            .filter(PluginConfigModel.plugin_id == "with-permissions")
            .first()
        )
        assert "user.read" in retrieved.permissions_granted
        assert "event.write" in retrieved.permissions_granted


class TestPluginMigrationHistory:
    """Tests for PluginMigrationHistory model."""

    def test_create_migration_history(self, db_session):
        """Test creating a migration history record."""
        history = PluginMigrationHistory(
            plugin_id="test-plugin",
            revision="abc123def456",
            applied_at="2025-01-15T10:30:00",
        )
        db_session.add(history)
        db_session.commit()

        assert history.id is not None
        assert history.plugin_id == "test-plugin"
        assert history.revision == "abc123def456"
        assert history.applied_at == "2025-01-15T10:30:00"

    def test_multiple_migrations_same_plugin(self, db_session):
        """Test recording multiple migrations for same plugin."""
        for i, revision in enumerate(["rev1", "rev2", "rev3"]):
            history = PluginMigrationHistory(
                plugin_id="multi-migration",
                revision=revision,
                applied_at=f"2025-01-{15+i}T10:30:00",
            )
            db_session.add(history)

        db_session.commit()

        histories = (
            db_session.query(PluginMigrationHistory)
            .filter(PluginMigrationHistory.plugin_id == "multi-migration")
            .all()
        )
        assert len(histories) == 3

    def test_delete_migration_history_for_plugin(self, db_session):
        """Test deleting all migration history for a plugin."""
        # Create histories for two plugins
        for plugin_id in ["plugin-a", "plugin-b"]:
            history = PluginMigrationHistory(
                plugin_id=plugin_id,
                revision="rev1",
                applied_at="2025-01-15T10:30:00",
            )
            db_session.add(history)

        db_session.commit()

        # Delete plugin-a's history
        db_session.query(PluginMigrationHistory).filter(
            PluginMigrationHistory.plugin_id == "plugin-a"
        ).delete()
        db_session.commit()

        # plugin-a should have no history
        plugin_a_count = (
            db_session.query(PluginMigrationHistory)
            .filter(PluginMigrationHistory.plugin_id == "plugin-a")
            .count()
        )
        assert plugin_a_count == 0

        # plugin-b should still have history
        plugin_b_count = (
            db_session.query(PluginMigrationHistory)
            .filter(PluginMigrationHistory.plugin_id == "plugin-b")
            .count()
        )
        assert plugin_b_count == 1
