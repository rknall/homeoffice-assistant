# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for currency_service."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
import respx
from httpx import Response

from src.models.currency_cache import CurrencyCache
from src.services.currency_service import (
    ConversionResult,
    Currency,
    CurrencyService,
    CurrencyServiceError,
)


@pytest.fixture
def currency_service(db_session):
    """Create a currency service with test database."""
    return CurrencyService(db_session)


class TestGetSupportedCurrencies:
    """Tests for get_supported_currencies method."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetches_currencies_from_api(self, currency_service):
        """Should fetch and return currencies from frankfurter API."""
        respx.get("https://api.frankfurter.app/currencies").mock(
            return_value=Response(
                200,
                json={
                    "EUR": "Euro",
                    "USD": "United States Dollar",
                    "PLN": "Polish Złoty",
                },
            )
        )

        currencies = await currency_service.get_supported_currencies()

        assert len(currencies) == 3
        assert Currency(code="EUR", name="Euro") in currencies
        assert Currency(code="PLN", name="Polish Złoty") in currencies

    @respx.mock
    @pytest.mark.asyncio
    async def test_caches_currencies_in_memory(self, currency_service):
        """Should cache currencies and not call API twice."""
        route = respx.get("https://api.frankfurter.app/currencies").mock(
            return_value=Response(200, json={"EUR": "Euro"})
        )

        await currency_service.get_supported_currencies()
        await currency_service.get_supported_currencies()

        assert route.call_count == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_raises_on_api_error(self, currency_service):
        """Should raise CurrencyServiceError on API failure."""
        respx.get("https://api.frankfurter.app/currencies").mock(
            return_value=Response(500)
        )

        with pytest.raises(CurrencyServiceError):
            await currency_service.get_supported_currencies()


class TestGetRate:
    """Tests for get_rate method."""

    @pytest.mark.asyncio
    async def test_same_currency_returns_one(self, currency_service):
        """Same currency conversion should return rate of 1."""
        rate, rate_date = await currency_service.get_rate(
            "EUR", "EUR", date(2025, 1, 15)
        )

        assert rate == Decimal("1.0")
        assert rate_date == date(2025, 1, 15)

    @pytest.mark.asyncio
    async def test_same_currency_case_insensitive(self, currency_service):
        """Same currency check should be case insensitive."""
        rate, _ = await currency_service.get_rate("eur", "EUR", date(2025, 1, 15))
        assert rate == Decimal("1.0")

    @respx.mock
    @pytest.mark.asyncio
    async def test_uses_cached_rate(self, currency_service, db_session):
        """Should return cached rate if fresh enough."""
        # Pre-populate cache
        cache_entry = CurrencyCache(
            base_currency="PLN",
            target_currency="EUR",
            rate=Decimal("0.231"),
            rate_date=date(2025, 1, 15),
            fetched_at=datetime.utcnow(),
        )
        db_session.add(cache_entry)
        db_session.commit()

        rate, rate_date = await currency_service.get_rate(
            "PLN", "EUR", date(2025, 1, 15)
        )

        assert rate == Decimal("0.231")
        assert rate_date == date(2025, 1, 15)

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetches_from_api_when_not_cached(self, currency_service):
        """Should fetch from API when rate not in cache."""
        respx.get("https://api.frankfurter.app/2025-01-15").mock(
            return_value=Response(
                200,
                json={
                    "amount": 1.0,
                    "base": "PLN",
                    "date": "2025-01-15",
                    "rates": {"EUR": 0.231},
                },
            )
        )

        rate, rate_date = await currency_service.get_rate(
            "PLN", "EUR", date(2025, 1, 15)
        )

        assert rate == Decimal("0.231")
        assert rate_date == date(2025, 1, 15)

    @respx.mock
    @pytest.mark.asyncio
    async def test_caches_fetched_rate(self, currency_service, db_session):
        """Should cache the rate after fetching from API."""
        respx.get("https://api.frankfurter.app/2025-01-15").mock(
            return_value=Response(
                200,
                json={
                    "amount": 1.0,
                    "base": "USD",
                    "date": "2025-01-15",
                    "rates": {"EUR": 0.92},
                },
            )
        )

        await currency_service.get_rate("USD", "EUR", date(2025, 1, 15))

        cached = (
            db_session.query(CurrencyCache)
            .filter(
                CurrencyCache.base_currency == "USD",
                CurrencyCache.target_currency == "EUR",
            )
            .first()
        )
        assert cached is not None
        assert cached.rate == Decimal("0.92")

    @respx.mock
    @pytest.mark.asyncio
    async def test_handles_weekend_rate_date(self, currency_service):
        """API returns Friday's rate for weekend dates."""
        # Request Saturday, API returns Friday's date
        respx.get("https://api.frankfurter.app/2025-01-18").mock(
            return_value=Response(
                200,
                json={
                    "amount": 1.0,
                    "base": "GBP",
                    "date": "2025-01-17",  # Friday
                    "rates": {"EUR": 1.19},
                },
            )
        )

        rate, rate_date = await currency_service.get_rate(
            "GBP", "EUR", date(2025, 1, 18)  # Saturday
        )

        assert rate == Decimal("1.19")
        assert rate_date == date(2025, 1, 17)  # Returns Friday

    @respx.mock
    @pytest.mark.asyncio
    async def test_falls_back_to_latest_on_404(self, currency_service):
        """Should fall back to latest rate when date not found."""
        respx.get("https://api.frankfurter.app/2025-01-15").mock(
            return_value=Response(404)
        )
        respx.get("https://api.frankfurter.app/latest").mock(
            return_value=Response(
                200,
                json={
                    "amount": 1.0,
                    "base": "CHF",
                    "date": "2025-01-14",
                    "rates": {"EUR": 1.05},
                },
            )
        )

        rate, rate_date = await currency_service.get_rate(
            "CHF", "EUR", date(2025, 1, 15)
        )

        assert rate == Decimal("1.05")
        assert rate_date == date(2025, 1, 14)


