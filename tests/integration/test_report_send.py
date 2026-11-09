# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Report send tests: submissions are written only after the email was sent."""

from datetime import date
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.integrations.base import EmailProvider
from src.models import (
    Company,
    EmailTemplate,
    Event,
    Expense,
    ExpenseSubmission,
    User,
)
from src.models.enums import (
    CompanyType,
    ExpenseCategory,
    ExpenseStatus,
    PaymentType,
)


class FakeSmtp(EmailProvider):
    """Email provider double that records or fails sends."""

    def __init__(self, result: bool | Exception) -> None:
        super().__init__({})
        self.result = result
        self.sent: list[dict[str, Any]] = []

    @classmethod
    def get_type(cls) -> str:
        return "smtp"

    @classmethod
    def get_display_name(cls) -> str:
        return "Fake SMTP"

    @classmethod
    def get_config_schema(cls) -> dict[str, Any]:
        return {}

    async def health_check(self) -> tuple[bool, str]:
        return True, "ok"

    async def send_email(
        self,
        to: list[str],
        subject: str,
        body: str,
        body_html: str | None = None,
        attachments: list[tuple[str, bytes, str]] | None = None,
    ) -> bool:
        if isinstance(self.result, Exception):
            raise self.result
        self.sent.append({"to": to, "subject": subject})
        return self.result


@pytest.fixture
def report_data(db_session: Session, test_user: User) -> dict[str, Any]:
    """Create an event with one open expense and an email template."""
    company = Company(name="Report Company", type=CompanyType.EMPLOYER)
    db_session.add(company)
    db_session.flush()
    event = Event(
        user_id=test_user.id,
        company_id=company.id,
        name="Report Event",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 3),
    )
    db_session.add(event)
    db_session.flush()
    expense = Expense(
        event_id=event.id,
        date=date(2026, 3, 2),
        amount=Decimal("12.50"),
        payment_type=PaymentType.CASH,
        category=ExpenseCategory.MEALS,
    )
    template = EmailTemplate(
        name="Report",
        reason="expense_report",
        company_id=company.id,
        subject="Report {{ event_name }}",
        body_html="<p>Report</p>",
        body_text="Report",
        is_default=True,
    )
    db_session.add_all([expense, template])
    db_session.commit()
    return {"event": event, "expense": expense, "template": template}


def _send(client: TestClient, event: Event, provider: FakeSmtp) -> Any:
    config = MagicMock(is_active=True)
    with (
        patch(
            "src.services.report_service.integration_service.get_integration_configs",
            return_value=[config],
        ),
        patch(
            "src.services.report_service.integration_service.create_provider_instance",
            return_value=provider,
        ),
    ):
        return client.post(
            f"/api/v1/events/{event.id}/expense-report/send",
            json={"recipient_emails": ["boss@example.com"]},
        )


def _assert_unchanged(db_session: Session, report_data: dict[str, Any]) -> None:
    db_session.expire_all()
    expense = db_session.get(Expense, report_data["expense"].id)
    assert expense is not None
    assert expense.status != ExpenseStatus.SUBMITTED
    assert db_session.query(ExpenseSubmission).count() == 0
    assert db_session.get(Event, report_data["event"].id).report_sent_at is None


@pytest.mark.parametrize("failure", [False, RuntimeError("smtp down")])
def test_send_failure_leaves_expenses_unchanged(
    authenticated_client: TestClient,
    db_session: Session,
    report_data: dict[str, Any],
    failure: bool | Exception,
) -> None:
    """An SMTP failure writes no submission and keeps the expense status."""
    response = _send(authenticated_client, report_data["event"], FakeSmtp(failure))

    assert response.status_code == 200
    assert response.json()["success"] is False
    assert "send" in response.json()["message"].lower()
    _assert_unchanged(db_session, report_data)


def test_send_success_writes_submission(
    authenticated_client: TestClient,
    db_session: Session,
    report_data: dict[str, Any],
) -> None:
    """A successful send writes one submission and sets SUBMITTED."""
    provider = FakeSmtp(True)
    response = _send(authenticated_client, report_data["event"], provider)

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert len(provider.sent) == 1
    db_session.expire_all()
    assert db_session.query(ExpenseSubmission).count() == 1
    expense = db_session.get(Expense, report_data["expense"].id)
    assert expense is not None
    assert expense.status == ExpenseStatus.SUBMITTED


@pytest.mark.parametrize(
    ("failure", "category"),
    [
        (ConnectionRefusedError("smtp.internal.example:587 refused"), "unreachable"),
        (RuntimeError("secret smtp.internal.example detail"), "unexpected"),
    ],
)
def test_send_error_message_is_categorised(
    authenticated_client: TestClient,
    report_data: dict[str, Any],
    failure: Exception,
    category: str,
) -> None:
    """A raised send error reports only its category, never the raw text."""
    response = _send(authenticated_client, report_data["event"], FakeSmtp(failure))

    message = response.json()["message"]
    assert message.startswith("Error sending report: ")
    assert category in message
    assert "smtp.internal.example" not in message
