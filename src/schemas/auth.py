"""Authentication schemas."""
import re

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.schemas.user import UserResponse

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")


class LoginRequest(BaseModel):
    """Schema for login request."""

    username: str
    password: str


class RegisterRequest(BaseModel):
    """Schema for registration request."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not USERNAME_PATTERN.match(v):
            raise ValueError("Username must contain only alphanumeric characters and underscores")
        return v


class AuthResponse(BaseModel):
    """Schema for authentication response."""

    user: UserResponse


class AuthStatusResponse(BaseModel):
    """Schema for auth status response."""

    first_run: bool
    registration_enabled: bool = False
