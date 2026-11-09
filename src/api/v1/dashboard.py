# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Dashboard API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.deps import require_permission
from src.database import get_db
from src.models import User
from src.schemas.dashboard import DashboardSummary
from src.services import dashboard_service

router = APIRouter()

# The summary covers the caller's own events, so holding event.read in any
# company (or globally) is enough to open it.
read_events = require_permission("event.read", company_id_param="company_id")


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(read_events),
) -> DashboardSummary:
    """Get aggregated dashboard summary for the current user.

    Returns counts by event status, upcoming events, events needing reports,
    incomplete todos, and expense breakdown for the last 90 days.
    """
    return dashboard_service.get_dashboard_summary(db, current_user.id)
