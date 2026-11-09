# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Role and permission queries and assignments."""

import logging
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Session, joinedload

from src.models import Permission, Role, RolePermission, User, UserRole
from src.plugins.base import ProvidedPermission
from src.rbac.roles import MEMBER_ROLE

SYSTEM_ADMIN_PERMISSION = "system.admin"

logger = logging.getLogger(__name__)


def user_has_permission(
    db: Session, user: User, permission_code: str, company_id: uuid.UUID | None = None
) -> bool:
    """Check if a user holds a permission globally or for a company.

    Args:
        db: Database session.
        user: The user to check.
        permission_code: Permission code, e.g. "event.read".
        company_id: Company the check is scoped to. None checks global roles
            only.

    Returns:
        True when the user is active and holds the code.
    """
    if not user.is_active:
        return False
    if is_global_admin(db, user):
        return True
    return permission_code in get_user_permissions(db, user, company_id)


def is_global_admin(db: Session, user: User) -> bool:
    """Check whether the user holds a system role globally.

    Args:
        db: Database session.
        user: The user to check.

    Returns:
        True when a global assignment of an ``is_system`` role exists.
    """
    query = (
        sa.select(UserRole.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(
            UserRole.user_id == user.id,
            UserRole.company_id.is_(None),
            Role.is_system,
        )
        .limit(1)
    )
    return db.scalar(query) is not None


def get_user_permissions(
    db: Session, user: User, company_id: uuid.UUID | None = None
) -> set[str]:
    """Get the permission codes a user holds.

    Args:
        db: Database session.
        user: The user whose roles are resolved.
        company_id: When given, roles scoped to this company count as well as
            global roles. When None, only global roles count.

    Returns:
        The set of permission codes.
    """
    scope = UserRole.company_id.is_(None)
    if company_id is not None:
        scope = sa.or_(scope, UserRole.company_id == company_id)
    query = (
        sa.select(RolePermission.permission_code)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user.id, scope)
        .distinct()
    )
    return set(db.scalars(query))


def companies_with_permission(
    db: Session, user: User, permission_code: str
) -> set[uuid.UUID] | None:
    """Get the companies in which a user holds a permission.

    List routes without a company id use this to filter their results.

    Args:
        db: Database session.
        user: The user to check.
        permission_code: Permission code, e.g. "company.view".

    Returns:
        None when the user holds the code globally (or is a Global Admin), so
        no company filter applies. Otherwise the ids of the companies whose
        scoped roles grant the code; an empty set means no access.
    """
    if not user.is_active:
        return set()
    if is_global_admin(db, user):
        return None
    query = (
        sa.select(UserRole.company_id)
        .join(RolePermission, RolePermission.role_id == UserRole.role_id)
        .where(
            UserRole.user_id == user.id,
            RolePermission.permission_code == permission_code,
        )
        .distinct()
    )
    company_ids = set(db.scalars(query))
    if None in company_ids:
        return None
    return company_ids


def get_user_roles(
    db: Session, user: User, company_id: uuid.UUID | None = None
) -> list[Role]:
    """Get a list of all roles for a user.

    If company_id is provided, it includes global roles and company-specific roles.
    If company_id is None, it only includes global roles.
    """
    roles = []
    user_roles_query = db.query(UserRole).filter(UserRole.user_id == user.id)
    if company_id:
        user_roles_query = user_roles_query.filter(
            sa.or_(UserRole.company_id.is_(None), UserRole.company_id == company_id)
        )
    else:
        user_roles_query = user_roles_query.filter(UserRole.company_id.is_(None))

    for user_role in user_roles_query.options(joinedload(UserRole.role)).all():
        roles.append(user_role.role)

    return roles


def assign_role_to_user(
    db: Session,
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    company_id: uuid.UUID | None = None,
    assigned_by: User | None = None,
) -> UserRole:
    """Assign a role to a user."""
    user_role = UserRole(
        user_id=user_id,
        role_id=role_id,
        company_id=company_id,
        assigned_by_id=assigned_by.id if assigned_by else None,
    )
    db.add(user_role)
    db.commit()
    return user_role


def remove_role_from_user(
    db: Session,
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    company_id: uuid.UUID | None = None,
) -> bool:
    """Remove a role from a user. Returns True if removed, False if not found."""
    user_role = (
        db.query(UserRole)
        .filter(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
            UserRole.company_id == company_id,
        )
        .first()
    )

    if user_role:
        db.delete(user_role)
        db.commit()
        return True
    return False


def get_role_by_name(db: Session, name: str) -> Role | None:
    """Get a role by its name."""
    return db.query(Role).filter(Role.name == name).first()


def assign_member_role(db: Session, user_id: uuid.UUID) -> UserRole | None:
    """Give a user the default Member role globally.

    Args:
        db: Database session.
        user_id: The user that gets the role.

    Returns:
        The new assignment, or None when the Member role does not exist.
    """
    member = get_role_by_name(db, MEMBER_ROLE)
    if member is None:
        logger.warning(
            "Role %r not found; user %s gets no default role", MEMBER_ROLE, user_id
        )
        return None
    return assign_role_to_user(db, user_id=user_id, role_id=member.id)


def role_grants_system_admin(db: Session, role: Role) -> bool:
    """Check whether holding a role makes a user a system administrator.

    Args:
        db: Database session.
        role: The role to check.

    Returns:
        True for a system role or a role linked to ``system.admin``.
    """
    if role.is_system:
        return True
    query = sa.select(RolePermission.role_id).where(
        RolePermission.role_id == role.id,
        RolePermission.permission_code == SYSTEM_ADMIN_PERMISSION,
    )
    return db.scalar(query.limit(1)) is not None


