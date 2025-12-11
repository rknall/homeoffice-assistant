# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""API dependencies for dependency injection."""

import uuid
from collections.abc import Generator

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.models import User
from src.services import auth_service, rbac_service


def get_db() -> Generator[Session]:
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
    db: Session = Depends(get_db),
) -> User:
    """Get current user and verify they have system.admin permission."""
    if not rbac_service.user_has_permission(db, current_user, "system.admin"):
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


def require_permission(
    permission_code: str, company_id_param: str | None = None
) -> User:
    """Dependency for permission-based authorization."""

    def dependency(
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> User:
        company_id = None
        if company_id_param and company_id_param in request.path_params:
            company_id_raw = request.path_params[company_id_param]
            try:
                company_id = uuid.UUID(str(company_id_raw))
            except (TypeError, ValueError):
                company_id = None

        if not rbac_service.user_has_permission(
            db, current_user, permission_code, company_id=company_id
        ):
            raise HTTPException(
                status_code=403, detail=f"Permission denied: {permission_code}"
            )
        return current_user

    return dependency
