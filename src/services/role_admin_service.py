# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Administration of custom roles: create, update, delete, permission links."""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Session

from src.models import Permission, Role, RolePermission
from src.services import rbac_service


def _check_role_name(db: Session, name: str, role_id: uuid.UUID | None) -> None:
    """Reject a role name that is reserved or already taken.

    Args:
        db: Database session.
        name: The requested role name.
        role_id: The role being renamed, or None for a new role.

    Raises:
        ValueError: When a system role uses the name or another role has it.
    """
    if any(role.name == name for role in rbac_service.get_system_roles(db)):
        raise ValueError(f"Cannot use reserved role name '{name}'")
    existing = rbac_service.get_role_by_name(db, name)
    if existing is not None and existing.id != role_id:
        raise ValueError("Role with this name already exists")


def _set_role_permissions(db: Session, role: Role, codes: list[str]) -> None:
    """Replace the permissions linked to a role.

    Args:
        db: Database session.
        role: The role whose links are replaced.
        codes: The permission codes the role holds afterwards.

    Raises:
        ValueError: When a code does not exist.
    """
    known = set(
        db.scalars(sa.select(Permission.code).where(Permission.code.in_(codes)))
    )
    for code in codes:
        if code not in known:
            raise ValueError(f"Permission '{code}' not found")
    db.execute(sa.delete(RolePermission).where(RolePermission.role_id == role.id))
    for code in dict.fromkeys(codes):
        db.add(RolePermission(role_id=role.id, permission_code=code))


def create_role(
    db: Session, name: str, description: str | None, permission_codes: list[str]
) -> Role:
    """Create a custom (non-system) role.

    Args:
        db: Database session.
        name: Role name; must not be taken or used by a system role.
        description: Optional description.
        permission_codes: Codes of existing permissions to link.

    Returns:
        The created role.

    Raises:
        ValueError: When the name is reserved or taken, or a code is unknown.
    """
    _check_role_name(db, name, None)
    role = Role(name=name, description=description, is_system=False)
    db.add(role)
    db.flush()
    try:
        _set_role_permissions(db, role, permission_codes)
    except ValueError:
        db.rollback()
        raise
    db.commit()
    db.refresh(role)
    return role


def update_role(
    db: Session,
    role: Role,
    name: str | None = None,
    description: str | None = None,
    permission_codes: list[str] | None = None,
) -> Role:
    """Update a custom role; arguments left as None are not changed.

    Args:
        db: Database session.
        role: The role to change; must not be a system role.
        name: New name.
        description: New description.
        permission_codes: New full list of permission codes.

    Returns:
        The updated role.

    Raises:
        ValueError: When the role is a system role, the name is reserved or
            taken, or a code is unknown.
    """
    if role.is_system:
        raise ValueError("System roles cannot be modified")
    try:
        if name:
            _check_role_name(db, name, role.id)
            role.name = name
        if description is not None:
            role.description = description
        if permission_codes is not None:
            _set_role_permissions(db, role, permission_codes)
    except ValueError:
        db.rollback()
        raise
    db.commit()
    db.refresh(role)
    return role


def delete_role(db: Session, role: Role) -> None:
    """Delete a custom role with its permission links and assignments.

    Args:
        db: Database session.
        role: The role to delete; must not be a system role.

    Raises:
        ValueError: When the role is a system role.
    """
    if role.is_system:
        raise ValueError("System roles cannot be deleted")
    db.delete(role)
    db.commit()
