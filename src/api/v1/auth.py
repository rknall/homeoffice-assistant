# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Authentication API endpoints."""

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from src.api.deps import get_current_user
from src.database import get_db
from src.models import User
from src.schemas.auth import (
    AuthResponse,
    AuthStatusResponse,
    LoginRequest,
    RegisterRequest,
    UsernameAvailabilityResponse,
)
from src.schemas.user import UserProfileUpdate
from src.services import auth_service, file_storage_service, user_service
from src.services.user_service import build_user_response

SESSION_MAX_AGE = 86400 * auth_service.SESSION_EXPIRY_DAYS

router = APIRouter()


def _set_session_cookie(response: Response, request: Request, token: str) -> None:
    """Set the session cookie, marked secure when the request came over HTTPS.

    Args:
        response: The response that carries the cookie.
        request: The incoming request; its scheme decides the secure flag.
        token: The session token.
    """
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        max_age=SESSION_MAX_AGE,
    )


@router.get("/status", response_model=AuthStatusResponse)
def get_auth_status(db: Session = Depends(get_db)) -> AuthStatusResponse:
    """Get authentication status (first run check)."""
    return AuthStatusResponse(
        first_run=auth_service.is_first_run(db),
        registration_enabled=auth_service.is_registration_open(db),
    )


@router.get("/check-username/{username}", response_model=UsernameAvailabilityResponse)
def check_username_availability(
    username: str,
    db: Session = Depends(get_db),
) -> UsernameAvailabilityResponse:
    """Check if a username is available.

    Only answered while registration is possible (first run or registration
    enabled); otherwise it would let anyone enumerate the existing accounts.
    """
    if not auth_service.is_registration_open(db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is disabled",
        )
    existing = auth_service.get_user_by_username(db, username)
    return UsernameAvailabilityResponse(available=existing is None, username=username)


@router.post(
    "/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED
)
def register(
    data: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthResponse:
    """Register a new user.

    Only works during first run or if admin enables registration.
    """
    if not auth_service.is_registration_open(db):
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

    _set_session_cookie(response, request, token)

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
    request: Request,
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

    _set_session_cookie(response, request, token)

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
    session: str | None = Cookie(default=None),
) -> None:
    """Logout current user."""
    if session:
        auth_service.delete_session(db, session)
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
    try:
        user = user_service.update_profile(db, current_user, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    return AuthResponse(user=build_user_response(db, user))


@router.post("/me/avatar", response_model=AuthResponse)
async def upload_avatar(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuthResponse:
    """Upload a new avatar for the current user."""
    content = await file.read()
    try:
        user = user_service.set_avatar(db, current_user, file.filename, content)
    except file_storage_service.FileValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    return AuthResponse(user=build_user_response(db, user))


@router.delete("/me/avatar", response_model=AuthResponse)
def delete_avatar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuthResponse:
    """Delete the current user's avatar and revert to Gravatar."""
    user = user_service.clear_avatar(db, current_user)
    return AuthResponse(user=build_user_response(db, user))
