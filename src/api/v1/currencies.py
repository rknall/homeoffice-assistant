# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Currency API endpoints."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.models import User
from src.services.currency_service import (
    CurrencyService,
    CurrencyServiceError,
    RateNotFoundError,
)

router = APIRouter()


class CurrencyResponse(BaseModel):
    """Currency information response."""

    code: str
    name: str


class ExchangeRateResponse(BaseModel):
    """Exchange rate response."""

    from_currency: str
    to_currency: str
    rate: str
    rate_date: str


@router.get("/currencies", response_model=list[CurrencyResponse])
async def list_currencies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CurrencyResponse]:
    """Get list of supported currencies.

    Returns all currencies supported by the exchange rate API.
    """
    service = CurrencyService(db)
    try:
        currencies = await service.get_supported_currencies()
        return [
            CurrencyResponse(code=c.code, name=c.name)
            for c in currencies
        ]
    except CurrencyServiceError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Currency service unavailable: {e}",
        ) from e
    finally:
        await service.close()


@router.get("/currencies/rate", response_model=ExchangeRateResponse)
async def get_exchange_rate(
    from_currency: str = Query(..., min_length=3, max_length=3, alias="from"),
    to_currency: str = Query(..., min_length=3, max_length=3, alias="to"),
    rate_date: date | None = Query(None, alias="date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExchangeRateResponse:
    """Get exchange rate between two currencies."""
    if rate_date is None:
        rate_date = date.today()

    service = CurrencyService(db)
    try:
        rate, actual_date = await service.get_rate(
            from_currency.upper(),
            to_currency.upper(),
            rate_date,
        )
        return ExchangeRateResponse(
            from_currency=from_currency.upper(),
            to_currency=to_currency.upper(),
            rate=str(rate),
            rate_date=actual_date.isoformat(),
        )
    except RateNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        ) from e
    except CurrencyServiceError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Currency service unavailable: {e}",
        ) from e
    finally:
        await service.close()
