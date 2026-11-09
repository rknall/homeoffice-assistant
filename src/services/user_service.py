# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""User profile logic and the user response shared by the auth and user APIs."""

from sqlalchemy.orm import Session

from src.models import User
from src.schemas.user import UserProfileUpdate, UserResponse
from src.security import get_password_hash, verify_password
from src.services import file_storage_service, rbac_service


def build_user_response(db: Session, user: User) -> UserResponse:
    """Build the API representation of a user with its permissions.

    Args:
        db: Database session.
        user: The user to describe.

    Returns:
        The response with global permissions and permissions per company.
    """
    perms = rbac_service.get_user_all_permissions(db, user)
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        full_name=user.full_name,
        avatar_url=file_storage_service.avatar_url(user.avatar_url),
        use_gravatar=user.use_gravatar,
        created_at=user.created_at,
        updated_at=user.updated_at,
        permissions=perms["global_permissions"],
        company_permissions=perms["company_permissions"],
    )


def update_profile(db: Session, user: User, data: UserProfileUpdate) -> User:
    """Apply a user's change to their own profile.

    Args:
        db: Database session.
        user: The user changing their profile.
        data: The requested changes; a new password needs the current one.

    Returns:
        The updated user.

    Raises:
        ValueError: When a new password is given without the correct current
            password.
    """
    if data.new_password:
        if not data.current_password:
            raise ValueError("Current password is required to change password")
        if not verify_password(data.current_password, user.hashed_password):
            raise ValueError("Current password is incorrect")
        user.hashed_password = get_password_hash(data.new_password)
    if data.full_name is not None:
        user.full_name = data.full_name or None
    if data.use_gravatar is not None:
        user.use_gravatar = data.use_gravatar
    db.commit()
    db.refresh(user)
    return user


def set_avatar(db: Session, user: User, filename: str | None, content: bytes) -> User:
    """Store an uploaded avatar for a user and switch off Gravatar.

    Args:
        db: Database session.
        user: The user getting the avatar.
        filename: The client's file name.
        content: The uploaded bytes.

    Returns:
        The updated user.

    Raises:
        file_storage_service.FileValidationError: When the upload is rejected.
    """
    user.avatar_url = file_storage_service.save_avatar(
        user.id, filename, content, user.avatar_url
    )
    user.use_gravatar = False
    db.commit()
    db.refresh(user)
    return user


def clear_avatar(db: Session, user: User) -> User:
    """Delete a user's avatar file and fall back to Gravatar.

    Args:
        db: Database session.
        user: The user whose avatar is removed.

    Returns:
        The updated user.
    """
    file_storage_service.remove_avatar(user.avatar_url)
    user.avatar_url = None
    user.use_gravatar = True
    db.commit()
    db.refresh(user)
    return user
