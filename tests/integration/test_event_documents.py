# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Paperless document routes only reach documents linked to the event."""

from datetime import date
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.integrations.base import LlmProvider
from src.integrations.llm import LlmError
from src.integrations.paperless import PaperlessProvider
from src.models import Company, DocumentReference, Event, Expense, User
from src.models.enums import (
    CompanyType,
    ExpenseCategory,
    IntegrationType,
    PaymentType,
)
from src.services import integration_service

REFERENCED_DOC = 11
EXPENSE_DOC = 12
LISTED_DOC = 13
FOREIGN_DOC = 99


@pytest.fixture
def event(db_session: Session, test_user: User) -> Event:
    """Create an event with one referenced and one expense document."""
    company = Company(
        name="Doc Company",
        type=CompanyType.EMPLOYER,
        paperless_storage_path_id=5,
    )
    db_session.add(company)
    db_session.flush()
    event = Event(
        user_id=test_user.id,
        company_id=company.id,
        name="Doc Event",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 3),
        paperless_custom_field_value="Doc Event",
    )
    db_session.add(event)
    db_session.flush()
    db_session.add_all(
        [
            DocumentReference(
                event_id=event.id, paperless_doc_id=REFERENCED_DOC, title="Ref"
            ),
            Expense(
                event_id=event.id,
                date=date(2026, 3, 2),
                amount=Decimal("12.50"),
                payment_type=PaymentType.CASH,
                category=ExpenseCategory.MEALS,
                paperless_doc_id=EXPENSE_DOC,
            ),
        ]
    )
    db_session.commit()
    db_session.refresh(event)
    return event


@pytest.fixture
def paperless(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Replace the Paperless and LLM integrations with mocks."""
    provider = MagicMock(spec=PaperlessProvider)
    provider.get_custom_field_by_name.return_value = {"id": 7}
    provider.get_documents_for_event.return_value = [{"id": LISTED_DOC}]
    provider.delete_document.return_value = True
    provider.download_document.return_value = (b"%PDF", "doc.pdf", "application/pdf")
    provider.get_document_content.return_value = "Hotel 120.00 EUR"

    llm = MagicMock(spec=LlmProvider)
    llm.extract_expense.return_value = {"amount": "120.00", "currency": "EUR"}
    provider.llm = llm

    paperless_config = MagicMock(name="paperless_config")
    llm_config = MagicMock(name="llm_config")

    def create(config: Any) -> MagicMock:
        return llm if config is llm_config else provider

    def configs(db: Any, integration_type: Any = None, active_only: bool = False):
        return [
            llm_config if integration_type == IntegrationType.LLM else paperless_config
        ]

    monkeypatch.setattr(integration_service, "get_integration_configs", configs)
    monkeypatch.setattr(
        integration_service,
        "get_decrypted_config",
        lambda config: {"custom_field_name": "Trip"},
    )
    monkeypatch.setattr(integration_service, "create_provider_instance", create)
    return provider


def _call(client: TestClient, route: str, event: Event, doc_id: int) -> Any:
    base = f"/api/v1/events/{event.id}/documents/{doc_id}"
    if route == "delete":
        return client.delete(base)
    if route == "preview":
        return client.get(f"{base}/preview")
    return client.post(f"{base}/scan-expense")


ROUTES = ["delete", "preview", "scan"]


@pytest.mark.parametrize("route", ROUTES)
def test_foreign_document_returns_404(
    authenticated_client: TestClient,
    event: Event,
    paperless: MagicMock,
    route: str,
) -> None:
    """A document id not linked to the event is never touched."""
    response = _call(authenticated_client, route, event, FOREIGN_DOC)

    assert response.status_code == 404
    paperless.delete_document.assert_not_called()
    paperless.download_document.assert_not_called()
    paperless.get_document_content.assert_not_called()


@pytest.mark.parametrize("doc_id", [REFERENCED_DOC, EXPENSE_DOC, LISTED_DOC])
@pytest.mark.parametrize("route", ROUTES)
def test_linked_document_keeps_response(
    authenticated_client: TestClient,
    event: Event,
    paperless: MagicMock,
    route: str,
    doc_id: int,
) -> None:
    """Referenced, expense and Paperless-listed documents stay reachable."""
    response = _call(authenticated_client, route, event, doc_id)

    if route == "delete":
        assert response.status_code == 204
        paperless.delete_document.assert_awaited_once_with(doc_id)
    elif route == "preview":
        assert response.status_code == 200
        assert response.content == b"%PDF"
        assert 'filename="doc.pdf"' in response.headers["content-disposition"]
    else:
        assert response.status_code == 200
        assert response.json()["amount"] == "120.00"


def test_local_link_skips_paperless_lookup(
    authenticated_client: TestClient, event: Event, paperless: MagicMock
) -> None:
    """A locally linked document needs no Paperless listing call."""
    response = _call(authenticated_client, "preview", event, REFERENCED_DOC)

    assert response.status_code == 200
    paperless.get_documents_for_event.assert_not_called()


def test_document_listing_unchanged(
    authenticated_client: TestClient, event: Event, paperless: MagicMock
) -> None:
    """The event document list still uses the storage path and custom field."""
    paperless.get_documents_for_event.return_value = [
        {"id": LISTED_DOC, "title": "Listed", "original_file_name": "l.pdf"}
    ]

    response = authenticated_client.get(f"/api/v1/events/{event.id}/documents")

    assert response.status_code == 200
    assert [doc["id"] for doc in response.json()] == [LISTED_DOC]
    paperless.get_custom_field_by_name.assert_awaited_once_with("Trip")
    paperless.get_documents_for_event.assert_awaited_once_with(
        storage_path_id=5,
        custom_field_id=7,
        custom_field_value="Doc Event",
    )


def test_scan_failure_reports_category_only(
    authenticated_client: TestClient, event: Event, paperless: MagicMock
) -> None:
    """An LLM failure shows its category, not the wrapped provider text."""
    cause = httpx.ConnectError("https://llm.internal.example:11434 refused")
    error = LlmError("LLM request failed: https://llm.internal.example:11434")
    error.__cause__ = cause
    paperless.llm.extract_expense.side_effect = error

    response = _call(authenticated_client, "scan", event, EXPENSE_DOC)

    assert response.status_code == 502
    assert response.json()["detail"] == "Expense scan failed: server unreachable"
    assert "llm.internal.example" not in response.text
