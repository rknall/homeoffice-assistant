# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for rbac_seed_service."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models import Permission, Role, RolePermission
from src.rbac.permissions import CORE_PERMISSIONS
from src.rbac.roles import (
    DEFAULT_ROLES,
    GLOBAL_ADMIN_PERMISSIONS,
    GLOBAL_ADMIN_ROLE,
    MEMBER_PERMISSIONS,
    MEMBER_ROLE,
)
from src.services import rbac_seed_service, rbac_service


def role_codes(db: Session, name: str) -> set[str]:
    """Return the permission codes linked to the role called ``name``."""
    role = rbac_service.get_role_by_name(db, name)
    assert role is not None
    return set(
        db.scalars(
            select(RolePermission.permission_code).where(
                RolePermission.role_id == role.id
            )
        )
    )


def test_seed_creates_default_roles(db_session: Session) -> None:
    rbac_seed_service.seed_rbac_data(db_session)

    names = set(db_session.scalars(select(Role.name)))
    assert names == {role["name"] for role in DEFAULT_ROLES}
    assert role_codes(db_session, GLOBAL_ADMIN_ROLE) == set(GLOBAL_ADMIN_PERMISSIONS)
    assert role_codes(db_session, MEMBER_ROLE) == set(MEMBER_PERMISSIONS)
    member = rbac_service.get_role_by_name(db_session, MEMBER_ROLE)
    assert member is not None and not member.is_system


def test_seed_is_idempotent(db_session: Session) -> None:
    rbac_seed_service.seed_rbac_data(db_session)
    counts = [
        db_session.scalar(select(func.count()).select_from(model))
        for model in (Permission, Role, RolePermission)
    ]

    rbac_seed_service.seed_rbac_data(db_session)

    assert [
        db_session.scalar(select(func.count()).select_from(model))
        for model in (Permission, Role, RolePermission)
    ] == counts
    assert counts[0] == len(CORE_PERMISSIONS)


def test_seed_syncs_global_admin_with_new_core_code(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    rbac_seed_service.seed_rbac_data(db_session)
    new_code = {"code": "report.export", "module": "core", "description": "New"}
    monkeypatch.setattr(
        rbac_seed_service, "CORE_PERMISSIONS", [*CORE_PERMISSIONS, new_code]
    )
    monkeypatch.setattr(
        rbac_seed_service,
        "GLOBAL_ADMIN_PERMISSIONS",
        [*GLOBAL_ADMIN_PERMISSIONS, "report.export"],
    )

    rbac_seed_service.seed_rbac_data(db_session)

    assert "report.export" in role_codes(db_session, GLOBAL_ADMIN_ROLE)
    assert "report.export" not in role_codes(db_session, MEMBER_ROLE)


def test_seed_restores_global_admin_but_keeps_member_edits(
    db_session: Session,
) -> None:
    rbac_seed_service.seed_rbac_data(db_session)
    for name in (GLOBAL_ADMIN_ROLE, MEMBER_ROLE):
        role = rbac_service.get_role_by_name(db_session, name)
        assert role is not None
        db_session.query(RolePermission).filter(
            RolePermission.role_id == role.id,
            RolePermission.permission_code == "event.delete",
        ).delete()
    db_session.commit()

    rbac_seed_service.seed_rbac_data(db_session)

    assert "event.delete" in role_codes(db_session, GLOBAL_ADMIN_ROLE)
    assert "event.delete" not in role_codes(db_session, MEMBER_ROLE)
