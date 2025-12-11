# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""User schemas."""

import datetime
import re
import uuid

from pydantic import BaseModel, EmailStr, Field, field_validator

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")


class UserBase(BaseModel):
    """Base user schema."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format (alphanumeric and underscores only)."""
        if not USERNAME_PATTERN.match(v):
            raise ValueError(
                "Username must contain only alphanumeric characters and underscores"
            )
        return v


class UserCreate(UserBase):
    """Schema for creating a user."""

    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Schema for updating a user (admin use)."""

    username: str | None = Field(None, min_length=3, max_length=50)
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=8)
    is_active: bool | None = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str | None) -> str | None:
        """Validate username format (alphanumeric and underscores only)."""
        if v is not None and not USERNAME_PATTERN.match(v):
            raise ValueError(
                "Username must contain only alphanumeric characters and underscores"
            )
        return v


class UserProfileUpdate(BaseModel):
    """Schema for updating user's own profile."""

    full_name: str | None = Field(None, max_length=200)
    use_gravatar: bool | None = None
    current_password: str | None = None
    new_password: str | None = Field(None, min_length=8)


class UserResponse(BaseModel):
    """Schema for user response."""

    id: uuid.UUID
    username: str
    email: str
    is_active: bool
    full_name: str | None = None
    avatar_url: str | None = None
    use_gravatar: bool = True
    created_at: datetime.datetime
    updated_at: datetime.datetime
    permissions: list[str] = []
    company_permissions: dict[str, list[str]] = {}

    model_config = {"from_attributes": True}
