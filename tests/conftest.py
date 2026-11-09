# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Core user fixtures.

The database and the ``db_session``/``client`` fixtures live in the repository
root ``conftest.py``.
"""

from collections.abc import Callable, Generator, Sequence

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models import Company, User
from src.models.enums import CompanyType
from src.rbac.roles import GLOBAL_ADMIN_ROLE, MEMBER_ROLE
from src.security import get_password_hash
from src.services import rbac_service
from src.services.rbac_seed_service import seed_rbac_data

# Login secret shared by every user built with ``user_factory``.
FACTORY_LOGIN = "factory-login-123"

UserFactory = Callable[..., User]
LoginHelper = Callable[[TestClient, User], TestClient]


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a regular test user holding the Member role globally.

    Every regular user gets Member (migration and registration), so this is
    the access a normal account has.
    """
    seed_rbac_data(db_session)
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    assert rbac_service.assign_member_role(db_session, user.id) is not None
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session: Session) -> User:
    """Create an admin test user with Global Admin role."""
    # Seed RBAC data (roles and permissions)
    seed_rbac_data(db_session)

    # Create admin user
    user = User(
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("adminpassword123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    # Assign Global Admin role
    global_admin_role = rbac_service.get_role_by_name(db_session, GLOBAL_ADMIN_ROLE)
    if global_admin_role:
        rbac_service.assign_role_to_user(
            db_session, user_id=user.id, role_id=global_admin_role.id
        )

    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def authenticated_client(client: TestClient, test_user: User) -> TestClient:
    """Create an authenticated test client."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpassword123"},
    )
    assert response.status_code == 200
    return client


@pytest.fixture
def admin_client(client: TestClient, admin_user: User) -> TestClient:
    """Create an authenticated admin test client."""
    response = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "adminpassword123"}
    )
    assert response.status_code == 200
    return client


@pytest.fixture
def user_factory(db_session: Session) -> UserFactory:
    """Return a builder for users with optional role assignments.

    The builder takes ``username``, ``roles`` (role names, seeded on demand)
    and ``company`` (scope for the role assignments; ``None`` means global).
    Without ``roles`` the user holds Member globally, like every real regular
    account; pass ``roles=()`` for a user without any role.
    Every built user logs in with ``FACTORY_LOGIN``.
    """

    def build(
        username: str,
        roles: Sequence[str] | None = None,
        company: Company | None = None,
    ) -> User:
        if roles is None:
            roles = (MEMBER_ROLE,)
        user = User(
            username=username,
            email=f"{username}@example.com",
            hashed_password=get_password_hash(FACTORY_LOGIN),
            is_active=True,
        )
        db_session.add(user)
        db_session.flush()
        if roles:
            seed_rbac_data(db_session)
        for role_name in roles:
            role = rbac_service.get_role_by_name(db_session, role_name)
            assert role is not None, f"unknown role {role_name}"
            rbac_service.assign_role_to_user(
                db_session,
                user_id=user.id,
                role_id=role.id,
                company_id=company.id if company else None,
            )
        db_session.commit()
        db_session.refresh(user)
        return user

    return build


@pytest.fixture
def second_user(user_factory: UserFactory) -> User:
    """Create a second regular user holding Member globally."""
    return user_factory("seconduser")


@pytest.fixture
def viewer_company(db_session: Session) -> Company:
    """Create the company that ``company_viewer_user`` is scoped to."""
    company = Company(name="Viewer Company", type=CompanyType.EMPLOYER)
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


@pytest.fixture
def company_viewer_user(user_factory: UserFactory, viewer_company: Company) -> User:
    """Create a user holding Company Viewer on ``viewer_company`` only."""
    return user_factory(
        "companyviewer", roles=["Company Viewer"], company=viewer_company
    )


@pytest.fixture
def login(client: TestClient) -> Generator[LoginHelper]:
    """Return ``login(client, user)``, which logs a factory user in.

    Each call returns a new client with its own cookie jar on the same app and
    database override, so several users can act in one test.
    """
    opened: list[TestClient] = []

    def do_login(base: TestClient, user: User) -> TestClient:
        user_client = TestClient(base.app)
        opened.append(user_client)
        response = user_client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": FACTORY_LOGIN},
        )
        assert response.status_code == 200, response.text
        return user_client

    yield do_login
    for user_client in opened:
        user_client.close()
