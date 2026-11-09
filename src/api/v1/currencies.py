# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Currency API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.deps import get_current_user
from src.database import get_db
from src.integrations.failure import failure_category
from src.models import User
from src.schemas.currency import CurrencyResponse
from src.services.currency_service import CurrencyService, CurrencyServiceError

router = APIRouter()


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
        return [CurrencyResponse(code=c.code, name=c.name) for c in currencies]
    except CurrencyServiceError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Currency service unavailable: {failure_category(e)}",
        ) from e
    finally:
        await service.close()
