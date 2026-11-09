# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for rbac_service and the permission dependencies built on it."""

import uuid
from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.requests import Request

from src.api.deps import require_event_permission, require_permission
from src.models import Company, Event, RolePermission, User
from src.models.enums import CompanyType
from src.plugins.base import ProvidedPermission
from src.rbac.roles import (
    GLOBAL_ADMIN_PERMISSIONS,
    GLOBAL_ADMIN_ROLE,
    MEMBER_PERMISSIONS,
    MEMBER_ROLE,
)
from src.services import rbac_service
from src.services.rbac_seed_service import seed_rbac_data
from tests.conftest import UserFactory

VIEWER_CODES = {"company.view", "expense.view", "event.read"}
ADMIN_CODES = VIEWER_CODES | {
    "company.manage",
    "expense.manage",
    "event.write",
    "event.delete",
}


def make_company(db: Session, name: str) -> Company:
    """Create and return a company."""
    company = Company(name=name, type=CompanyType.EMPLOYER)
    db.add(company)
    db.commit()
    return company


def make_request(path_params: dict[str, str] | None = None, query: str = "") -> Request:
    """Build a bare request carrying path and query parameters."""
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "path_params": path_params or {},
            "query_string": query.encode(),
        }
    )


def role_codes(db: Session, name: str) -> set[str]:
    """Return the permission codes linked to the role called ``name``."""
    role = rbac_service.get_role_by_name(db, name)
    assert role is not None
    return set(
        db.scalars(
            select(RolePermission.permission_code).where(
                RolePermission.role_id == role.id
            )
        )
    )


@pytest.fixture
def alpha(db_session: Session) -> Company:
    return make_company(db_session, "Alpha")


@pytest.fixture
def beta(db_session: Session) -> Company:
    return make_company(db_session, "Beta")


@pytest.fixture
def viewer(user_factory: UserFactory, alpha: Company) -> User:
    return user_factory("viewer", roles=["Company Viewer"], company=alpha)


@pytest.fixture
def member(user_factory: UserFactory) -> User:
    return user_factory("member", roles=[MEMBER_ROLE])


@pytest.fixture
def admin(user_factory: UserFactory) -> User:
    return user_factory("globaladmin", roles=[GLOBAL_ADMIN_ROLE])


def test_global_role_permissions(db_session: Session, member: User) -> None:
    assert rbac_service.get_user_permissions(db_session, member) == set(
        MEMBER_PERMISSIONS
    )
    assert rbac_service.user_has_permission(db_session, member, "event.read")
    assert not rbac_service.user_has_permission(db_session, member, "system.admin")


def test_company_role_permissions(
    db_session: Session, viewer: User, alpha: Company, beta: Company
) -> None:
    assert rbac_service.get_user_permissions(db_session, viewer) == set()
    assert (
        rbac_service.get_user_permissions(db_session, viewer, alpha.id) == VIEWER_CODES
    )
    assert rbac_service.get_user_permissions(db_session, viewer, beta.id) == set()
    assert rbac_service.user_has_permission(
        db_session, viewer, "company.view", company_id=alpha.id
    )
    assert not rbac_service.user_has_permission(
        db_session, viewer, "company.view", company_id=beta.id
    )
    assert not rbac_service.user_has_permission(db_session, viewer, "company.view")
    assert not rbac_service.user_has_permission(
        db_session, viewer, "company.manage", company_id=alpha.id
    )


def test_global_and_company_roles_combine(
    db_session: Session, user_factory: UserFactory, alpha: Company, beta: Company
) -> None:
    user = user_factory("both", roles=["Company Admin"], company=alpha)
    viewer_role = rbac_service.get_role_by_name(db_session, "Company Viewer")
    assert viewer_role is not None
    rbac_service.assign_role_to_user(db_session, user.id, viewer_role.id)

    assert rbac_service.get_user_permissions(db_session, user) == VIEWER_CODES
    assert rbac_service.get_user_permissions(db_session, user, beta.id) == VIEWER_CODES
    assert rbac_service.get_user_permissions(db_session, user, alpha.id) == (
        VIEWER_CODES | ADMIN_CODES
    )
    all_perms = rbac_service.get_user_all_permissions(db_session, user)
    assert set(all_perms["global_permissions"]) == VIEWER_CODES
    assert all_perms["company_permissions"].keys() == {str(alpha.id)}
    assert set(all_perms["company_permissions"][str(alpha.id)]) == ADMIN_CODES


def test_is_global_admin_only_for_global_system_role(
    db_session: Session, admin: User, user_factory: UserFactory, alpha: Company
) -> None:
    scoped = user_factory("scopedadmin", roles=[GLOBAL_ADMIN_ROLE], company=alpha)

    assert rbac_service.is_global_admin(db_session, admin)
    assert not rbac_service.is_global_admin(db_session, scoped)
    assert rbac_service.user_has_permission(db_session, admin, "anything.at.all")


