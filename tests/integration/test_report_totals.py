# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Dashboard, report preview and generated report agree on the totals."""

import io
import zipfile
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from src.models import Company, Event, Expense, User
from src.models.enums import (
    CompanyType,
    ExpenseCategory,
    ExpenseStatus,
    PaymentType,
)
from src.services import dashboard_service
from src.services.currency_service import CurrencyService, CurrencyServiceError


@pytest.fixture(autouse=True)
def rates_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every non-base currency conversion fail."""

    async def failing_convert(self, *args, **kwargs):
        raise CurrencyServiceError("rates unavailable")

    monkeypatch.setattr(CurrencyService, "convert", failing_convert)


def _make_event(db: Session, user: User) -> Event:
    company = Company(name="Totals Company", type=CompanyType.EMPLOYER)
    db.add(company)
    db.flush()
    event = Event(
        user_id=user.id,
        company_id=company.id,
        name="Totals Event",
        start_date=date(2020, 4, 1),
        end_date=date(2020, 4, 3),
    )
    db.add(event)
    db.flush()
    return event


def _expense(
    event: Event,
    amount: str,
    currency: str = "EUR",
    converted: str | None = None,
    **kwargs,
) -> Expense:
    return Expense(
        event_id=event.id,
        date=date(2020, 4, 2),
        amount=Decimal(amount),
        currency=currency,
        converted_amount=Decimal(converted) if converted else None,
        payment_type=PaymentType.CASH,
        category=ExpenseCategory.MEALS,
        **kwargs,
    )


def _report_total(client: TestClient, event: Event) -> float:
    response = client.post(
        f"/api/v1/events/{event.id}/expense-report/generate",
        json={"mark_as_submitted": False},
    )
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
        name = next(n for n in zip_file.namelist() if n.endswith(".xlsx"))
        sheet = load_workbook(io.BytesIO(zip_file.read(name))).active
    row = next(r for r in sheet.iter_rows() if r[4].value == "Totals:")
    return float(row[7].value)


def test_totals_agree_with_one_unconverted_row(
    authenticated_client: TestClient, db_session: Session, test_user: User
) -> None:
    """The unconverted USD row counts at its raw amount everywhere."""
    event = _make_event(db_session, test_user)
    db_session.add_all(
        [
            _expense(event, "10.00", converted="10.00"),
            _expense(event, "5.00", currency="USD"),
        ]
    )
    db_session.commit()

    dashboard = dashboard_service.get_events_needing_reports(db_session, test_user.id)
    preview = authenticated_client.get(
        f"/api/v1/events/{event.id}/expense-report/preview"
    ).json()
    generated = _report_total(authenticated_client, event)

    assert dashboard[0].total_amount == Decimal("15.00")
    assert preview["total"] == 15.0
    assert generated == 15.0


def test_preview_total_excludes_private_and_reimbursed(
    authenticated_client: TestClient, db_session: Session, test_user: User
) -> None:
    """Preview selects expenses like the generated report does."""
    event = _make_event(db_session, test_user)
    db_session.add_all(
        [
            _expense(event, "10.00", converted="10.00"),
            _expense(event, "40.00", converted="40.00", is_private=True),
            _expense(
                event, "70.00", converted="70.00", status=ExpenseStatus.REIMBURSED
            ),
        ]
    )
    db_session.commit()

    preview = authenticated_client.get(
        f"/api/v1/events/{event.id}/expense-report/preview"
    ).json()
    generated = _report_total(authenticated_client, event)

    assert preview["expense_count"] == 1
    assert preview["total"] == 10.0
    assert preview["total"] == generated
