# src/services/rbac_service.py
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Session, joinedload

from src.models import Permission, Role, RolePermission, User, UserRole


def user_has_permission(
    db: Session, user: User, permission_code: str, company_id: uuid.UUID | None = None
) -> bool:
    """Check if a user has a specific permission."""
    if not user.is_active:
        return False

    # Global admin has all permissions
    if is_global_admin(db, user):
        return True

    permissions = get_user_permissions(db, user, company_id)
    return permission_code in permissions


def is_global_admin(db: Session, user: User) -> bool:
    """Check for global admin role."""
    global_admin_role = get_role_by_name(db, "Global Admin")
    if not global_admin_role:
        return False

    for user_role in user.user_roles:
        if user_role.role_id == global_admin_role.id and user_role.company_id is None:
            return True
    return False


def get_user_permissions(
    db: Session, user: User, company_id: uuid.UUID | None = None
) -> set[str]:
    """Get a set of all permission codes for a user.

    If company_id is provided, it includes permissions from global roles
    and company-specific roles for that company.
    If company_id is None, it only includes permissions from global roles.
    """
    permission_codes = set()

    # Get permissions from global roles
    global_roles = (
        db.query(UserRole)
        .filter(UserRole.user_id == user.id, UserRole.company_id is None)
        .all()
    )
    for user_role in global_roles:
        role_permissions = (
            db.query(RolePermission)
            .filter(RolePermission.role_id == user_role.role_id)
            .all()
        )
        for rp in role_permissions:
            permission_codes.add(rp.permission_code)

    # Get permissions from company-specific roles
    if company_id:
        company_roles = (
            db.query(UserRole)
            .filter(UserRole.user_id == user.id, UserRole.company_id == company_id)
            .all()
        )
        for user_role in company_roles:
            role_permissions = (
                db.query(RolePermission)
                .filter(RolePermission.role_id == user_role.role_id)
                .all()
            )
            for rp in role_permissions:
                permission_codes.add(rp.permission_code)

    return permission_codes


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
            sa.or_(UserRole.company_id is None, UserRole.company_id == company_id)
        )
    else:
        user_roles_query = user_roles_query.filter(UserRole.company_id is None)

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

    # Get all user role assignments
    user_roles = db.query(UserRole).filter(UserRole.user_id == user.id).all()

    for user_role in user_roles:
        # Get permissions for this role
        role_perms = (
            db.query(RolePermission)
            .filter(RolePermission.role_id == user_role.role_id)
            .all()
        )
        perm_codes = {rp.permission_code for rp in role_perms}

        if user_role.company_id is None:
            # Global role
            global_permissions.update(perm_codes)
        else:
            # Company-scoped role
            company_id_str = str(user_role.company_id)
            if company_id_str not in company_permissions:
                company_permissions[company_id_str] = set()
            company_permissions[company_id_str].update(perm_codes)

    return {
        "global_permissions": list(global_permissions),
        "company_permissions": {k: list(v) for k, v in company_permissions.items()},
    }
