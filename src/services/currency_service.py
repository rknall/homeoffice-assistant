# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Currency conversion service using frankfurter.app API."""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

import httpx
from sqlalchemy.orm import Session

from src.models.currency_cache import CurrencyCache

logger = logging.getLogger(__name__)

# frankfurter.app API base URL (ECB data, free, no API key needed)
FRANKFURTER_API_URL = "https://api.frankfurter.app"

# Cache duration before we consider re-fetching (in hours)
CACHE_FRESHNESS_HOURS = 24

# Maximum days to look back for a rate when exact date unavailable
MAX_RATE_LOOKBACK_DAYS = 7


@dataclass
class Currency:
    """Currency information."""

    code: str
    name: str


@dataclass
class ConversionResult:
    """Result of a currency conversion."""

    original_amount: Decimal
    original_currency: str
    converted_amount: Decimal
    target_currency: str
    exchange_rate: Decimal
    rate_date: date


class CurrencyServiceError(Exception):
    """Base exception for currency service errors."""


class RateNotFoundError(CurrencyServiceError):
    """Exchange rate could not be found."""


class CurrencyService:
    """Service for currency conversion and exchange rate management."""

    def __init__(self, db: Session) -> None:
        """Initialize the currency service.

        Args:
            db: Database session for caching rates.
        """
        self.db = db
        self._http_client: httpx.AsyncClient | None = None
        self._supported_currencies: dict[str, str] | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                base_url=FRANKFURTER_API_URL,
                timeout=10.0,
            )
        return self._http_client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def get_supported_currencies(self) -> list[Currency]:
        """Fetch list of supported currencies from the API.

        Returns:
            List of Currency objects with code and name.

        Raises:
            CurrencyServiceError: If API call fails.
        """
        if self._supported_currencies is not None:
            return [
                Currency(code=code, name=name)
                for code, name in sorted(self._supported_currencies.items())
            ]

        try:
            client = await self._get_client()
            response = await client.get("/currencies")
            response.raise_for_status()
            self._supported_currencies = response.json()
            return [
                Currency(code=code, name=name)
                for code, name in sorted(self._supported_currencies.items())
            ]
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch currencies: {e}")
            raise CurrencyServiceError(f"Failed to fetch currencies: {e}") from e

    async def get_rate(
        self,
        from_currency: str,
        to_currency: str,
        rate_date: date,
    ) -> tuple[Decimal, date]:
        """Get exchange rate for a specific date.

        First checks the cache, then fetches from API if needed.
        Falls back to nearest available rate for weekends/holidays.

        Args:
            from_currency: Source currency code (e.g., "PLN").
            to_currency: Target currency code (e.g., "EUR").
            rate_date: Date for the exchange rate.

        Returns:
            Tuple of (exchange_rate, actual_rate_date).

        Raises:
            RateNotFoundError: If no rate found within lookback period.
            CurrencyServiceError: If API call fails.
        """
        # Same currency = rate of 1
        if from_currency.upper() == to_currency.upper():
            return Decimal("1.0"), rate_date

        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        # Try to find cached rate for exact date or nearby dates
        cached_rate = self._get_cached_rate(from_currency, to_currency, rate_date)
        if cached_rate is not None:
            return cached_rate

        # Fetch from API
        return await self._fetch_and_cache_rate(from_currency, to_currency, rate_date)

    def _get_cached_rate(
        self,
        from_currency: str,
        to_currency: str,
        rate_date: date,
    ) -> tuple[Decimal, date] | None:
        """Look for a cached rate, checking nearby dates if needed.

        Checks for rates within MAX_RATE_LOOKBACK_DAYS, preferring exact date,
        then most recent date before the requested date.
        """
        min_date = rate_date - timedelta(days=MAX_RATE_LOOKBACK_DAYS)

        # Look for rates in the date range, ordered by date descending
        cached = (
            self.db.query(CurrencyCache)
            .filter(
                CurrencyCache.base_currency == from_currency,
                CurrencyCache.target_currency == to_currency,
                CurrencyCache.rate_date <= rate_date,
                CurrencyCache.rate_date >= min_date,
            )
            .order_by(CurrencyCache.rate_date.desc())
            .first()
        )

        if cached is not None:
            # Check if cache is fresh enough
            cache_age = datetime.utcnow() - cached.fetched_at
            if cache_age < timedelta(hours=CACHE_FRESHNESS_HOURS):
                return cached.rate, cached.rate_date

        return None

    async def _fetch_and_cache_rate(
        self,
        from_currency: str,
        to_currency: str,
        rate_date: date,
    ) -> tuple[Decimal, date]:
        """Fetch rate from API and cache it.

        The API returns the nearest available rate if exact date is unavailable
        (e.g., weekends return Friday's rate).
        """
        try:
            client = await self._get_client()

            # API format: /YYYY-MM-DD?from=EUR&to=USD
            date_str = rate_date.isoformat()
            response = await client.get(
                f"/{date_str}",
                params={"from": from_currency, "to": to_currency},
            )
            response.raise_for_status()
            data = response.json()

            # API returns: {amount, base, date, rates: {currency: rate}}
            actual_date = date.fromisoformat(data["date"])
            rate = Decimal(str(data["rates"][to_currency]))

            # Cache the rate
            self._cache_rate(from_currency, to_currency, rate, actual_date)

            return rate, actual_date

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Try fetching latest rate as fallback
                return await self._fetch_latest_rate(from_currency, to_currency)
            logger.error(f"API error fetching rate: {e}")
            raise CurrencyServiceError(f"API error: {e}") from e
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch rate: {e}")
            raise CurrencyServiceError(f"Failed to fetch rate: {e}") from e
        except (KeyError, ValueError) as e:
            logger.error(f"Invalid API response: {e}")
            raise CurrencyServiceError(f"Invalid API response: {e}") from e

    async def _fetch_latest_rate(
        self,
        from_currency: str,
        to_currency: str,
    ) -> tuple[Decimal, date]:
        """Fetch the latest available rate as a fallback."""
        try:
            client = await self._get_client()
            response = await client.get(
                "/latest",
                params={"from": from_currency, "to": to_currency},
            )
            response.raise_for_status()
            data = response.json()

            actual_date = date.fromisoformat(data["date"])
            rate = Decimal(str(data["rates"][to_currency]))

            self._cache_rate(from_currency, to_currency, rate, actual_date)

            return rate, actual_date

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch latest rate: {e}")
            raise RateNotFoundError(
                f"No rate found for {from_currency} to {to_currency}"
            ) from e

    def _cache_rate(
        self,
        from_currency: str,
        to_currency: str,
        rate: Decimal,
        rate_date: date,
    ) -> None:
        """Store a rate in the cache, updating if exists."""
        existing = (
            self.db.query(CurrencyCache)
            .filter(
                CurrencyCache.base_currency == from_currency,
                CurrencyCache.target_currency == to_currency,
                CurrencyCache.rate_date == rate_date,
            )
            .first()
        )

        if existing:
            existing.rate = rate
            existing.fetched_at = datetime.utcnow()
        else:
            cache_entry = CurrencyCache(
                base_currency=from_currency,
                target_currency=to_currency,
                rate=rate,
                rate_date=rate_date,
                fetched_at=datetime.utcnow(),
            )
            self.db.add(cache_entry)

        self.db.commit()

    async def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
        expense_date: date,
    ) -> ConversionResult:
        """Convert an amount from one currency to another.

        Args:
            amount: Amount to convert.
            from_currency: Source currency code.
            to_currency: Target currency code.
            expense_date: Date for the exchange rate.

        Returns:
            ConversionResult with all conversion details.

        Raises:
            RateNotFoundError: If no rate could be found.
            CurrencyServiceError: If conversion fails.
        """
        rate, actual_date = await self.get_rate(
            from_currency, to_currency, expense_date
        )
        converted = amount * rate

        # Round to 2 decimal places for currency
        converted = converted.quantize(Decimal("0.01"))

        return ConversionResult(
            original_amount=amount,
            original_currency=from_currency.upper(),
            converted_amount=converted,
            target_currency=to_currency.upper(),
            exchange_rate=rate,
            rate_date=actual_date,
        )


# Synchronous wrapper functions for use in non-async contexts
def get_supported_currencies_sync(db: Session) -> list[Currency]:
    """Synchronous wrapper for getting supported currencies.

    For use in schema validation and other sync contexts.
    Uses cached data if available.
    """
    import asyncio

    service = CurrencyService(db)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context, need to use run_coroutine_threadsafe
            future = asyncio.run_coroutine_threadsafe(
                service.get_supported_currencies(), loop
            )
            return future.result(timeout=10)
        else:
            return loop.run_until_complete(service.get_supported_currencies())
    except RuntimeError:
        # No event loop, create a new one
        return asyncio.run(service.get_supported_currencies())
    finally:
        # Don't close the client here as it may be used again
        pass
