# src/schemas/rbac.py
import uuid

from pydantic import BaseModel


class PermissionSchema(BaseModel):
    """Schema representing a permission."""

    code: str
    module: str
    description: str | None

    class Config:
        orm_mode = True


class RoleSchema(BaseModel):
    """Schema representing a role."""

    id: uuid.UUID
    name: str
    is_system: bool
    description: str | None

    class Config:
        orm_mode = True


class RoleWithPermissionsSchema(RoleSchema):
    """Schema representing a role along with its permissions."""

    permissions: list[PermissionSchema]


class RoleCreateSchema(BaseModel):
    """Schema for creating a new role."""

    name: str
    description: str | None
    permissions: list[str]  # List of permission codes


class RoleUpdateSchema(BaseModel):
    """Schema for updating a role."""

    name: str | None
    description: str | None
    permissions: list[str] | None


class UserRoleSchema(BaseModel):
    """Schema representing a user's role assignment."""

    user_id: uuid.UUID
    role_id: uuid.UUID
    company_id: uuid.UUID | None
    role: RoleSchema

    class Config:
        orm_mode = True


class UserRoleAssignmentSchema(BaseModel):
    """Schema for assigning a role to a user."""

    role_id: uuid.UUID
    company_id: uuid.UUID | None


class UserPermissionsSchema(BaseModel):
    """Schema representing a user's permissions."""

    global_permissions: list[str]
    company_permissions: dict[str, list[str]]
