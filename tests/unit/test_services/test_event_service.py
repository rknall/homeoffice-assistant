# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for event_service."""

from datetime import date

import pytest

from src.integrations.base import DocumentProvider
from src.models import Company, Event, User
from src.models.enums import CompanyType, EventStatus
from src.schemas.event import EventCreate, EventUpdate
from src.security import get_password_hash
from src.services import event_service


def create_user(db_session, username: str = "user") -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password=get_password_hash("Secret123!"),
        is_admin=False,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_company(db_session, name: str = "Acme") -> Company:
    company = Company(name=name, type=CompanyType.EMPLOYER)
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


def create_event_instance(db_session) -> tuple[Event, User, Company]:
    user = create_user(db_session)
    company = create_company(db_session)
    data = EventCreate(
        name="Expo",
        description="Desc",
        start_date=date(2025, 5, 1),
        end_date=date(2025, 5, 5),
        company_id=company.id,
        city="Vienna",
        country="Austria",
        country_code="AT",
        latitude=1.23,
        longitude=4.56,
        cover_image_url="https://example.com/image.jpg",
        cover_thumbnail_url="https://example.com/thumb.jpg",
        cover_photographer_name="Photographer",
        cover_photographer_url="https://example.com/photographer",
    )
    event = event_service.create_event(db_session, data, user.id)
    return event, user, company


def test_get_and_filter_events(db_session):
    _, user, company = create_event_instance(db_session)
    results = event_service.get_events(db_session, include_company=True)
    assert len(results) == 1
    assert results[0].company is not None

    assert event_service.get_events(db_session, user_id=user.id)[0].user_id == user.id
    assert (
        event_service.get_events(db_session, company_id=company.id)[0].company_id
        == company.id
    )
    # Status filtering uses computed dates: May 1-5, 2025 is in the past (end_date < today)
    # Note: Event.status column stores default value (UPCOMING), but filtering uses dates
    past_events = event_service.get_events(db_session, status=EventStatus.PAST)
    assert len(past_events) == 1
    assert past_events[0].name == "Expo"


def test_event_crud_operations(db_session):
    event, user, _ = create_event_instance(db_session)
    fetched = event_service.get_event(db_session, event.id)
    assert fetched == event
    assert (
        event_service.get_event_for_user(
            db_session, event.id, user.id, include_company=True
        )
        == event
    )

    update = EventUpdate(
        name="Updated Expo",
        description="Updated",
        city="Graz",
        latitude=7.89,
        longitude=6.54,
        cover_image_url="https://example.com/new.jpg",
        cover_thumbnail_url="https://example.com/new-thumb.jpg",
        cover_photographer_name="New Photographer",
        paperless_custom_field_value="Custom",
    )
    updated = event_service.update_event(db_session, event, update)

    assert updated.name == "Updated Expo"
    assert updated.external_tag == "Updated Expo"
    assert updated.city == "Graz"
    assert updated.paperless_custom_field_value == "Custom"
    assert updated.cover_image_url.endswith("new.jpg")

    event_service.delete_event(db_session, updated)
    assert event_service.get_event(db_session, updated.id) is None


class DummyDocumentProvider(DocumentProvider):
    """Simple DocumentProvider stub for async tests."""

    def __init__(self, config: dict | None = None) -> None:
        self.config = config or {}
        self.tag_lookup_result: dict | None = {"id": 1}
        self.created_tag_result = {"id": 2}
        self.closed = False
        self.custom_field_data: dict | None = {"id": 5, "data_type": "select"}
        self.custom_field_choice_exists = False
        self.added_choices: list[str] = []
        self.tag_lookup_calls = 0
        self.create_tag_calls = 0
        self.custom_field_calls = 0

    @classmethod
    def get_type(cls) -> str:
        return "dummy"

    @classmethod
    def get_display_name(cls) -> str:
        return "Dummy"

    @classmethod
    def get_config_schema(cls) -> dict:
        return {}

    async def health_check(self) -> tuple[bool, str]:
        return True, "ok"

    async def close(self) -> None:
        self.closed = True

    async def list_storage_paths(self) -> list[dict]:
        return []

    async def list_tags(self) -> list[dict]:
        return []

    async def create_tag(self, name: str) -> dict:
        self.create_tag_calls += 1
        return self.created_tag_result

    async def get_tag_by_name(self, name: str) -> dict | None:
        self.tag_lookup_calls += 1
        return self.tag_lookup_result

    async def get_documents(
        self,
        tag_id=None,
        storage_path_id=None,
        custom_field_value=None,
    ) -> list[dict]:
        return []

    async def download_document(self, doc_id: int):
        return b"", "doc.pdf", "application/pdf"

    async def get_custom_field_by_name(self, name: str):
        self.custom_field_calls += 1
        return self.custom_field_data

    async def check_custom_field_choice_exists(self, field_id, value: str):
        return self.custom_field_choice_exists

    async def add_custom_field_choice(self, field_id, value: str):
        self.added_choices.append(value)


@pytest.mark.asyncio
async def test_sync_event_tag_to_paperless(monkeypatch, db_session):
    event, _user, _company = create_event_instance(db_session)
    provider = DummyDocumentProvider()

    monkeypatch.setattr(
        event_service.integration_service,
        "get_active_document_provider",
        lambda db: object(),
    )
    monkeypatch.setattr(
        event_service.integration_service,
        "create_provider_instance",
        lambda config: provider,
    )

    result = await event_service.sync_event_tag_to_paperless(db_session, event)
    assert result == {"id": 1}
    assert provider.tag_lookup_calls == 1

    provider.tag_lookup_result = None
    result = await event_service.sync_event_tag_to_paperless(db_session, event)
    assert result == {"id": 2}
    assert provider.create_tag_calls == 1


@pytest.mark.asyncio
async def test_sync_event_to_paperless_custom_field(monkeypatch, db_session):
    event, _user, _company = create_event_instance(db_session)
    provider = DummyDocumentProvider()
    provider.custom_field_choice_exists = False

    monkeypatch.setattr(
        event_service.integration_service,
        "get_active_document_provider",
        lambda db: object(),
    )
    monkeypatch.setattr(
        event_service.integration_service,
        "create_provider_instance",
        lambda config: provider,
    )
    monkeypatch.setattr(
        event_service.integration_service,
        "get_decrypted_config",
        lambda config: {"custom_field_name": "Trip"},
    )

    success = await event_service.sync_event_to_paperless_custom_field(
        db_session, event
    )
    assert success is True
    assert len(provider.added_choices) == 1

    provider.custom_field_choice_exists = True

    success = await event_service.sync_event_to_paperless_custom_field(
        db_session, event
    )
    assert success is True


@pytest.mark.asyncio
async def test_sync_event_to_paperless_custom_field_without_config(db_session):
    event, _user, _company = create_event_instance(db_session)
    assert (
        await event_service.sync_event_to_paperless_custom_field(db_session, event)
        is False
    )
