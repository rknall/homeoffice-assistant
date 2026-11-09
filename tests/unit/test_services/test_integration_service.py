# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for integration_service."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.integrations.base import DocumentProvider, EmailProvider
from src.integrations.registry import IntegrationRegistry
from src.models import IntegrationConfig, User
from src.models.enums import IntegrationType
from src.schemas.integration import (
    IntegrationConfigCreate,
    IntegrationConfigUpdate,
    LlmModelsRequest,
)
from src.security import get_password_hash
from src.services import config_secrets, integration_service


def create_user(db_session) -> User:
    user = User(
        username="integration",
        email="integration@example.com",
        hashed_password=get_password_hash("Secret123!"),
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
    updated = integration_service.update_integration_config(db_session, config, update)

    assert updated.name == "Updated"
    assert updated.is_active is False
    decrypted = integration_service.get_decrypted_config(updated)
    assert decrypted["token"] == "secret"
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


STORED_ACCESS = "stored-access-value"
STORED_SIGNING = "stored-signing-value"
STORED_LLM_KEY = "stored-llm-key"
STORED_BASIC = "stored-basic-value"


def create_unsplash_config(db_session, user_id) -> IntegrationConfig:
    data = IntegrationConfigCreate(
        integration_type=IntegrationType.UNSPLASH,
        name="Unsplash",
        config={"access_key": STORED_ACCESS, "secret_key": STORED_SIGNING},
    )
    return integration_service.create_integration_config(db_session, data, user_id)


def create_llm_config(db_session, user_id) -> IntegrationConfig:
    data = IntegrationConfigCreate(
        integration_type=IntegrationType.LLM,
        name="LLM",
        config={
            "base_url": "https://llm.example.com/v1",
            "api_key": STORED_LLM_KEY,
            "username": "gateway",
            "password": STORED_BASIC,
            "model": "m1",
        },
    )
    return integration_service.create_integration_config(db_session, data, user_id)


def test_secret_fields_follow_schema_format():
    schema = {
        "properties": {
            "url": {"type": "string", "format": "uri"},
            "access_key": {"type": "string", "format": "password"},
            "name": {"type": "string"},
        }
    }
    assert config_secrets.secret_fields(schema) == {"access_key"}
    assert config_secrets.secret_fields({}) == set()


def test_set_secret_fields_lists_only_set_secrets():
    schema = {
        "properties": {
            "api_key": {"format": "password"},
            "token": {"format": "password"},
            "url": {},
        }
    }
    config = {"api_key": STORED_LLM_KEY, "token": "", "url": "https://a.example.com"}

    assert config_secrets.set_secret_fields(config, schema) == ["api_key"]
    assert config_secrets.set_secret_fields({}, schema) == []


def test_get_secrets_set(db_session):
    user = create_user(db_session)
    config = create_config(db_session, user.id)

    assert integration_service.get_secrets_set(config) == ["token"]


def test_mask_and_merge_keep_non_secret_fields():
    schema = {"properties": {"api_key": {"format": "password"}, "url": {}}}
    stored = {"api_key": STORED_LLM_KEY, "url": "https://a.example.com"}

    masked = config_secrets.mask(stored, schema)
    assert masked == {"api_key": config_secrets.MASK, "url": "https://a.example.com"}
    assert stored["api_key"] == STORED_LLM_KEY

    merged = config_secrets.merge(
        stored, {"api_key": config_secrets.MASK, "url": "https://b.example.com"}, schema
    )
    assert merged == {"api_key": STORED_LLM_KEY, "url": "https://b.example.com"}
    assert config_secrets.merge(stored, {"api_key": "new"}, schema)["api_key"] == "new"


def test_unsplash_secrets_masked(db_session):
    user = create_user(db_session)
    config = create_unsplash_config(db_session, user.id)
    masked = integration_service.get_masked_config(config)
    assert masked["access_key"] == config_secrets.MASK
    assert masked["secret_key"] == config_secrets.MASK


def test_unsplash_secrets_preserved_on_update(db_session):
    user = create_user(db_session)
    config = create_unsplash_config(db_session, user.id)
    update = IntegrationConfigUpdate(config={"access_key": "", "secret_key": ""})
    updated = integration_service.update_integration_config(db_session, config, update)
    decrypted = integration_service.get_decrypted_config(updated)
    assert decrypted["access_key"] == STORED_ACCESS
    assert decrypted["secret_key"] == STORED_SIGNING


def test_resolve_llm_models_config_same_base_url_fills_secrets(db_session):
    user = create_user(db_session)
    config = create_llm_config(db_session, user.id)
    request = LlmModelsRequest(
        base_url="https://llm.example.com/v1/", username="gateway", config_id=config.id
    )
    resolved = integration_service.resolve_llm_models_config(db_session, request)
    assert resolved["api_key"] == STORED_LLM_KEY
    assert resolved["password"] == STORED_BASIC
    assert "config_id" not in resolved


def test_resolve_llm_models_config_foreign_base_url_keeps_secrets(db_session):
    user = create_user(db_session)
    config = create_llm_config(db_session, user.id)
    request = LlmModelsRequest(
        base_url="https://attacker.example.com/v1",
        username="gateway",
        config_id=config.id,
    )
    resolved = integration_service.resolve_llm_models_config(db_session, request)
    assert resolved["api_key"] == config_secrets.MASK
    assert resolved["password"] == config_secrets.MASK


def _fake_provider(monkeypatch, spec) -> MagicMock:
    provider = MagicMock(spec=spec)
    provider.close = AsyncMock()
    monkeypatch.setattr(
        integration_service, "create_provider_instance", lambda conf: provider
    )
    return provider


async def test_open_provider_yields_and_closes(db_session, monkeypatch):
    config = create_config(db_session, create_user(db_session).id)
    provider = _fake_provider(monkeypatch, DocumentProvider)

    async with integration_service.open_provider(
        db_session, config.id, IntegrationType.PAPERLESS
    ) as opened:
        assert opened is provider
        provider.close.assert_not_awaited()

    provider.close.assert_awaited_once()


async def test_open_provider_closes_on_error(db_session, monkeypatch):
    config = create_config(db_session, create_user(db_session).id)
    provider = _fake_provider(monkeypatch, DocumentProvider)

    with pytest.raises(RuntimeError):
        async with integration_service.open_provider(
            db_session, config.id, IntegrationType.PAPERLESS
        ):
            raise RuntimeError("boom")

    provider.close.assert_awaited_once()


async def test_open_provider_unknown_config(db_session):
    with pytest.raises(integration_service.IntegrationNotFoundError) as info:
        async with integration_service.open_provider(
            db_session, uuid.uuid4(), IntegrationType.PAPERLESS
        ):
            pass

    assert info.value.status_code == 404


async def test_open_provider_wrong_type(db_session):
    config = create_config(db_session, create_user(db_session).id)

    with pytest.raises(integration_service.IntegrationTypeMismatchError) as info:
        async with integration_service.open_provider(
            db_session, config.id, IntegrationType.SMTP
        ):
            pass

    assert info.value.status_code == 400
    assert "SMTP" in info.value.detail


async def test_open_provider_unusable_instance(db_session, monkeypatch):
    config = create_config(db_session, create_user(db_session).id)
    monkeypatch.setattr(integration_service, "create_provider_instance", lambda c: None)

    with pytest.raises(integration_service.ProviderUnavailableError) as info:
        async with integration_service.open_provider(
            db_session, config.id, IntegrationType.PAPERLESS
        ):
            pass

    assert info.value.status_code == 500


async def test_open_active_provider_skips_inactive(db_session, monkeypatch):
    config = create_config(db_session, create_user(db_session).id)
    provider = _fake_provider(monkeypatch, DocumentProvider)

    async with integration_service.open_active_provider(
        db_session, IntegrationType.PAPERLESS
    ) as opened:
        assert opened is provider

    config.is_active = False
    db_session.commit()
    with pytest.raises(integration_service.NoActiveIntegrationError) as info:
        async with integration_service.open_active_provider(
            db_session, IntegrationType.PAPERLESS
        ):
            pass

    assert info.value.status_code == 400
    assert "Paperless" in info.value.detail


async def test_open_active_provider_picks_the_active_smtp(db_session, monkeypatch):
    user = create_user(db_session)
    for name, active in [("off", False), ("on", True)]:
        config = integration_service.create_integration_config(
            db_session,
            IntegrationConfigCreate(
                integration_type=IntegrationType.SMTP,
                name=name,
                config={"host": name, "password": "x"},
            ),
            user.id,
        )
        config.is_active = active
    db_session.commit()
    picked: list[str] = []
    provider = MagicMock(spec=EmailProvider)
    provider.close = AsyncMock()

    def create(conf):
        picked.append(conf.name)
        return provider

    monkeypatch.setattr(integration_service, "create_provider_instance", create)

    async with integration_service.open_active_provider(
        db_session, IntegrationType.SMTP
    ):
        pass

    assert picked == ["on"]


def test_get_type_matches_integration_type():
    for integration_type in IntegrationType:
        provider = IntegrationRegistry.get_provider(integration_type.value)
        assert provider is not None
        assert provider.get_type() == integration_type.value
