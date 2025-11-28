"""Integration configuration service."""
from typing import Any, Optional

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
    integration_type: Optional[IntegrationType] = None,
    active_only: bool = False,
) -> list[IntegrationConfig]:
    """Get all integration configurations."""
    query = db.query(IntegrationConfig)
    if integration_type:
        query = query.filter(IntegrationConfig.integration_type == integration_type)
    if active_only:
        query = query.filter(IntegrationConfig.is_active == True)  # noqa: E712
    return query.all()


def get_integration_config(db: Session, config_id: str) -> Optional[IntegrationConfig]:
    """Get a single integration configuration by ID."""
    return db.query(IntegrationConfig).filter(IntegrationConfig.id == config_id).first()


def create_integration_config(
    db: Session,
    data: IntegrationConfigCreate,
    user_id: str,
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
        config.config_encrypted = encrypt_config(data.config)
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


def create_provider_instance(config: IntegrationConfig) -> Optional[IntegrationProvider]:
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


def get_active_document_provider(db: Session) -> Optional[IntegrationConfig]:
    """Get the active document provider (Paperless) configuration."""
    configs = get_integration_configs(
        db,
        integration_type=IntegrationType.PAPERLESS,
        active_only=True,
    )
    return configs[0] if configs else None