class TestConvert:
    """Tests for convert method."""

    @pytest.mark.asyncio
    async def test_same_currency_conversion(self, currency_service):
        """Same currency conversion returns same amount."""
        result = await currency_service.convert(
            amount=Decimal("100.00"),
            from_currency="EUR",
            to_currency="EUR",
            expense_date=date(2025, 1, 15),
        )

        assert result.converted_amount == Decimal("100.00")
        assert result.exchange_rate == Decimal("1.0")

    @respx.mock
    @pytest.mark.asyncio
    async def test_converts_with_exchange_rate(self, currency_service):
        """Should convert amount using exchange rate."""
        respx.get("https://api.frankfurter.app/2025-01-15").mock(
            return_value=Response(
                200,
                json={
                    "amount": 1.0,
                    "base": "PLN",
                    "date": "2025-01-15",
                    "rates": {"EUR": 0.23},
                },
            )
        )

        result = await currency_service.convert(
            amount=Decimal("500.00"),
            from_currency="PLN",
            to_currency="EUR",
            expense_date=date(2025, 1, 15),
        )

        assert result.converted_amount == Decimal("115.00")  # 500 * 0.23
        assert result.exchange_rate == Decimal("0.23")
        assert result.original_amount == Decimal("500.00")
        assert result.original_currency == "PLN"
        assert result.target_currency == "EUR"

    @respx.mock
    @pytest.mark.asyncio
    async def test_rounds_to_two_decimal_places(self, currency_service):
        """Converted amount should be rounded to 2 decimals."""
        respx.get("https://api.frankfurter.app/2025-01-15").mock(
            return_value=Response(
                200,
                json={
                    "amount": 1.0,
                    "base": "USD",
                    "date": "2025-01-15",
                    "rates": {"EUR": 0.923456},
                },
            )
        )

        result = await currency_service.convert(
            amount=Decimal("100.00"),
            from_currency="USD",
            to_currency="EUR",
            expense_date=date(2025, 1, 15),
        )

        # 100 * 0.923456 = 92.3456 → rounded to 92.35
        assert result.converted_amount == Decimal("92.35")

    @respx.mock
    @pytest.mark.asyncio
    async def test_returns_conversion_result_dataclass(self, currency_service):
        """Should return a ConversionResult with all fields."""
        respx.get("https://api.frankfurter.app/2025-01-15").mock(
            return_value=Response(
                200,
                json={
                    "amount": 1.0,
                    "base": "GBP",
                    "date": "2025-01-15",
                    "rates": {"EUR": 1.18},
                },
            )
        )

        result = await currency_service.convert(
            amount=Decimal("50.00"),
            from_currency="GBP",
            to_currency="EUR",
            expense_date=date(2025, 1, 15),
        )

        assert isinstance(result, ConversionResult)
        assert result.rate_date == date(2025, 1, 15)


class TestCacheExpiry:
    """Tests for cache expiration behavior."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_expired_cache_triggers_api_call(self, currency_service, db_session):
        """Should fetch from API when cached rate is too old."""
        # Add stale cache entry (25 hours old)
        stale_time = datetime.utcnow() - timedelta(hours=25)
        cache_entry = CurrencyCache(
            base_currency="USD",
            target_currency="EUR",
            rate=Decimal("0.90"),  # Old rate
            rate_date=date(2025, 1, 14),
            fetched_at=stale_time,
        )
        db_session.add(cache_entry)
        db_session.commit()

        # Mock API with fresh rate
        respx.get("https://api.frankfurter.app/2025-01-15").mock(
            return_value=Response(
                200,
                json={
                    "amount": 1.0,
                    "base": "USD",
                    "date": "2025-01-15",
                    "rates": {"EUR": 0.92},  # New rate
                },
            )
        )

        rate, _ = await currency_service.get_rate("USD", "EUR", date(2025, 1, 15))

        # Should get the fresh rate from API
        assert rate == Decimal("0.92")
