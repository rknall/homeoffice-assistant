# src/api/v1/rbac.py
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db, require_permission
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
from src.services import rbac_service

router = APIRouter()

@router.get("/rbac/permissions", response_model=list[PermissionSchema], summary="List all available permissions")
def list_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin")),
):
    """Retrieve a list of all available permissions in the system.
    Requires system.admin permission.
    """
    permissions = db.query(Permission).all()
    return permissions

@router.get("/rbac/roles", response_model=list[RoleSchema], summary="List all roles")
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin")),
):
    """Retrieve a list of all roles in the system.
    Requires system.admin permission.
    """
    roles = db.query(Role).all()
    return roles

@router.get("/rbac/roles/{role_id}", response_model=RoleWithPermissionsSchema, summary="Get a role by ID with its permissions")
def get_role(
    role_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin")),
):
    """Retrieve a specific role by its ID, including all associated permissions.
    Requires system.admin permission.
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    permissions = db.query(Permission).join(RolePermission).filter(RolePermission.role_id == role_id).all()

    # Manually construct the response to include permissions
    role_dict = role.__dict__
    role_dict["permissions"] = [PermissionSchema.from_orm(p) for p in permissions]
    return RoleWithPermissionsSchema(**role_dict)


@router.post("/rbac/roles", response_model=RoleSchema, status_code=status.HTTP_201_CREATED, summary="Create a new custom role")
def create_role(
    role_in: RoleCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin")),
):
    """Create a new custom role with specified permissions.
    Requires system.admin permission.
    """
    existing_role = rbac_service.get_role_by_name(db, role_in.name)
    if existing_role:
        raise HTTPException(status_code=400, detail="Role with this name already exists")

    role = Role(name=role_in.name, description=role_in.description, is_system=False)
    db.add(role)
    db.flush() # To get role.id

    for perm_code in role_in.permissions:
        permission = db.query(Permission).filter(Permission.code == perm_code).first()
        if not permission:
            raise HTTPException(status_code=400, detail=f"Permission '{perm_code}' not found")
        role_permission = RolePermission(role_id=role.id, permission_code=permission.code)
        db.add(role_permission)

    db.commit()
    db.refresh(role)
    return role

@router.put("/rbac/roles/{role_id}", response_model=RoleSchema, summary="Update an existing role")
def update_role(
    role_id: uuid.UUID,
    role_in: RoleUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin")),
):
    """Update an existing custom role's name, description, and permissions.
    System roles cannot be modified.
    Requires system.admin permission.
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=403, detail="System roles cannot be modified")

    if role_in.name:
        existing_role = rbac_service.get_role_by_name(db, role_in.name)
        if existing_role and existing_role.id != role_id:
            raise HTTPException(status_code=400, detail="Role with this name already exists")
        role.name = role_in.name

    if role_in.description is not None:
        role.description = role_in.description

    if role_in.permissions is not None:
        # Clear existing permissions
        db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
        db.flush()

        # Add new permissions
        for perm_code in role_in.permissions:
            permission = db.query(Permission).filter(Permission.code == perm_code).first()
            if not permission:
                raise HTTPException(status_code=400, detail=f"Permission '{perm_code}' not found")
            role_permission = RolePermission(role_id=role.id, permission_code=permission.code)
            db.add(role_permission)

    db.commit()
    db.refresh(role)
    return role

@router.delete("/rbac/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a custom role")
def delete_role(
    role_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin")),
):
    """Delete a custom role. System roles cannot be deleted.
    Requires system.admin permission.
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=403, detail="System roles cannot be deleted")

    db.delete(role)
    db.commit()
    return

@router.get("/rbac/users/{user_id}/roles", response_model=list[UserRoleSchema], summary="Get a user's role assignments")
def get_user_role_assignments(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user.manage")),
):
    """Retrieve all role assignments for a specific user.
    Requires user.manage permission.
    """
    user_roles = db.query(UserRole).filter(UserRole.user_id == user_id).all()
    return user_roles

@router.post("/rbac/users/{user_id}/roles", response_model=UserRoleSchema, status_code=status.HTTP_201_CREATED, summary="Assign a role to a user")
def assign_role_to_user_api(
    user_id: uuid.UUID,
    assignment: UserRoleAssignmentSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user.manage")),
):
    """Assign a role to a user, optionally scoped to a company.
    Requires user.manage permission.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    role = db.query(Role).filter(Role.id == assignment.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Check for existing assignment
    existing_assignment = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_id == assignment.role_id,
        UserRole.company_id == assignment.company_id
    ).first()
    if existing_assignment:
        raise HTTPException(status_code=400, detail="User already has this role assignment")

    user_role = rbac_service.assign_role_to_user(
        db,
        user_id=user_id,
        role_id=assignment.role_id,
        company_id=assignment.company_id,
        assigned_by=current_user,
    )
    db.refresh(user_role)
    return user_role

@router.delete("/rbac/users/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove a role from a user")
def remove_role_from_user_api(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    company_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user.manage")),
):
    """Remove a role assignment from a user, optionally scoped to a company.
    Requires user.manage permission.
    """
    success = rbac_service.remove_role_from_user(db, user_id, role_id, company_id)
    if not success:
        raise HTTPException(status_code=404, detail="Role assignment not found")
    return

@router.get("/rbac/me/permissions", response_model=UserPermissionsSchema, summary="Get current user's effective permissions")
def get_my_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve the current authenticated user's effective permissions,
    including global and company-specific permissions.
    """
    global_permissions = rbac_service.get_user_permissions(db, current_user, company_id=None)

    # For company-specific permissions, we need to find all companies the user has roles for
    user_companies = db.query(UserRole.company_id).filter(
        UserRole.user_id == current_user.id,
        UserRole.company_id != None
    ).distinct().all()

    company_permissions = {}
    for company_id_tuple in user_companies:
        company_id = company_id_tuple[0]
        if company_id:
            company_permissions[str(company_id)] = list(rbac_service.get_user_permissions(db, current_user, company_id))

    return UserPermissionsSchema(
        global_permissions=list(global_permissions),
        company_permissions=company_permissions
    )
