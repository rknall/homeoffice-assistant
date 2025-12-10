# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for report_generator."""

import io
import zipfile
from datetime import date
from decimal import Decimal

import pytest

from src.integrations.base import DocumentProvider
from src.models import Company, Event, User
from src.models.enums import CompanyType, EventStatus, ExpenseCategory, PaymentType
from src.schemas.event import EventCreate
from src.schemas.expense import ExpenseCreate
from src.security import get_password_hash
from src.services import event_service, expense_service, report_generator


def create_user(db_session) -> User:
    user = User(
        username="reporter",
        email="report@example.com",
        hashed_password=get_password_hash("Secret123!"),
        is_admin=True,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_company(db_session) -> Company:
    company = Company(name="Acme", type=CompanyType.EMPLOYER)
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


def create_event_with_expenses(db_session) -> Event:
    user = create_user(db_session)
    company = create_company(db_session)
    event = event_service.create_event(
        db_session,
        EventCreate(
            name="Conference",
            description="Desc",
            start_date=date(2025, 5, 1),
            end_date=date(2025, 5, 3),
            company_id=company.id,
            status=EventStatus.ACTIVE,
        ),
        user.id,
    )

    expense_service.create_expense(
        db_session,
        event.id,
        ExpenseCreate(
            date=date(2025, 5, 1),
            amount=Decimal("12.34"),
            currency="EUR",
            payment_type=PaymentType.CASH,
            category=ExpenseCategory.TRAVEL,
            description="Taxi",
            paperless_doc_id=1,
        ),
    )
    expense_service.create_expense(
        db_session,
        event.id,
        ExpenseCreate(
            date=date(2025, 5, 2),
            amount=Decimal("20.00"),
            currency="EUR",
            payment_type=PaymentType.CREDIT_CARD,
            category=ExpenseCategory.MEALS,
            description="Dinner",
        ),
    )
    db_session.refresh(event)
    return event


def test_get_preview(db_session):
    event = create_event_with_expenses(db_session)
    generator = report_generator.ExpenseReportGenerator(db_session)
    preview = generator.get_preview(event)
    assert preview["expense_count"] == 2
    assert preview["documents_available"] == 1
    assert preview["paperless_configured"] is False


class FakePaperless:
    async def download_document(self, doc_id: int):
        return b"PDF", "receipt.pdf", "application/pdf"

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_generate_creates_zip_with_excel(db_session):
    event = create_event_with_expenses(db_session)
    generator = report_generator.ExpenseReportGenerator(
        db_session, paperless=FakePaperless()
    )
    zip_bytes = await generator.generate(event)

    assert len(zip_bytes) > 0
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zip_file:
        names = zip_file.namelist()
        assert any(name.endswith(".xlsx") for name in names)
        assert any(name.startswith("documents/") for name in names)


def test_get_filename(db_session):
    event = create_event_with_expenses(db_session)
    generator = report_generator.ExpenseReportGenerator(db_session)
    filename = generator.get_filename(event)
    assert filename.startswith("expense_report_")
    assert filename.endswith(".zip")


class DummyDocumentProvider(DocumentProvider):
    def __init__(self, config: dict):
        self.config = config

    @classmethod
    def get_type(cls) -> str:
        return "dummy"

    @classmethod
    def get_display_name(cls) -> str:
        return "Dummy"

    @classmethod
    def get_config_schema(cls) -> dict:
        return {}

    async def health_check(self):
        return True, "ok"

    async def close(self):
        return None

    async def list_storage_paths(self):
        return []

    async def list_tags(self):
        return []

    async def create_tag(self, name: str):
        return {"id": 1, "name": name}

    async def get_tag_by_name(self, name: str):
        return None

    async def get_documents(self, tag_id=None, storage_path_id=None, custom_field_value=None):
        return []

    async def download_document(self, doc_id: int):
        return b"", "doc.pdf", "application/pdf"


@pytest.mark.asyncio
async def test_create_report_generator(monkeypatch, db_session):
    event = create_event_with_expenses(db_session)
    monkeypatch.setattr(
        report_generator.integration_service,
        "get_active_document_provider",
        lambda db: object(),
    )
    monkeypatch.setattr(
        report_generator.integration_service,
        "create_provider_instance",
        lambda config: DummyDocumentProvider({}),
    )

    generator = await report_generator.create_report_generator(db_session, event)
    assert isinstance(generator.paperless, DummyDocumentProvider)

    monkeypatch.setattr(
        report_generator.integration_service,
        "create_provider_instance",
        lambda config: object(),
    )
    generator = await report_generator.create_report_generator(db_session, event)
    assert generator.paperless is None
