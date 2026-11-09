# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Integration configuration service."""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.orm import Session

from src.encryption import decrypt_config, encrypt_config
from src.integrations.base import (
    DocumentProvider,
    EmailProvider,
    ImageSearchProvider,
    IntegrationProvider,
    LlmProvider,
    PhotoProvider,
)
from src.integrations.registry import IntegrationRegistry
from src.models import IntegrationConfig
from src.models.enums import IntegrationType
from src.schemas.integration import (
    IntegrationConfigCreate,
    IntegrationConfigUpdate,
    LlmModelsRequest,
)
from src.services import config_secrets

# Provider interface every integration type must implement
_PROVIDER_INTERFACES: dict[IntegrationType, type[IntegrationProvider]] = {
    IntegrationType.PAPERLESS: DocumentProvider,
    IntegrationType.IMMICH: PhotoProvider,
    IntegrationType.SMTP: EmailProvider,
    IntegrationType.UNSPLASH: ImageSearchProvider,
    IntegrationType.LLM: LlmProvider,
}

_TYPE_LABELS: dict[IntegrationType, str] = {
    IntegrationType.PAPERLESS: "Paperless",
    IntegrationType.IMMICH: "Immich",
    IntegrationType.SMTP: "SMTP",
    IntegrationType.UNSPLASH: "Unsplash",
    IntegrationType.LLM: "LLM",
}


class ProviderError(Exception):
    """A provider could not be opened.

    Attributes:
        status_code: The HTTP status the API layer reports for this error.
        detail: The message shown to the caller.
    """

    status_code = 500

    def __init__(self, detail: str) -> None:
        """Store the caller-facing message."""
        super().__init__(detail)
        self.detail = detail


class IntegrationNotFoundError(ProviderError):
    """The requested integration does not exist."""

    status_code = 404


class IntegrationTypeMismatchError(ProviderError):
    """The integration is not of the type the operation needs."""

    status_code = 400


class NoActiveIntegrationError(ProviderError):
    """No active integration of the needed type is configured."""

    status_code = 400


class ProviderUnavailableError(ProviderError):
    """The provider instance could not be created."""

    status_code = 500


def list_integration_types() -> list[dict[str, Any]]:
    """List all available integration types with their schemas."""
    return IntegrationRegistry.get_all_type_info()


def get_config_schema(integration_type: IntegrationType) -> dict[str, Any]:
    """Return the config schema of an integration type's provider.

    Args:
        integration_type: The integration type.

    Returns:
        The provider's JSON schema, or an empty dict for an unknown type.
    """
    provider_class = IntegrationRegistry.get_provider(integration_type.value)
    return provider_class.get_config_schema() if provider_class else {}


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
        # Secrets left blank by the edit form keep their stored value
        new_config = config_secrets.merge(
            get_decrypted_config(config),
            data.config,
            get_config_schema(config.integration_type),
        )
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


@asynccontextmanager
async def _open(
    config: IntegrationConfig, expected_type: IntegrationType
) -> AsyncIterator[Any]:
    """Create the provider of a config and close it when the block ends."""
    provider = create_provider_instance(config)
    interface = _PROVIDER_INTERFACES[expected_type]
    if provider is None or not isinstance(provider, interface):
        raise ProviderUnavailableError("Failed to create provider instance")
    try:
        yield provider
    finally:
        await provider.close()


@asynccontextmanager
async def open_provider(
    db: Session, config_id: uuid.UUID, expected_type: IntegrationType
) -> AsyncIterator[Any]:
    """Open the provider of one integration and close it afterwards.

    Args:
        db: Database session.
        config_id: The integration to open.
        expected_type: The type the integration must have.

    Yields:
        The provider instance, which implements the type's provider interface.

    Raises:
        IntegrationNotFoundError: If the integration does not exist.
        IntegrationTypeMismatchError: If it has another type.
        ProviderUnavailableError: If the provider cannot be created.
    """
    config = get_integration_config(db, config_id)
    if config is None:
        raise IntegrationNotFoundError("Integration not found")
    if config.integration_type != expected_type:
        label = _TYPE_LABELS[expected_type]
        raise IntegrationTypeMismatchError(
            f"This endpoint is only available for {label} integrations"
        )
    async with _open(config, expected_type) as provider:
        yield provider


@asynccontextmanager
async def open_active_provider(
    db: Session, integration_type: IntegrationType
) -> AsyncIterator[Any]:
    """Open the provider of the first active integration of a type.

    Args:
        db: Database session.
        integration_type: The integration type to use.

    Yields:
        The provider instance, which implements the type's provider interface.

    Raises:
        NoActiveIntegrationError: If no active integration of the type exists.
        ProviderUnavailableError: If the provider cannot be created.
    """
    configs = get_integration_configs(db, integration_type, active_only=True)
    if not configs:
        label = _TYPE_LABELS[integration_type]
        raise NoActiveIntegrationError(f"No active {label} integration configured")
    async with _open(configs[0], integration_type) as provider:
        yield provider


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
    """Get the decrypted configuration with its secret fields masked."""
    return config_secrets.mask(
        get_decrypted_config(config), get_config_schema(config.integration_type)
    )


def get_secrets_set(config: IntegrationConfig) -> list[str]:
    """Get the names of the secret fields that hold a stored value."""
    return config_secrets.set_secret_fields(
        get_decrypted_config(config), get_config_schema(config.integration_type)
    )


def _normalize_base_url(base_url: Any) -> str:
    """Normalize a base URL the way the LLM provider uses it."""
    return str(base_url or "").strip().rstrip("/")


def resolve_llm_models_config(db: Session, data: LlmModelsRequest) -> dict[str, Any]:
    """Build the provider config for listing the models of an LLM endpoint.

    The edit form sends saved secrets back blank. They are filled in from the
    stored integration only when the request targets the stored ``base_url``,
    so stored credentials are never sent to a different server.

    Args:
        db: Database session.
        data: Form values of the model listing request.

    Returns:
        The config to create the LLM provider with.
    """
    config = data.model_dump(exclude={"config_id"})
    if data.config_id is None:
        return config
    stored = get_integration_config(db, data.config_id)
    if stored is None or stored.integration_type != IntegrationType.LLM:
        return config
    saved = get_decrypted_config(stored)
    if _normalize_base_url(saved.get("base_url")) != _normalize_base_url(
        config["base_url"]
    ):
        return config
    return config_secrets.merge(saved, config, get_config_schema(IntegrationType.LLM))