def test_inactive_user_has_no_permission(db_session: Session, admin: User) -> None:
    admin.is_active = False
    db_session.commit()

    assert not rbac_service.user_has_permission(db_session, admin, "event.read")
    assert rbac_service.companies_with_permission(db_session, admin, "x") == set()


def test_companies_with_permission(
    db_session: Session,
    viewer: User,
    member: User,
    admin: User,
    alpha: Company,
    user_factory: UserFactory,
) -> None:
    nobody = user_factory("nobody", roles=())

    assert rbac_service.companies_with_permission(
        db_session, viewer, "company.view"
    ) == {alpha.id}
    assert (
        rbac_service.companies_with_permission(db_session, viewer, "company.manage")
        == set()
    )
    assert (
        rbac_service.companies_with_permission(db_session, member, "company.view")
        is None
    )
    assert (
        rbac_service.companies_with_permission(db_session, admin, "company.view")
        is None
    )
    assert (
        rbac_service.companies_with_permission(db_session, nobody, "company.view")
        == set()
    )


def test_plugin_permission_member_default_granted_at_first_registration(
    db_session: Session,
) -> None:
    seed_rbac_data(db_session)
    provided = [
        ProvidedPermission("demo.items.read", "Read", member_default=True),
        ProvidedPermission("demo.items.purge", "Purge"),
    ]

    rbac_service.register_plugin_permissions(db_session, "demo", provided)

    admin_codes = role_codes(db_session, GLOBAL_ADMIN_ROLE)
    assert {"demo.items.read", "demo.items.purge"} <= admin_codes
    assert set(GLOBAL_ADMIN_PERMISSIONS) <= admin_codes
    member_codes = role_codes(db_session, MEMBER_ROLE)
    assert "demo.items.read" in member_codes
    assert "demo.items.purge" not in member_codes

    member_role = rbac_service.get_role_by_name(db_session, MEMBER_ROLE)
    assert member_role is not None
    db_session.query(RolePermission).filter(
        RolePermission.role_id == member_role.id,
        RolePermission.permission_code == "demo.items.read",
    ).delete()
    db_session.commit()

    rbac_service.register_plugin_permissions(db_session, "demo", provided)

    assert "demo.items.read" not in role_codes(db_session, MEMBER_ROLE)


def test_require_permission_reads_path_then_query(
    db_session: Session, viewer: User, alpha: Company, beta: Company
) -> None:
    check = require_permission("company.view", company_id_param="company_id")

    from_path = make_request({"company_id": str(alpha.id)}, f"company_id={beta.id}")
    assert check(request=from_path, db=db_session, current_user=viewer) is viewer
    from_query = make_request(query=f"company_id={alpha.id}")
    assert check(request=from_query, db=db_session, current_user=viewer) is viewer
    with pytest.raises(HTTPException) as denied:
        check(
            request=make_request(query=f"company_id={beta.id}"),
            db=db_session,
            current_user=viewer,
        )
    assert denied.value.status_code == 403


def test_require_permission_without_company_id(
    db_session: Session, viewer: User, member: User
) -> None:
    scoped = require_permission("company.view", company_id_param="company_id")
    unscoped = require_permission("company.view")
    request = make_request()

    # Held in one company is enough when the request names no company.
    assert scoped(request=request, db=db_session, current_user=viewer) is viewer
    assert unscoped(request=request, db=db_session, current_user=member) is member
    with pytest.raises(HTTPException) as denied:
        unscoped(request=request, db=db_session, current_user=viewer)
    assert denied.value.status_code == 403
    with pytest.raises(HTTPException):
        require_permission("company.manage", company_id_param="company_id")(
            request=request, db=db_session, current_user=viewer
        )


def test_require_event_permission(
    db_session: Session,
    viewer: User,
    member: User,
    alpha: Company,
) -> None:
    event = Event(
        user_id=viewer.id,
        company_id=alpha.id,
        name="Trip",
        start_date=date(2025, 6, 1),
        end_date=date(2025, 6, 3),
    )
    db_session.add(event)
    db_session.commit()

    read = require_event_permission("event.read")
    write = require_event_permission("event.write")

    assert read(event_id=event.id, db=db_session, current_user=viewer) == event
    with pytest.raises(HTTPException) as forbidden:
        write(event_id=event.id, db=db_session, current_user=viewer)
    assert forbidden.value.status_code == 403
    with pytest.raises(HTTPException) as not_owner:
        read(event_id=event.id, db=db_session, current_user=member)
    assert not_owner.value.status_code == 404
    with pytest.raises(HTTPException) as missing:
        read(event_id=uuid.uuid4(), db=db_session, current_user=viewer)
    assert missing.value.status_code == 404
