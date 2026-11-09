# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Role and permission administration routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, permission_denied, require_permission
from src.database import get_db
from src.models import Permission, Role, RolePermission, User, UserRole
from src.schemas.rbac import (
    PermissionSchema,
    RoleCreateSchema,
    RoleSchema,
    RoleUpdateSchema,
    RoleWithPermissionsSchema,
    UserPermissionsSchema,
    UserRoleAssignmentSchema,
    UserRoleSchema,
)
from src.services import rbac_service, role_admin_service

router = APIRouter()


def _check_role_change_allowed(
    db: Session, actor: User, target: User, role: Role
) -> None:
    """Reject role changes that would let user.manage escalate privileges.

    Args:
        db: Database session.
        actor: The user making the change.
        target: The user whose roles change.
        role: The role being assigned or removed.

    Raises:
        HTTPException: 403 when the change requires system.admin.
    """
    if not rbac_service.can_assign_role(
        db, actor, role
    ) or not rbac_service.can_manage_user(db, actor, target):
        raise permission_denied("system.admin")


@router.get(
    "/rbac/permissions",
    response_model=list[PermissionSchema],
    summary="List all available permissions",
)
def list_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin")),
) -> list[Permission]:
    """Retrieve a list of all available permissions in the system.

    Requires system.admin permission.
    """
    permissions = db.query(Permission).all()
    return permissions


@router.get("/rbac/roles", response_model=list[RoleSchema], summary="List all roles")
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin")),
) -> list[Role]:
    """Retrieve a list of all roles in the system.

    Requires system.admin permission.
    """
    roles = db.query(Role).all()
    return roles


@router.get(
    "/rbac/roles/{role_id}",
    response_model=RoleWithPermissionsSchema,
    summary="Get a role by ID with its permissions",
)
def get_role(
    role_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin")),
) -> RoleWithPermissionsSchema:
    """Retrieve a specific role by its ID, including all associated permissions.

    Requires system.admin permission.
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    permissions = (
        db.query(Permission)
        .join(RolePermission)
        .filter(RolePermission.role_id == role_id)
        .all()
    )

    # Manually construct the response to include permissions
    return RoleWithPermissionsSchema(
        id=role.id,
        name=role.name,
        is_system=role.is_system,
        description=role.description,
        permissions=[PermissionSchema.model_validate(p) for p in permissions],
    )


@router.post(
    "/rbac/roles",
    response_model=RoleSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new custom role",
)
def create_role(
    role_in: RoleCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin")),
) -> Role:
    """Create a new custom role with specified permissions.

    Requires system.admin permission.
    """
    try:
        return role_admin_service.create_role(
            db, role_in.name, role_in.description, role_in.permissions
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put(
    "/rbac/roles/{role_id}",
    response_model=RoleSchema,
    summary="Update an existing role",
)
def update_role(
    role_id: uuid.UUID,
    role_in: RoleUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin")),
) -> Role:
    """Update an existing role's name, description, and permissions.

    System roles cannot be modified.
    Requires system.admin permission.
    """
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=403, detail="System roles cannot be modified")
    try:
        return role_admin_service.update_role(
            db,
            role,
            name=role_in.name,
            description=role_in.description,
            permission_codes=role_in.permissions,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete(
    "/rbac/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a custom role",
)
def delete_role(
    role_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin")),
) -> None:
    """Delete a role. System roles cannot be deleted.

    Requires system.admin permission.
    """
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    try:
        role_admin_service.delete_role(db, role)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


@router.get(
    "/rbac/users/{user_id}/roles",
    response_model=list[UserRoleSchema],
    summary="Get a user's role assignments",
)
def get_user_role_assignments(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user.manage")),
) -> list[UserRole]:
    """Retrieve all role assignments for a specific user.

    Requires user.manage permission.
    """
    user_roles = db.query(UserRole).filter(UserRole.user_id == user_id).all()
    return user_roles


@router.post(
    "/rbac/users/{user_id}/roles",
    response_model=UserRoleSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a role to a user",
)
def assign_role_to_user_api(
    user_id: uuid.UUID,
    assignment: UserRoleAssignmentSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user.manage")),
) -> UserRole:
    """Assign a role to a user, optionally scoped to a company.

    Requires user.manage permission. Assigning a role that grants system
    administration, or changing a user who holds it, requires system.admin.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    role = db.query(Role).filter(Role.id == assignment.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    _check_role_change_allowed(db, current_user, user, role)

    # Check for existing assignment
    existing_assignment = (
        db.query(UserRole)
        .filter(
            UserRole.user_id == user_id,
            UserRole.role_id == assignment.role_id,
            UserRole.company_id == assignment.company_id,
        )
        .first()
    )
    if existing_assignment:
        raise HTTPException(
            status_code=400, detail="User already has this role assignment"
        )

    user_role = rbac_service.assign_role_to_user(
        db,
        user_id=user_id,
        role_id=assignment.role_id,
        company_id=assignment.company_id,
        assigned_by=current_user,
    )
    db.refresh(user_role)
    return user_role


@router.delete(
    "/rbac/users/{user_id}/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a role from a user",
)
def remove_role_from_user_api(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    company_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user.manage")),
) -> None:
    """Remove a role assignment from a user.

    Requires user.manage permission. Removing a role that grants system
    administration, or changing a user who holds it, requires system.admin.
    """
    user = db.get(User, user_id)
    role = db.get(Role, role_id)
    if user is not None and role is not None:
        _check_role_change_allowed(db, current_user, user, role)
    success = rbac_service.remove_role_from_user(db, user_id, role_id, company_id)
    if not success:
        raise HTTPException(status_code=404, detail="Role assignment not found")
    return


@router.get(
    "/rbac/me/permissions",
    response_model=UserPermissionsSchema,
    summary="Get current user's effective permissions",
)
def get_my_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserPermissionsSchema:
    """Retrieve the effective permissions for the current user.

    Permissions are both globally and per company.
    """
    global_permissions = rbac_service.get_user_permissions(
        db, current_user, company_id=None
    )

    # For company-specific permissions, we need to find all companies
    # the user has roles for
    user_companies = (
        db.query(UserRole.company_id)
        .filter(UserRole.user_id == current_user.id, UserRole.company_id.isnot(None))
        .distinct()
        .all()
    )

    company_permissions = {}
    for company_id_tuple in user_companies:
        company_id = company_id_tuple[0]
        if company_id:
            company_permissions[str(company_id)] = list(
                rbac_service.get_user_permissions(db, current_user, company_id)
            )

    return UserPermissionsSchema(
        global_permissions=list(global_permissions),
        company_permissions=company_permissions,
    )
