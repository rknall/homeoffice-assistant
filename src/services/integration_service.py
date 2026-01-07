# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Integration configuration service."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from src.encryption import decrypt_config, encrypt_config
from src.integrations.base import IntegrationProvider
from src.integrations.registry import IntegrationRegistry
from src.models import IntegrationConfig
from src.models.enums import IntegrationType
from src.schemas.integration import IntegrationConfigCreate, IntegrationConfigUpdate


def list_integration_types() -> list[dict[str, Any]]:
    """List all available integration types with their schemas."""
    return IntegrationRegistry.get_all_type_info()


def get_integration_configs(
    db: Session,
    integration_type: IntegrationType | None = None,
    active_only: bool = False,
) -> list[IntegrationConfig]:
    """Get all integration configurations."""
    query = db.query(IntegrationConfig)
    if integration_type:
        query = query.filter(IntegrationConfig.integration_type == integration_type)
    if active_only:
        query = query.filter(IntegrationConfig.is_active)
    return query.all()


def get_integration_config(
    db: Session, config_id: uuid.UUID
) -> IntegrationConfig | None:
    """Get a single integration configuration by ID."""
    return db.query(IntegrationConfig).filter(IntegrationConfig.id == config_id).first()


def create_integration_config(
    db: Session,
    data: IntegrationConfigCreate,
    user_id: uuid.UUID,
) -> IntegrationConfig:
    """Create a new integration configuration."""
    config = IntegrationConfig(
        integration_type=data.integration_type,
        name=data.name,
        config_encrypted=encrypt_config(data.config),
        is_active=True,
        created_by=user_id,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def update_integration_config(
    db: Session,
    config: IntegrationConfig,
    data: IntegrationConfigUpdate,
) -> IntegrationConfig:
    """Update an existing integration configuration."""
    if data.name is not None:
        config.name = data.name
    if data.config is not None:
        # Merge with existing config - preserve secrets if not provided
        existing_config = get_decrypted_config(config)
        new_config = data.config.copy()
        sensitive_fields = ["token", "password", "api_key", "secret"]
        for field in sensitive_fields:
            # If new value is empty but old value exists, keep the old value
            if existing_config.get(field) and (
                field not in new_config or not new_config.get(field)
            ):
                new_config[field] = existing_config[field]
        config.config_encrypted = encrypt_config(new_config)
    if data.is_active is not None:
        config.is_active = data.is_active
    db.commit()
    db.refresh(config)
    return config


def delete_integration_config(db: Session, config: IntegrationConfig) -> None:
    """Delete an integration configuration."""
    db.delete(config)
    db.commit()


def get_decrypted_config(config: IntegrationConfig) -> dict[str, Any]:
    """Get the decrypted configuration for an integration."""
    return decrypt_config(config.config_encrypted)


def create_provider_instance(config: IntegrationConfig) -> IntegrationProvider | None:
    """Create a provider instance from an integration configuration."""
    decrypted = get_decrypted_config(config)
    return IntegrationRegistry.create_provider(config.integration_type.value, decrypted)


async def test_integration_connection(config: IntegrationConfig) -> tuple[bool, str]:
    """Test connectivity for an integration configuration."""
    provider = create_provider_instance(config)
    if provider is None:
        return False, f"Unknown integration type: {config.integration_type}"
    try:
        success, message = await provider.health_check()
        return success, message
    finally:
        await provider.close()


def get_active_document_provider(db: Session) -> IntegrationConfig | None:
    """Get the active document provider (Paperless) configuration."""
    configs = get_integration_configs(
        db,
        integration_type=IntegrationType.PAPERLESS,
        active_only=True,
    )
    return configs[0] if configs else None


def get_masked_config(config: IntegrationConfig) -> dict[str, Any]:
    """Get the decrypted configuration with sensitive fields masked."""
    decrypted = get_decrypted_config(config)
    # Mask password fields
    sensitive_fields = ["token", "password", "api_key", "secret"]
    for field in sensitive_fields:
        if decrypted.get(field):
            decrypted[field] = ""  # Empty string indicates masked
    return decrypted
