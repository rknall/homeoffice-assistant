# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for auth_service."""

from datetime import datetime, timedelta

from src.models import SystemSettings, User
from src.models.session import Session as SessionModel
from src.schemas.auth import RegisterRequest
from src.security import get_password_hash
from src.services import auth_service
from src.services import email_template_service as email_service


def create_user(db_session, username: str = "existing") -> User:
    """Helper to create a persisted user."""
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password=get_password_hash("Secret123!"),
        is_admin=False,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_is_first_run_true_when_no_users(db_session):
    assert auth_service.is_first_run(db_session) is True


def test_is_first_run_false_when_user_exists(db_session):
    create_user(db_session)
    assert auth_service.is_first_run(db_session) is False


def test_first_run_complete_setting(db_session):
    assert auth_service.get_first_run_complete_setting(db_session) is False
    auth_service.set_first_run_complete(db_session)
    assert auth_service.get_first_run_complete_setting(db_session) is True


def test_registration_enabled_setting(db_session):
    assert auth_service.is_registration_enabled(db_session) is False
    db_session.add(
        SystemSettings(key="registration_enabled", value="true", is_encrypted=False)
    )
    db_session.commit()
    assert auth_service.is_registration_enabled(db_session) is True


def test_register_user_first_run_creates_admin_and_template(db_session, monkeypatch):
    called = {}

    def fake_default(db):
        called["called"] = True

    monkeypatch.setattr(
        email_service,
        "ensure_default_template_exists",
        fake_default,
    )

    request = RegisterRequest(
        username="firstuser",
        email="first@example.com",
        password="ComplexPass1!",
        full_name="First User",
    )

    user = auth_service.register_user(db_session, request)

    assert user.is_admin is True
    assert user.role.value == "admin"
    assert called["called"] is True


def test_register_user_after_first_run(db_session):
    create_user(db_session)
    request = RegisterRequest(
        username="lateruser",
        email="later@example.com",
        password="ComplexPass1!",
        full_name="Later User",
    )

    user = auth_service.register_user(db_session, request)

    assert user.is_admin is False
    assert user.role.value == "user"


def test_authenticate_success_and_failures(db_session):
    user = create_user(db_session, username="authuser")
    assert auth_service.authenticate(db_session, "authuser", "Secret123!") == user
    assert auth_service.authenticate(db_session, "authuser", "wrong") is None
    assert auth_service.authenticate(db_session, "nouser", "Secret123!") is None

    user.is_active = False
    db_session.commit()
    assert auth_service.authenticate(db_session, "authuser", "Secret123!") is None


def test_session_lifecycle(db_session):
    user = create_user(db_session, "sessionuser")
    token = auth_service.create_session(db_session, user.id)
    session = auth_service.get_session(db_session, token)
    assert session is not None
    assert session.user_id == user.id

    # Force expiry and ensure it gets deleted
    session.expires_at = datetime.utcnow() - timedelta(days=1)
    db_session.commit()
    assert auth_service.get_session(db_session, token) is None
    assert auth_service.delete_session(db_session, token) is False


def test_delete_session_returns_true(db_session):
    user = create_user(db_session, "deleteuser")
    token = auth_service.create_session(db_session, user.id)
    assert auth_service.delete_session(db_session, token) is True
    assert auth_service.delete_session(db_session, "missing") is False


def test_get_user_helpers(db_session):
    user = create_user(db_session, "lookup")
    assert auth_service.get_user_by_id(db_session, user.id) == user
    assert auth_service.get_user_by_username(db_session, "lookup") == user
    assert auth_service.get_user_by_email(db_session, "lookup@example.com") == user


def test_cleanup_expired_sessions(db_session):
    user = create_user(db_session, "cleaner")
    for idx in range(3):
        token = auth_service.create_session(db_session, user.id)
        session = db_session.query(SessionModel).filter_by(token=token).first()
        session.expires_at = datetime.utcnow() - timedelta(days=idx + 1)
    db_session.commit()

    deleted = auth_service.cleanup_expired_sessions(db_session)

    assert deleted == 3
    assert db_session.query(SessionModel).count() == 0
