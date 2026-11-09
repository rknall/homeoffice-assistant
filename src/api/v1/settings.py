# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Settings API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, require_permission
from src.database import get_db
from src.models import User
from src.schemas.settings import (
    CurrencySettingsResponse,
    CurrencySettingsUpdate,
    LocaleSettingsResponse,
    LocaleSettingsUpdate,
)
from src.services import settings_service

router = APIRouter()


@router.get("/locale", response_model=LocaleSettingsResponse)
def get_locale_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LocaleSettingsResponse:
    """Get locale settings (date format, time format, timezone).

    Every page formats dates with these, so any logged-in user may read them.
    """
    settings = settings_service.get_locale_settings(db)
    return LocaleSettingsResponse(**settings)


@router.put("/locale", response_model=LocaleSettingsResponse)
def update_locale_settings(
    data: LocaleSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.settings.write")),
) -> LocaleSettingsResponse:
    """Update locale settings. Admin only."""
    settings = settings_service.update_locale_settings(
        db,
        date_format=data.date_format,
        time_format=data.time_format,
        timezone=data.timezone,
    )
    return LocaleSettingsResponse(**settings)


@router.get("/currency", response_model=CurrencySettingsResponse)
def get_currency_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CurrencySettingsResponse:
    """Get the system-wide base currency.

    Expense amounts are shown in it, so any logged-in user may read it.
    """
    return CurrencySettingsResponse(
        base_currency=settings_service.get_base_currency(db)
    )


@router.put("/currency", response_model=CurrencySettingsResponse)
def update_currency_settings(
    data: CurrencySettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.settings.write")),
) -> CurrencySettingsResponse:
    """Update the system-wide base currency. Admin only."""
    currency = settings_service.set_base_currency(db, data.base_currency)
    return CurrencySettingsResponse(base_currency=currency)
