# src/api/v1/users.py
"""User management API endpoints."""

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from src.api.deps import get_db, require_permission
from src.models import User
from src.schemas.user import UserCreate, UserResponse, UserUpdate
from src.security import get_password_hash
from src.services import rbac_service

AVATAR_DIR = "static/avatars"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

router = APIRouter()


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

    # Build response with permissions for each user
    result = []
    for user in users:
        global_permissions = rbac_service.get_user_permissions(
            db, user, company_id=None
        )
        all_permissions = rbac_service.get_user_all_permissions(db, user)

        result.append(
            UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                is_active=user.is_active,
                full_name=user.full_name,
                avatar_url=user.avatar_url,
                use_gravatar=user.use_gravatar,
                created_at=user.created_at,
                updated_at=user.updated_at,
                permissions=list(global_permissions),
                company_permissions=all_permissions.get("company_permissions", {}),
            )
        )

    return result


@router.post(
    "/users",
    response_model=UserResponse,
    summary="Create a new user",
)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user.manage")),
) -> UserResponse:
    """Create a new user.

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
    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        use_gravatar=user.use_gravatar,
        created_at=user.created_at,
        updated_at=user.updated_at,
        permissions=[],
        company_permissions={},
    )


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

    global_permissions = rbac_service.get_user_permissions(db, user, company_id=None)
    all_permissions = rbac_service.get_user_all_permissions(db, user)

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        use_gravatar=user.use_gravatar,
        created_at=user.created_at,
        updated_at=user.updated_at,
        permissions=list(global_permissions),
        company_permissions=all_permissions.get("company_permissions", {}),
    )


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

    Requires user.manage permission.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_in.username is not None:
        # Check for duplicate username
        existing = (
            db.query(User)
            .filter(User.username == user_in.username, User.id != user_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=400, detail="Username already taken"
            )
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

    global_permissions = rbac_service.get_user_permissions(db, user, company_id=None)
    all_permissions = rbac_service.get_user_all_permissions(db, user)

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        use_gravatar=user.use_gravatar,
        created_at=user.created_at,
        updated_at=user.updated_at,
        permissions=list(global_permissions),
        company_permissions=all_permissions.get("company_permissions", {}),
    )


def _build_user_response(db: Session, user: User) -> UserResponse:
    """Build a UserResponse with permissions."""
    global_permissions = rbac_service.get_user_permissions(db, user, company_id=None)
    all_permissions = rbac_service.get_user_all_permissions(db, user)
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        use_gravatar=user.use_gravatar,
        created_at=user.created_at,
        updated_at=user.updated_at,
        permissions=list(global_permissions),
        company_permissions=all_permissions.get("company_permissions", {}),
    )


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
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

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
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
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
    if user.avatar_url:
        old_path = user.avatar_url.lstrip("/")
        if os.path.exists(old_path):
            os.remove(old_path)

    # Save new avatar with unique filename
    filename = f"{user.id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(AVATAR_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(content)

    # Update user
    user.avatar_url = f"/{filepath}"
    user.use_gravatar = False
    db.commit()
    db.refresh(user)

    return _build_user_response(db, user)


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
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.avatar_url:
        old_path = user.avatar_url.lstrip("/")
        if os.path.exists(old_path):
            os.remove(old_path)

    user.avatar_url = None
    user.use_gravatar = True
    db.commit()
    db.refresh(user)

    return _build_user_response(db, user)
