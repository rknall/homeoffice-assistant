# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Shared route constants and helpers."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import ensure_permission
from src.models.user import User
from src.plugins.registry import PluginRegistry

from ..services import (
    TimeTrackingConfig,
)

router = APIRouter()

PLUGIN_ID = "time-tracking"

RECORDS_READ = "time-tracking.records.read"
RECORDS_WRITE = "time-tracking.records.write"
RECORDS_DELETE = "time-tracking.records.delete"
REPORTS_READ = "time-tracking.reports.read"
SETTINGS_WRITE = "time-tracking.settings.write"


def get_plugin_config() -> TimeTrackingConfig:
    """Return the live plugin settings, or the defaults when not loaded."""
    plugin = PluginRegistry.get_instance().get_plugin(PLUGIN_ID)
    return TimeTrackingConfig.from_settings(plugin.config.settings if plugin else {})


def require_company_code(
    db: Session, user: User, code: str, company_id: str | None
) -> UUID | None:
    """Check a permission for a company id taken from a request body.

    Routes whose company id arrives in the body cannot use
    ``require_permission``, which only sees path and query params.

    Args:
        db: Database session.
        user: The current user.
        code: Permission code the user must hold.
        company_id: Company id from the body; None checks global roles only.

    Returns:
        The parsed company id, or None when the body carries none.

    Raises:
        HTTPException: 422 for a malformed company id, 403 when the user
            lacks the code.
    """
    try:
        company_uuid = UUID(company_id) if company_id else None
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid company_id",
        ) from None
    ensure_permission(db, user, code, company_uuid)
    return company_uuid
