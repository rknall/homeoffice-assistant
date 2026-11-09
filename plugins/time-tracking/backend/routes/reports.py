# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Report and plugin info routes."""

from uuid import UUID

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, require_permission
from src.database import get_db
from src.models.user import User

from ..schemas import (
    MonthlyReportResponse,
    PluginInfoResponse,
)
from ..services import (
    LeaveBalanceService,
    ReportService,
    TimeEntryService,
    TimeTrackingConfig,
    plugin_name,
    plugin_version,
)
from .common import (
    PLUGIN_ID,
    REPORTS_READ,
    get_plugin_config,
    router,
)


@router.get("/reports/monthly", response_model=MonthlyReportResponse)
def get_monthly_report(
    year: int,
    month: int = Query(ge=1, le=12),
    company_id: UUID | None = None,
    db: Session = Depends(get_db),
    config: TimeTrackingConfig = Depends(get_plugin_config),
    current_user: User = Depends(
        require_permission(REPORTS_READ, company_id_param="company_id")
    ),
) -> MonthlyReportResponse:
    """Get monthly report summary."""
    return ReportService(db, config).monthly_report(
        current_user, year, month, company_id
    )


# --- Plugin Info Endpoint ---


@router.get("/info", response_model=PluginInfoResponse)
def get_plugin_info(
    db: Session = Depends(get_db),
    config: TimeTrackingConfig = Depends(get_plugin_config),
    current_user: User = Depends(get_current_user),
) -> PluginInfoResponse:
    """Get plugin information and summary."""
    leave_service = LeaveBalanceService(db, config)
    current_balance = leave_service.find_current_balance(current_user.id)

    return PluginInfoResponse(
        plugin_id=PLUGIN_ID,
        plugin_name=plugin_name(),
        version=plugin_version(),
        entry_count=TimeEntryService(db, config).count_entries(current_user.id),
        current_balance=(
            leave_service.to_response(current_balance) if current_balance else None
        ),
    )
