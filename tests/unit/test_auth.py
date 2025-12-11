# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
import os

# Set test environment
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-32chars!"  # noqa: S105
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from src.schemas.auth import RegisterRequest
from src.security import get_password_hash, verify_password
from src.services import auth_service


class TestPasswordHashing:
    """Test password hashing utilities."""

    def test_hash_password_produces_hash(self):
        """Test that hashing produces a bcrypt hash."""
        password = "my-secure-password"  # noqa: S105
        hashed = get_password_hash(password)

        assert hashed != password
        assert hashed.startswith("$2b$")

    def test_hash_password_different_each_time(self):
        """Test that hashing the same password produces different hashes (salted)."""
        password = "my-secure-password"  # noqa: S105

        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test verifying a correct password."""
        password = "my-secure-password"  # noqa: S105
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test verifying an incorrect password."""
        password = "my-secure-password"  # noqa: S105
        hashed = get_password_hash(password)

        assert verify_password("wrong-password", hashed) is False

    def test_verify_password_empty(self):
        """Test verifying an empty password."""
        password = "my-secure-password"  # noqa: S105
        hashed = get_password_hash(password)

        assert verify_password("", hashed) is False


class TestAuthService:
    """Test authentication service."""

    def test_is_first_run_true(self, db_session):
        """Test that first run is detected when no users exist."""
        assert auth_service.is_first_run(db_session) is True

    def test_is_first_run_false(self, db_session, test_user):
        """Test that first run is false when users exist."""
        assert auth_service.is_first_run(db_session) is False

    def test_register_first_user_is_admin(self, db_session):
        """Test that the first registered user becomes admin."""
        request = RegisterRequest(
            username="firstuser",
            email="first@example.com",
            password="password123",  # noqa: S106
        )
        user = auth_service.register_user(db_session, request)

        assert user is not None
        assert user.is_admin is True

    def test_register_second_user_not_admin(self, db_session):
        """Test that subsequent users are not admin."""
        # Create first user (admin)
        first_request = RegisterRequest(
            username="firstuser",
            email="first@example.com",
            password="password123",  # noqa: S106
        )
        auth_service.register_user(db_session, first_request)

        # Create second user (not admin)
        second_request = RegisterRequest(
            username="seconduser",
            email="second@example.com",
            password="password123",  # noqa: S106
        )
        user = auth_service.register_user(db_session, second_request)

        assert user is not None
        assert user.is_admin is False

    def test_authenticate_valid_credentials(self, db_session, test_user):
        """Test authenticating with valid credentials."""
        user = auth_service.authenticate(
            db_session,
            username="testuser",
            password="testpassword123",  # noqa: S106
        )

        assert user is not None
        assert user.username == "testuser"

    def test_authenticate_invalid_username(self, db_session, test_user):
        """Test authenticating with invalid username."""
        user = auth_service.authenticate(
            db_session,
            username="wronguser",
            password="testpassword123",  # noqa: S106
        )

        assert user is None

    def test_authenticate_invalid_password(self, db_session, test_user):
        """Test authenticating with invalid password."""
        user = auth_service.authenticate(
            db_session,
            username="testuser",
            password="wrongpassword",  # noqa: S106
        )

        assert user is None

    def test_create_session(self, db_session, test_user):
        """Test creating a session."""
        token = auth_service.create_session(db_session, test_user.id)

        assert token is not None
        assert len(token) > 20

    def test_get_session_valid(self, db_session, test_user):
        """Test getting a valid session."""
        token = auth_service.create_session(db_session, test_user.id)

        session = auth_service.get_session(db_session, token)

        assert session is not None
        assert session.user_id == test_user.id

    def test_get_session_invalid(self, db_session):
        """Test getting an invalid session."""
        session = auth_service.get_session(db_session, "invalid-token")

        assert session is None

    def test_delete_session(self, db_session, test_user):
        """Test deleting a session."""
        token = auth_service.create_session(db_session, test_user.id)

        # Session should exist initially
        session = auth_service.get_session(db_session, token)
        assert session is not None

        # Delete session
        result = auth_service.delete_session(db_session, token)
        assert result is True

        # Session should be deleted now
        session = auth_service.get_session(db_session, token)
        assert session is None
