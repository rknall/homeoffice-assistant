"""Authentication API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.models import User
from src.schemas.auth import (
    AuthResponse,
    AuthStatusResponse,
    LoginRequest,
    RegisterRequest,
)
from src.schemas.user import UserResponse
from src.services import auth_service

router = APIRouter()


@router.get("/status", response_model=AuthStatusResponse)
def get_auth_status(db: Session = Depends(get_db)) -> AuthStatusResponse:
    """Get authentication status (first run check)."""
    first_run = auth_service.is_first_run(db)
    registration_enabled = auth_service.is_registration_enabled(db) if not first_run else True
    return AuthStatusResponse(
        first_run=first_run,
        registration_enabled=registration_enabled,
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    data: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthResponse:
    """Register a new user. Only works during first run or if admin enables registration."""
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
    token = auth_service.create_session(db, user.id)

    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        secure=False,  # Set to True in production
        samesite="lax",
        max_age=86400 * 7,  # 7 days
    )

    return AuthResponse(user=UserResponse.model_validate(user))


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

    token = auth_service.create_session(db, user.id)

    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        secure=False,  # Set to True in production
        samesite="lax",
        max_age=86400 * 7,  # 7 days
    )

    return AuthResponse(user=UserResponse.model_validate(user))


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
    current_user: User = Depends(get_current_user),
) -> AuthResponse:
    """Get current authenticated user."""
    return AuthResponse(user=UserResponse.model_validate(current_user))
