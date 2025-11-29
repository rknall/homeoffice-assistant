# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Settings API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.models import User
from src.schemas.settings import LocaleSettingsResponse, LocaleSettingsUpdate
from src.services import settings_service

router = APIRouter()


@router.get("/locale", response_model=LocaleSettingsResponse)
def get_locale_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LocaleSettingsResponse:
    """Get locale settings (date format, time format, timezone)."""
    settings = settings_service.get_locale_settings(db)
    return LocaleSettingsResponse(**settings)


@router.put("/locale", response_model=LocaleSettingsResponse)
def update_locale_settings(
    data: LocaleSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LocaleSettingsResponse:
    """Update locale settings. Admin only."""
    if not current_user.is_admin:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update locale settings",
        )

    settings = settings_service.update_locale_settings(
        db,
        date_format=data.date_format,
        time_format=data.time_format,
        timezone=data.timezone,
    )
    return LocaleSettingsResponse(**settings)
