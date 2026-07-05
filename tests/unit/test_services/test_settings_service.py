# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for settings_service."""

from src.models import SystemSettings
from src.services import settings_service


def test_get_and_set_setting(db_session):
    assert settings_service.get_setting(db_session, "missing") is None
    settings_service.set_setting(db_session, "key", "value", is_encrypted=True)
    assert settings_service.get_setting(db_session, "key") == "value"
    setting = db_session.query(SystemSettings).filter_by(key="key").first()
    assert setting.is_encrypted is True


def test_locale_settings_defaults(db_session):
    settings = settings_service.get_locale_settings(db_session)
    assert settings["date_format"] == settings_service.DEFAULT_DATE_FORMAT


def test_update_locale_settings(db_session):
    updated = settings_service.update_locale_settings(
        db_session, date_format="DD.MM.YYYY", timezone="Europe/Vienna"
    )
    assert updated["date_format"] == "DD.MM.YYYY"
    assert updated["timezone"] == "Europe/Vienna"


def test_base_currency_defaults_to_eur(db_session):
    assert settings_service.get_base_currency(db_session) == "EUR"


def test_set_base_currency_uppercases(db_session):
    assert settings_service.set_base_currency(db_session, "usd") == "USD"
    assert settings_service.get_base_currency(db_session) == "USD"


def test_changing_base_currency_invalidates_conversions(db_session):
    from datetime import date
    from decimal import Decimal

    from src.models import Company, Event, Expense, User
    from src.models.enums import CompanyType, ExpenseCategory, PaymentType

    user = User(username="u1", email="u1@example.com", hashed_password="x")
    company = Company(name="Acme", type=CompanyType.EMPLOYER)
    db_session.add_all([user, company])
    db_session.flush()
    event = Event(
        name="Trip",
        company_id=company.id,
        user_id=user.id,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 2),
    )
    db_session.add(event)
    db_session.flush()
    expense = Expense(
        event_id=event.id,
        date=date(2025, 1, 1),
        description="Taxi",
        amount=Decimal("10.00"),
        currency="EUR",
        payment_type=PaymentType.CASH,
        category=ExpenseCategory.TRANSPORT,
        converted_amount=Decimal("10.00"),
        exchange_rate=Decimal("1.0"),
        rate_date=date(2025, 1, 1),
    )
    db_session.add(expense)
    db_session.commit()

    # Same currency: conversions untouched
    settings_service.set_base_currency(db_session, "EUR")
    db_session.refresh(expense)
    assert expense.converted_amount == Decimal("10.00")

    # Different currency: conversions invalidated for lazy recompute
    settings_service.set_base_currency(db_session, "GBP")
    db_session.refresh(expense)
    assert expense.converted_amount is None
    assert expense.exchange_rate is None
    assert expense.rate_date is None
