# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Leave balance routes."""

from datetime import date
from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session

from src.api.deps import require_permission
from src.database import get_db
from src.models.user import User

from ..schemas import (
    LeaveBalanceResponse,
    LeaveBalanceUpdate,
)
from ..services import (
    LeaveBalanceService,
    TimeTrackingConfig,
)
from .common import (
    RECORDS_READ,
    RECORDS_WRITE,
    get_plugin_config,
    router,
)


@router.get("/leave-balance", response_model=LeaveBalanceResponse)
def get_leave_balance(
    year: int | None = None,
    company_id: UUID | None = None,
    db: Session = Depends(get_db),
    config: TimeTrackingConfig = Depends(get_plugin_config),
    current_user: User = Depends(
        require_permission(RECORDS_READ, company_id_param="company_id")
    ),
) -> LeaveBalanceResponse:
    """Get leave balance for a year."""
    service = LeaveBalanceService(db, config)
    balance = service.get_balance(
        current_user.id, year or date.today().year, company_id
    )
    return service.to_response(balance)


@router.put("/leave-balance", response_model=LeaveBalanceResponse)
def update_leave_balance(
    data: LeaveBalanceUpdate,
    year: int | None = None,
    company_id: UUID | None = None,
    db: Session = Depends(get_db),
    config: TimeTrackingConfig = Depends(get_plugin_config),
    current_user: User = Depends(
        require_permission(RECORDS_WRITE, company_id_param="company_id")
    ),
) -> LeaveBalanceResponse:
    """Update leave balance settings."""
    service = LeaveBalanceService(db, config)
    balance = service.update_balance(
        user_id=current_user.id,
        year=year or date.today().year,
        company_id=company_id,
        vacation_entitled=data.vacation_entitled,
        vacation_carryover=data.vacation_carryover,
    )
    return service.to_response(balance)


# --- Company Settings Endpoints ---
