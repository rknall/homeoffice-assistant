# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""User schemas."""
import datetime
import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.models.enums import UserRole

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")


class UserBase(BaseModel):
    """Base user schema."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not USERNAME_PATTERN.match(v):
            raise ValueError("Username must contain only alphanumeric characters and underscores")
        return v


class UserCreate(UserBase):
    """Schema for creating a user."""

    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Schema for updating a user (admin use)."""

    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not USERNAME_PATTERN.match(v):
            raise ValueError("Username must contain only alphanumeric characters and underscores")
        return v


class UserProfileUpdate(BaseModel):
    """Schema for updating user's own profile."""

    full_name: Optional[str] = Field(None, max_length=200)
    use_gravatar: Optional[bool] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = Field(None, min_length=8)


class UserResponse(BaseModel):
    """Schema for user response."""

    id: str
    username: str
    email: str
    role: UserRole
    is_admin: bool
    is_active: bool
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    use_gravatar: bool = True
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}
