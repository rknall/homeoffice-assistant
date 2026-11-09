# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Seeding of core permissions and default roles."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import Permission, Role, RolePermission
from src.rbac.permissions import CORE_PERMISSIONS
from src.rbac.roles import DEFAULT_ROLES, GLOBAL_ADMIN_PERMISSIONS

from . import rbac_service


def seed_rbac_data(db: Session) -> None:
    """Seed core permissions and default roles, and sync Global Admin.

    Runs on every start and is idempotent. A default role gets its permission
    links only when it is created, so an admin's later edits to it are kept.
    The system role is the exception: it is linked to every core permission on
    each run, so a core code added in a release reaches existing installs.

    Args:
        db: Database session.
    """
    existing_codes = set(db.scalars(select(Permission.code)))
    for perm_data in CORE_PERMISSIONS:
        if perm_data["code"] not in existing_codes:
            db.add(Permission(**perm_data))
    db.flush()

    for role_data in DEFAULT_ROLES:
        if rbac_service.get_role_by_name(db, role_data["name"]):
            continue
        role = Role(
            name=role_data["name"],
            is_system=role_data["is_system"],
            description=role_data["description"],
        )
        db.add(role)
        db.flush()
        for perm_code in role_data["permissions"]:
            db.add(RolePermission(role_id=role.id, permission_code=perm_code))

    _sync_global_admin(db)
    db.commit()


def _sync_global_admin(db: Session) -> None:
    """Link every system role to each core permission it does not hold yet.

    Args:
        db: Database session.
    """
    db.flush()
    for role in db.scalars(select(Role).where(Role.is_system)):
        held = set(
            db.scalars(
                select(RolePermission.permission_code).where(
                    RolePermission.role_id == role.id
                )
            )
        )
        for code in GLOBAL_ADMIN_PERMISSIONS:
            if code not in held:
                db.add(RolePermission(role_id=role.id, permission_code=code))