def can_assign_role(db: Session, actor: User, role: Role) -> bool:
    """Check whether a user may assign or remove a role.

    Roles that grant system administration need ``system.admin`` themselves,
    so ``user.manage`` alone cannot be used to escalate.

    Args:
        db: Database session.
        actor: The user performing the change.
        role: The role being assigned or removed.

    Returns:
        True when the actor may hand out the role.
    """
    if not role_grants_system_admin(db, role):
        return True
    return user_has_permission(db, actor, SYSTEM_ADMIN_PERMISSION)


def can_manage_user(db: Session, actor: User, target: User) -> bool:
    """Check whether a user may edit another user's account or roles.

    Users who hold ``system.admin`` can only be changed by a user who holds
    it as well.

    Args:
        db: Database session.
        actor: The user performing the change.
        target: The user being changed.

    Returns:
        True when the actor may change the target.
    """
    if not user_has_permission(db, target, SYSTEM_ADMIN_PERMISSION):
        return True
    return user_has_permission(db, actor, SYSTEM_ADMIN_PERMISSION)


def get_system_roles(db: Session) -> list[Role]:
    """Get the system roles, such as Global Admin.

    Args:
        db: Database session.

    Returns:
        Every role with ``is_system`` set.
    """
    return list(db.scalars(sa.select(Role).where(Role.is_system)))


def register_permission(
    db: Session, code: str, module: str, description: str | None = None
) -> Permission:
    """Register a new permission if it does not already exist."""
    permission = db.query(Permission).filter(Permission.code == code).first()
    if not permission:
        permission = Permission(code=code, module=module, description=description)
        db.add(permission)
        db.commit()
    return permission


def get_user_all_permissions(db: Session, user: User) -> dict:
    """Get all permissions for a user, organized by scope.

    Returns a dict with:
      - global_permissions: list of permission codes from global roles
      - company_permissions: dict mapping company_id to list of permission codes
    """
    global_permissions: set[str] = set()
    company_permissions: dict[str, set[str]] = {}

    rows = db.execute(
        sa.select(UserRole.company_id, RolePermission.permission_code)
        .join(RolePermission, RolePermission.role_id == UserRole.role_id)
        .where(UserRole.user_id == user.id)
    )
    for company_id, code in rows:
        if company_id is None:
            global_permissions.add(code)
        else:
            company_permissions.setdefault(str(company_id), set()).add(code)

    return {
        "global_permissions": list(global_permissions),
        "company_permissions": {k: list(v) for k, v in company_permissions.items()},
    }


def register_plugin_permissions(
    db: Session,
    plugin_id: str,
    permissions: list[ProvidedPermission],
) -> list[Permission]:
    """Register permissions provided by a plugin.

    This creates permission records in the database with the plugin_id set.
    These permissions can then be assigned to roles.

    Args:
        db: Database session
        plugin_id: The plugin's unique identifier
        permissions: List of permissions the plugin provides

    Returns:
        List of created/existing Permission objects
    """
    registered: list[Permission] = []

    for prov_perm in permissions:
        # Check if permission already exists
        existing = (
            db.query(Permission).filter(Permission.code == prov_perm.code).first()
        )

        if existing:
            # Update if exists but belongs to same plugin
            if existing.plugin_id == plugin_id:
                existing.description = prov_perm.description
                registered.append(existing)
            else:
                logger.warning(
                    f"Permission '{prov_perm.code}' already exists "
                    f"(plugin_id={existing.plugin_id}), skipping"
                )
        else:
            # Create new permission
            permission = Permission(
                code=prov_perm.code,
                module=plugin_id,  # Use plugin_id as module
                description=prov_perm.description,
                plugin_id=plugin_id,
            )
            db.add(permission)
            db.flush()
            _grant_to_default_roles(db, prov_perm)
            registered.append(permission)
            logger.info(f"Registered plugin permission: {prov_perm.code}")

    db.commit()
    return registered


def _grant_to_default_roles(db: Session, prov_perm: ProvidedPermission) -> None:
    """Link a newly registered plugin permission to the default roles.

    Runs only when the permission row is created, so an admin who later
    removes the code from Member does not see it come back.

    Args:
        db: Database session.
        prov_perm: The plugin permission that was just created.
    """
    roles = get_system_roles(db)
    if prov_perm.member_default:
        member = get_role_by_name(db, MEMBER_ROLE)
        if member is not None:
            roles.append(member)
    for role in roles:
        db.add(RolePermission(role_id=role.id, permission_code=prov_perm.code))


def unregister_plugin_permissions(
    db: Session,
    plugin_id: str,
) -> int:
    """Remove all permissions provided by a plugin.

    This also removes any role-permission associations for these permissions.

    Args:
        db: Database session
        plugin_id: The plugin's unique identifier

    Returns:
        Number of permissions removed
    """
    # Find all permissions for this plugin
    plugin_permissions = (
        db.query(Permission).filter(Permission.plugin_id == plugin_id).all()
    )

    count = len(plugin_permissions)

    for permission in plugin_permissions:
        # Remove role associations first (CASCADE should handle this, but be explicit)
        db.query(RolePermission).filter(
            RolePermission.permission_code == permission.code
        ).delete(synchronize_session=False)

        # Remove the permission
        db.delete(permission)
        logger.info(f"Unregistered plugin permission: {permission.code}")

    db.commit()
    return count
