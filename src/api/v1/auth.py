# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Authentication API endpoints."""

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.models import User
from src.schemas.auth import (
    AuthResponse,
    AuthStatusResponse,
    LoginRequest,
    RegisterRequest,
)
from src.schemas.user import UserProfileUpdate, UserResponse
from src.security import get_password_hash, verify_password
from src.services import auth_service, rbac_service


def build_user_response(db: Session, user: User) -> UserResponse:
    """Build UserResponse with permissions from RBAC."""
    perms = rbac_service.get_user_all_permissions(db, user)
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        use_gravatar=user.use_gravatar,
        created_at=user.created_at,
        updated_at=user.updated_at,
        permissions=perms["global_permissions"],
        company_permissions=perms["company_permissions"],
    )

AVATAR_DIR = "static/avatars"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

router = APIRouter()


@router.get("/status", response_model=AuthStatusResponse)
def get_auth_status(db: Session = Depends(get_db)) -> AuthStatusResponse:
    """Get authentication status (first run check)."""
    first_run = auth_service.is_first_run(db)
    registration_enabled = (
        auth_service.is_registration_enabled(db) if not first_run else True
    )
    return AuthStatusResponse(
        first_run=first_run,
        registration_enabled=registration_enabled,
    )


@router.get("/check-username/{username}")
def check_username_availability(
    username: str,
    db: Session = Depends(get_db),
) -> dict:
    """Check if a username is available."""
    existing = auth_service.get_user_by_username(db, username)
    return {"available": existing is None, "username": username}


@router.post(
    "/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED
)
def register(
    data: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthResponse:
    """Register a new user.

    Only works during first run or if admin enables registration.
    """
    first_run = auth_service.is_first_run(db)

    if not first_run and not auth_service.is_registration_enabled(db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is disabled",
        )

    existing_username = auth_service.get_user_by_username(db, data.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    existing_email = auth_service.get_user_by_email(db, data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists",
        )

    user = auth_service.register_user(db, data)
    user_id = user.id
    token = auth_service.create_session(db, user_id)

    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        secure=False,  # Set to True in production
        samesite="lax",
        max_age=86400 * 7,  # 7 days
    )

    # Re-query user after session creation commit to avoid expired object error
    user = auth_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User not found after registration",
        )

    return AuthResponse(user=build_user_response(db, user))


@router.post("/login", response_model=AuthResponse)
def login(
    data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthResponse:
    """Login with username and password."""
    user = auth_service.authenticate(db, data.username, data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    user_id = user.id
    token = auth_service.create_session(db, user_id)

    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        secure=False,  # Set to True in production
        samesite="lax",
        max_age=86400 * 7,  # 7 days
    )

    # Re-query user after session creation commit to avoid expired object error
    user = auth_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User not found after session creation",
        )

    return AuthResponse(user=build_user_response(db, user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Logout current user."""
    # Delete all sessions for this user would be more secure
    # but for now we just clear the cookie
    response.delete_cookie(key="session")


@router.get("/me", response_model=AuthResponse)
def get_current_user_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuthResponse:
    """Get current authenticated user."""
    return AuthResponse(user=build_user_response(db, current_user))


@router.put("/me", response_model=AuthResponse)
def update_current_user_profile(
    data: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuthResponse:
    """Update current user's profile."""
    # If changing password, verify current password first
    if data.new_password:
        if not data.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required to change password",
            )
        if not verify_password(data.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )
        current_user.hashed_password = get_password_hash(data.new_password)

    # Update other fields
    if data.full_name is not None:
        current_user.full_name = data.full_name or None
    if data.use_gravatar is not None:
        current_user.use_gravatar = data.use_gravatar

    db.commit()
    db.refresh(current_user)

    return AuthResponse(user=build_user_response(db, current_user))


@router.post("/me/avatar", response_model=AuthResponse)
async def upload_avatar(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuthResponse:
    """Upload a new avatar for the current user."""
    # Validate file extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided",
        )

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            ),
        )

    # Read file content
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    # Ensure avatar directory exists
    os.makedirs(AVATAR_DIR, exist_ok=True)

    # Delete old avatar if exists
    if current_user.avatar_url:
        old_path = current_user.avatar_url.lstrip("/")
        if os.path.exists(old_path):
            os.remove(old_path)

    # Save new avatar with unique filename
    filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(AVATAR_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(content)

    # Update user
    current_user.avatar_url = f"/{filepath}"
    current_user.use_gravatar = False
    db.commit()
    db.refresh(current_user)

    return AuthResponse(user=build_user_response(db, current_user))


@router.delete("/me/avatar", response_model=AuthResponse)
def delete_avatar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuthResponse:
    """Delete the current user's avatar and revert to Gravatar."""
    if current_user.avatar_url:
        old_path = current_user.avatar_url.lstrip("/")
        if os.path.exists(old_path):
            os.remove(old_path)

    current_user.avatar_url = None
    current_user.use_gravatar = True
    db.commit()
    db.refresh(current_user)

    return AuthResponse(user=build_user_response(db, current_user))
