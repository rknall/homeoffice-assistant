# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""User management API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from src.api.deps import permission_denied, require_permission
from src.database import get_db
from src.models import User
from src.schemas.user import UserCreate, UserResponse, UserUpdate
from src.security import get_password_hash
from src.services import file_storage_service, rbac_service, user_service
from src.services.user_service import build_user_response

router = APIRouter()


def _get_user_for_change(db: Session, user_id: uuid.UUID, current_user: User) -> User:
    """Load a user that the current user is about to change.

    Args:
        db: Database session.
        user_id: The user to change.
        current_user: The user making the change.

    Returns:
        The user.

    Raises:
        HTTPException: 404 when the user does not exist, 403 when the user
            holds system.admin and the current user does not.
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not rbac_service.can_manage_user(db, current_user, user):
        raise permission_denied("system.admin")
    return user


@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="List all users",
)
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user.manage")),
) -> list[UserResponse]:
    """Retrieve a list of all users in the system.

    Requires user.manage permission.
    """
    users = db.query(User).order_by(User.username).all()

    return [build_user_response(db, user) for user in users]


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user.manage")),
) -> UserResponse:
    """Create a new user with the default Member role.

    Requires user.manage permission.
    """
    # Check for duplicate username
    existing = db.query(User).filter(User.username == user_in.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")

    # Check for duplicate email
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already in use")

    user = User(
        id=uuid.uuid4(),
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        is_active=True,
    )
    db.add(user)
    db.flush()
    rbac_service.assign_member_role(db, user.id)
    db.commit()
    db.refresh(user)

    return build_user_response(db, user)


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Get a user by ID",
)
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user.read")),
) -> UserResponse:
    """Retrieve a specific user by ID.

    Requires user.read permission.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return build_user_response(db, user)


@router.put(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Update a user",
)
def update_user(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user.manage")),
) -> UserResponse:
    """Update a user's information.

    Requires user.manage permission; changing a user who holds system.admin
    requires system.admin.
    """
    user = _get_user_for_change(db, user_id, current_user)

    if user_in.username is not None:
        # Check for duplicate username
        existing = (
            db.query(User)
            .filter(User.username == user_in.username, User.id != user_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")
        user.username = user_in.username

    if user_in.email is not None:
        # Check for duplicate email
        existing = (
            db.query(User)
            .filter(User.email == user_in.email, User.id != user_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = user_in.email

    if user_in.password is not None:
        user.hashed_password = get_password_hash(user_in.password)

    if user_in.is_active is not None:
        # Prevent deactivating yourself
        if user_id == current_user.id and not user_in.is_active:
            raise HTTPException(
                status_code=400, detail="Cannot deactivate your own account"
            )
        user.is_active = user_in.is_active

    if user_in.full_name is not None:
        user.full_name = user_in.full_name or None

    if user_in.use_gravatar is not None:
        user.use_gravatar = user_in.use_gravatar

    db.commit()
    db.refresh(user)

    return build_user_response(db, user)


@router.post(
    "/users/{user_id}/avatar",
    response_model=UserResponse,
    summary="Upload avatar for a user",
)
async def upload_user_avatar(
    user_id: uuid.UUID,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user.manage")),
) -> UserResponse:
    """Upload a new avatar for a specific user.

    Requires user.manage permission.
    """
    user = _get_user_for_change(db, user_id, current_user)
    content = await file.read()
    try:
        user = user_service.set_avatar(db, user, file.filename, content)
    except file_storage_service.FileValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    return build_user_response(db, user)


@router.delete(
    "/users/{user_id}/avatar",
    response_model=UserResponse,
    summary="Delete avatar for a user",
)
def delete_user_avatar(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user.manage")),
) -> UserResponse:
    """Delete a user's avatar and revert to Gravatar.

    Requires user.manage permission.
    """
    user = _get_user_for_change(db, user_id, current_user)
    return build_user_response(db, user_service.clear_avatar(db, user))
