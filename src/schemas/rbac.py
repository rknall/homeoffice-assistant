# src/schemas/rbac.py
import uuid

from pydantic import BaseModel, ConfigDict


class PermissionSchema(BaseModel):
    """Schema representing a permission."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    module: str
    description: str | None
    plugin_id: str | None = None  # Non-null means plugin-provided permission


class RoleSchema(BaseModel):
    """Schema representing a role."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    is_system: bool
    description: str | None


class RoleWithPermissionsSchema(RoleSchema):
    """Schema representing a role along with its permissions."""

    permissions: list[PermissionSchema]


class RoleCreateSchema(BaseModel):
    """Schema for creating a new role."""

    name: str
    description: str | None = None
    permissions: list[str] = []  # List of permission codes


class RoleUpdateSchema(BaseModel):
    """Schema for updating a role."""

    name: str | None = None
    description: str | None = None
    permissions: list[str] | None = None


class UserRoleSchema(BaseModel):
    """Schema representing a user's role assignment."""

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    role_id: uuid.UUID
    company_id: uuid.UUID | None
    role: RoleSchema


class UserRoleAssignmentSchema(BaseModel):
    """Schema for assigning a role to a user."""

    role_id: uuid.UUID
    company_id: uuid.UUID | None = None


class UserPermissionsSchema(BaseModel):
    """Schema representing a user's permissions."""

    global_permissions: list[str]
    company_permissions: dict[str, list[str]]
