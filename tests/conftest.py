# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment before importing app
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-32chars!"  # nosec - test-only secret  # noqa: S105
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from src.database import get_db
from src.main import app
from src.models import User
from src.models.base import Base
from src.security import get_password_hash
from src.services import rbac_service
from src.services.rbac_seed_service import seed_rbac_data

# Test database setup
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session) -> User:
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        is_admin=False,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session) -> User:
    """Create an admin test user with Global Admin role."""
    # Seed RBAC data (roles and permissions)
    seed_rbac_data(db_session)

    # Create admin user
    user = User(
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("adminpassword123"),
        is_admin=True,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    # Assign Global Admin role
    global_admin_role = rbac_service.get_role_by_name(db_session, "Global Admin")
    if global_admin_role:
        rbac_service.assign_role_to_user(
            db_session, user_id=user.id, role_id=global_admin_role.id
        )

    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def authenticated_client(client, test_user):
    """Create an authenticated test client."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpassword123"},
    )
    assert response.status_code == 200
    return client


@pytest.fixture
def admin_client(client, admin_user):
    """Create an authenticated admin test client."""
    response = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "adminpassword123"}
    )
    assert response.status_code == 200
    return client
