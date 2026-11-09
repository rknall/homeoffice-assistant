# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""API dependencies for dependency injection."""

import uuid
from collections.abc import Callable

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import Event, User
from src.services import auth_service, event_service, rbac_service


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


def permission_denied(code: str) -> HTTPException:
    """Build the 403 error for a missing permission code.

    Args:
        code: The permission code the user lacks.

    Returns:
        The exception to raise, with the detail ``Permission denied: <code>``.
    """
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Permission denied: {code}",
    )


def ensure_permission(
    db: Session, user: User, code: str, company_id: uuid.UUID | None = None
) -> None:
    """Raise 403 unless the user holds the code.

    Routes call this directly when the company comes from the request body
    or a loaded record, which the path/query based dependencies cannot see.

    Args:
        db: Database session.
        user: The user to check.
        code: Permission code, e.g. "event.write".
        company_id: Company to scope the check to. None counts global roles
            only.

    Raises:
        HTTPException: 403 when the user lacks the code.
    """
    if not rbac_service.user_has_permission(db, user, code, company_id=company_id):
        raise permission_denied(code)


def _company_id_from_request(request: Request, param: str) -> uuid.UUID | None:
    """Read a company id from the path params, then the query params.

    Args:
        request: The incoming request.
        param: Name of the path or query parameter.

    Returns:
        The parsed id, or None when the parameter is absent or not a UUID.
    """
    raw = request.path_params.get(param)
    if raw is None:
        raw = request.query_params.get(param)
    if raw is None:
        return None
    try:
        return uuid.UUID(str(raw))
    except ValueError:
        return None


def require_permission(
    permission_code: str, company_id_param: str | None = None
) -> Callable[..., User]:
    """Build a dependency that checks a permission code.

    Args:
        permission_code: Code the user must hold, e.g. "company.view".
        company_id_param: Name of the path or query parameter holding the
            company id. When the request carries it, the check is scoped to
            that company. When it is missing, the user passes if the code is
            held globally or in any company; the route then filters its
            results with ``rbac_service.companies_with_permission``. Without
            this argument only global roles count.

    Returns:
        A FastAPI dependency returning the current user.
    """

    def dependency(
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> User:
        if company_id_param is None:
            ensure_permission(db, current_user, permission_code)
        elif (
            company_id := _company_id_from_request(request, company_id_param)
        ) is not None:
            ensure_permission(db, current_user, permission_code, company_id)
        else:
            companies = rbac_service.companies_with_permission(
                db, current_user, permission_code
            )
            if companies is not None and not companies:
                raise permission_denied(permission_code)
        return current_user

    return dependency


def require_event_permission(permission_code: str) -> Callable[..., Event]:
    """Build a dependency that loads the caller's event and checks a code.

    The route must have an ``event_id`` path parameter.

    Args:
        permission_code: Code the user must hold for the event's company,
            e.g. "expense.manage".

    Returns:
        A FastAPI dependency returning the event. It raises 404 when the event
        does not exist or belongs to another user, and 403 when the user lacks
        the code for the event's company.
    """

    def dependency(
        event_id: uuid.UUID,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> Event:
        event = event_service.get_event_for_user(db, event_id, current_user.id)
        if event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found",
            )
        ensure_permission(db, current_user, permission_code, event.company_id)
        return event

    return dependency
