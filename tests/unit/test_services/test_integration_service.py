# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for integration_service."""

from unittest.mock import AsyncMock

import pytest

from src.models import IntegrationConfig, User
from src.models.enums import IntegrationType
from src.schemas.integration import IntegrationConfigCreate, IntegrationConfigUpdate
from src.security import get_password_hash
from src.services import integration_service


def create_user(db_session) -> User:
    user = User(
        username="integration",
        email="integration@example.com",
        hashed_password=get_password_hash("Secret123!"),
        is_admin=True,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_config(db_session, user_id: str) -> IntegrationConfig:
    data = IntegrationConfigCreate(
        integration_type=IntegrationType.PAPERLESS,
        name="Paperless",
        config={"token": "secret", "url": "https://example.com"},
    )
    return integration_service.create_integration_config(db_session, data, user_id)


def test_list_integration_types(monkeypatch):
    monkeypatch.setattr(
        integration_service.IntegrationRegistry,
        "get_all_type_info",
        lambda: [{"type": "paperless"}],
    )
    assert integration_service.list_integration_types() == [{"type": "paperless"}]


def test_config_crud_operations(db_session):
    user = create_user(db_session)
    config = create_config(db_session, user.id)

    fetched = integration_service.get_integration_config(db_session, config.id)
    assert fetched == config

    all_configs = integration_service.get_integration_configs(db_session)
    assert len(all_configs) == 1

    filtered = integration_service.get_integration_configs(
        db_session, integration_type=IntegrationType.PAPERLESS, active_only=True
    )
    assert filtered == [config]

    update = IntegrationConfigUpdate(
        name="Updated",
        config={"url": "https://new.example.com", "token": ""},
        is_active=False,
    )
    updated = integration_service.update_integration_config(
        db_session, config, update
    )

    assert updated.name == "Updated"
    assert updated.is_active is False
    decrypted = integration_service.get_decrypted_config(updated)
    assert decrypted["token"] == "secret"  # preserved from old config
    assert decrypted["url"] == "https://new.example.com"

    integration_service.delete_integration_config(db_session, updated)
    assert integration_service.get_integration_config(db_session, updated.id) is None


def test_provider_helpers(monkeypatch, db_session):
    provider = object()
    monkeypatch.setattr(
        integration_service.IntegrationRegistry,
        "create_provider",
        lambda _type, _config: provider,
    )
    user = create_user(db_session)
    config = create_config(db_session, user.id)
    assert integration_service.create_provider_instance(config) is provider


@pytest.mark.asyncio
async def test_test_integration_connection(monkeypatch, db_session):
    user = create_user(db_session)
    config = create_config(db_session, user.id)
    provider = AsyncMock()
    provider.health_check.return_value = (True, "ok")
    provider.close = AsyncMock()

    monkeypatch.setattr(
        integration_service,
        "create_provider_instance",
        lambda conf: provider,
    )

    success, message = await integration_service.test_integration_connection(config)
    assert success is True
    assert message == "ok"
    provider.close.assert_awaited()


def test_get_active_document_provider(db_session):
    user = create_user(db_session)
    config = create_config(db_session, user.id)
    active = integration_service.get_active_document_provider(db_session)
    assert active == config


def test_get_masked_config(db_session):
    user = create_user(db_session)
    config = create_config(db_session, user.id)
    masked = integration_service.get_masked_config(config)
    assert masked["token"] == ""
    assert masked["url"] == "https://example.com"
