# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""API dependencies for dependency injection."""
from collections.abc import Generator

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.models import User
from src.services import auth_service


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    db: Session = Depends(get_db),
    session: str | None = Cookie(default=None),
) -> User:
    """Get current authenticated user from session cookie."""
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    session_obj = auth_service.get_session(db, session)
    if not session_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    user = auth_service.get_user_by_id(db, session_obj.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current user and verify they are an admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def get_optional_user(
    db: Session = Depends(get_db),
    session: str | None = Cookie(default=None),
) -> User | None:
    """Get current user if authenticated, otherwise return None."""
    if not session:
        return None

    session_obj = auth_service.get_session(db, session)
    if not session_obj:
        return None

    user = auth_service.get_user_by_id(db, session_obj.user_id)
    if not user or not user.is_active:
        return None

    return user
