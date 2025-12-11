# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Database models for plugin management."""

import uuid as uuid_lib
from typing import Any

from sqlalchemy import Boolean, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.encryption import decrypt_config, encrypt_config
from src.models.base import Base, TimestampMixin


class PluginConfigModel(Base, TimestampMixin):
    """Database model for installed plugin configurations.

    Stores metadata about installed plugins including their enabled state
    and encrypted settings.
    """

    __tablename__ = "plugin_configs"

    id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid_lib.uuid4,
    )
    plugin_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    plugin_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    settings_encrypted: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    migration_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    permissions_granted: Mapped[str | None] = mapped_column(
        Text,  # JSON array of permission strings
        nullable=True,
    )

    def get_decrypted_settings(self) -> dict[str, Any]:
        """Get decrypted plugin settings.

        Returns:
            Decrypted settings dictionary, or empty dict if none
        """
        if not self.settings_encrypted:
            return {}
        try:
            return decrypt_config(self.settings_encrypted)
        except Exception:
            return {}

    def set_encrypted_settings(self, settings: dict[str, Any]) -> None:
        """Encrypt and store plugin settings.

        Args:
            settings: Settings dictionary to encrypt and store
        """
        if settings:
            self.settings_encrypted = encrypt_config(settings)
        else:
            self.settings_encrypted = None


class PluginMigrationHistory(Base):
    """Track which migrations have been run for each plugin.

    This provides an additional audit trail beyond Alembic's version tables.
    """

    __tablename__ = "plugin_migration_history"

    id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid_lib.uuid4,
    )
    plugin_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    revision: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    applied_at: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
