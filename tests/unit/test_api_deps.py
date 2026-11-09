# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for the shared permission check in src.api.deps."""

import pytest
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import ensure_permission, permission_denied
from src.models import Company, User
from src.models.enums import CompanyType


def test_permission_denied_builds_403_with_code() -> None:
    """The error carries 403 and the missing code in the detail."""
    error = permission_denied("event.write")

    assert error.status_code == status.HTTP_403_FORBIDDEN
    assert error.detail == "Permission denied: event.write"


def test_ensure_permission_passes_for_global_holder(
    db_session: Session, admin_user: User
) -> None:
    """A globally held code passes without a company."""
    ensure_permission(db_session, admin_user, "system.admin")


def test_ensure_permission_passes_for_company_holder(
    db_session: Session, company_viewer_user: User, viewer_company: Company
) -> None:
    """A code held in a company passes for that company."""
    ensure_permission(
        db_session, company_viewer_user, "company.view", viewer_company.id
    )


def test_ensure_permission_rejects_user_without_code(
    db_session: Session, test_user: User
) -> None:
    """A user lacking the code gets 403 with the code in the detail."""
    with pytest.raises(HTTPException) as exc_info:
        ensure_permission(db_session, test_user, "system.admin")

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "Permission denied: system.admin"


def test_ensure_permission_rejects_other_company(
    db_session: Session, company_viewer_user: User
) -> None:
    """A company-scoped holder is refused for another company."""
    other = Company(name="Other Company", type=CompanyType.EMPLOYER)
    db_session.add(other)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        ensure_permission(db_session, company_viewer_user, "company.view", other.id)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "Permission denied: company.view"
