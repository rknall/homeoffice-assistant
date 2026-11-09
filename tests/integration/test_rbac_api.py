# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for user and role administration through the RBAC and users API."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models import Role, User
from src.rbac.roles import GLOBAL_ADMIN_ROLE, MEMBER_ROLE
from src.services import rbac_service, role_admin_service
from tests.conftest import LoginHelper, UserFactory

USER_MANAGER_ROLE = "User Manager"


@pytest.fixture
def user_manager(
    db_session: Session, admin_user: User, user_factory: UserFactory
) -> User:
    """Create a user whose only permission is user.manage."""
    role_admin_service.create_role(db_session, USER_MANAGER_ROLE, None, ["user.manage"])
    return user_factory("usermanager", roles=[USER_MANAGER_ROLE])


@pytest.fixture
def manager_client(
    client: TestClient, login: LoginHelper, user_manager: User
) -> TestClient:
    """Log the user.manage-only user in."""
    return login(client, user_manager)


def _role(db_session: Session, name: str) -> Role:
    role = rbac_service.get_role_by_name(db_session, name)
    assert role is not None
    return role


def test_user_manager_cannot_assign_global_admin(
    db_session: Session, manager_client: TestClient, user_manager: User
):
    admin_role = _role(db_session, GLOBAL_ADMIN_ROLE)

    response = manager_client.post(
        f"/api/v1/rbac/users/{user_manager.id}/roles",
        json={"role_id": str(admin_role.id)},
    )

    assert response.status_code == 403
    assert not rbac_service.is_global_admin(db_session, user_manager)


def test_user_manager_cannot_assign_role_holding_system_admin(
    db_session: Session,
    manager_client: TestClient,
    user_manager: User,
):
    custom = role_admin_service.create_role(
        db_session, "Shadow", None, ["system.admin"]
    )

    response = manager_client.post(
        f"/api/v1/rbac/users/{user_manager.id}/roles",
        json={"role_id": str(custom.id)},
    )

    assert response.status_code == 403


def test_user_manager_cannot_reset_admin_password(
    manager_client: TestClient, admin_user: User
):
    response = manager_client.put(
        f"/api/v1/users/{admin_user.id}", json={"password": "taken-over-123"}
    )

    assert response.status_code == 403
    login = manager_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "adminpassword123"},
    )
    assert login.status_code == 200


def test_user_manager_cannot_remove_admin_role(
    db_session: Session, manager_client: TestClient, admin_user: User
):
    admin_role = _role(db_session, GLOBAL_ADMIN_ROLE)

    response = manager_client.delete(
        f"/api/v1/rbac/users/{admin_user.id}/roles/{admin_role.id}"
    )

    assert response.status_code == 403
    assert rbac_service.is_global_admin(db_session, admin_user)


def test_user_manager_can_manage_regular_user(
    db_session: Session,
    manager_client: TestClient,
    user_factory: UserFactory,
):
    regular = user_factory("regular", roles=())
    member_role = _role(db_session, MEMBER_ROLE)

    update = manager_client.put(
        f"/api/v1/users/{regular.id}", json={"full_name": "Regular User"}
    )
    assign = manager_client.post(
        f"/api/v1/rbac/users/{regular.id}/roles",
        json={"role_id": str(member_role.id)},
    )

    assert update.status_code == 200
    assert assign.status_code == 201


def test_create_user_without_roles_gets_member_globally(
    db_session: Session, admin_client: TestClient
):
    response = admin_client.post(
        "/api/v1/users",
        json={
            "username": "newmember",
            "email": "newmember@example.com",
            "password": "member-login-123",
        },
    )

    assert response.status_code == 201, response.text
    assert "event.read" in response.json()["permissions"]
    user = db_session.query(User).filter(User.username == "newmember").one()
    assert [(ur.role.name, ur.company_id) for ur in user.user_roles] == [
        (MEMBER_ROLE, None)
    ]


def test_create_role_rejects_system_role_name(admin_client: TestClient):
    response = admin_client.post(
        "/api/v1/rbac/roles", json={"name": GLOBAL_ADMIN_ROLE, "permissions": []}
    )

    assert response.status_code == 400
    assert "reserved" in response.json()["detail"]


def test_create_role_with_unknown_permission_leaves_no_role(
    db_session: Session, admin_client: TestClient
):
    response = admin_client.post(
        "/api/v1/rbac/roles", json={"name": "Broken", "permissions": ["no.such"]}
    )

    assert response.status_code == 400
    assert rbac_service.get_role_by_name(db_session, "Broken") is None


def test_update_role_replaces_permissions(
    db_session: Session, admin_client: TestClient
):
    created = admin_client.post(
        "/api/v1/rbac/roles",
        json={"name": "Reader", "permissions": ["event.read"]},
    )
    assert created.status_code == 201
    role_id = created.json()["id"]

    updated = admin_client.put(
        f"/api/v1/rbac/roles/{role_id}",
        json={"name": "Expense Reader", "permissions": ["expense.view"]},
    )

    assert updated.status_code == 200
    detail = admin_client.get(f"/api/v1/rbac/roles/{role_id}").json()
    assert detail["name"] == "Expense Reader"
    assert [p["code"] for p in detail["permissions"]] == ["expense.view"]


def test_system_role_cannot_be_updated(db_session: Session, admin_client: TestClient):
    admin_role = _role(db_session, GLOBAL_ADMIN_ROLE)

    response = admin_client.put(
        f"/api/v1/rbac/roles/{admin_role.id}", json={"description": "changed"}
    )

    assert response.status_code == 403
