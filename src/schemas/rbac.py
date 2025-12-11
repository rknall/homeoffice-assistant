# src/schemas/rbac.py
import uuid

from pydantic import BaseModel


class PermissionSchema(BaseModel):
    code: str
    module: str
    description: str | None

    class Config:
        orm_mode = True

class RoleSchema(BaseModel):
    id: uuid.UUID
    name: str
    is_system: bool
    description: str | None

    class Config:
        orm_mode = True

class RoleWithPermissionsSchema(RoleSchema):
    permissions: list[PermissionSchema]

class RoleCreateSchema(BaseModel):
    name: str
    description: str | None
    permissions: list[str] # List of permission codes

class RoleUpdateSchema(BaseModel):
    name: str | None
    description: str | None
    permissions: list[str] | None

class UserRoleSchema(BaseModel):
    user_id: uuid.UUID
    role_id: uuid.UUID
    company_id: uuid.UUID | None
    role: RoleSchema

    class Config:
        orm_mode = True

class UserRoleAssignmentSchema(BaseModel):
    role_id: uuid.UUID
    company_id: uuid.UUID | None

class UserPermissionsSchema(BaseModel):
    global_permissions: list[str]
    company_permissions: dict[str, list[str]]
