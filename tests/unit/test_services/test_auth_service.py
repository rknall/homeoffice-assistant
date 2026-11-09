# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for auth_service."""

from datetime import timedelta

from src.models import SystemSettings, User
from src.models.session import Session as SessionModel
from src.rbac.roles import GLOBAL_ADMIN_ROLE, MEMBER_ROLE
from src.schemas.auth import RegisterRequest
from src.security import get_password_hash
from src.services import auth_service, rbac_service
from src.services import email_template_service as email_service
from src.services.rbac_seed_service import seed_rbac_data
from src.utils.time import utc_now

REGISTER_LOGIN = "ComplexPass1!"


def create_user(db_session, username: str = "existing") -> User:
    """Helper to create a persisted user."""
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password=get_password_hash("Secret123!"),
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
    db_session.add(SystemSettings(key="registration_enabled", value="true"))
    db_session.commit()
    assert auth_service.is_registration_enabled(db_session) is True


def test_register_user_first_run_creates_admin_and_template(db_session, monkeypatch):
    # Seed RBAC data so Global Admin role exists
    seed_rbac_data(db_session)

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

    assert rbac_service.is_global_admin(db_session, user)
    # User roles are assigned via RBAC system
    assert len(user.user_roles) > 0
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

    assert not rbac_service.is_global_admin(db_session, user)
    # Without seeded roles there is no Member role to assign
    assert len(user.user_roles) == 0


def _register(db_session, username: str) -> User:
    """Register a user through the service with a fixed login secret."""
    request = RegisterRequest(
        username=username,
        email=f"{username}@example.com",
        password=REGISTER_LOGIN,
        full_name=username.title(),
    )
    return auth_service.register_user(db_session, request)


def test_first_registered_user_holds_only_global_admin(db_session):
    seed_rbac_data(db_session)

    user = _register(db_session, "firstadmin")

    assert [(ur.role.name, ur.company_id) for ur in user.user_roles] == [
        (GLOBAL_ADMIN_ROLE, None)
    ]


def test_later_registered_user_gets_member_globally(db_session):
    seed_rbac_data(db_session)
    _register(db_session, "firstadmin")
    db_session.add(SystemSettings(key="registration_enabled", value="true"))
    db_session.commit()

    user = _register(db_session, "selfregistered")

    assert [(ur.role.name, ur.company_id) for ur in user.user_roles] == [
        (MEMBER_ROLE, None)
    ]
    permissions = rbac_service.get_user_permissions(db_session, user)
    assert "event.read" in permissions
    assert "company.view" in permissions


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
    session.expires_at = utc_now() - timedelta(days=1)
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
        session.expires_at = utc_now() - timedelta(days=idx + 1)
    db_session.commit()

    deleted = auth_service.cleanup_expired_sessions(db_session)

    assert deleted == 3
    assert db_session.query(SessionModel).count() == 0


def test_session_reloaded_from_database_is_valid(db_session):
    user = create_user(db_session, "reloaduser")
    token = auth_service.create_session(db_session, user.id)
    db_session.expire_all()

    session = auth_service.get_session(db_session, token)

    assert session is not None
    assert session.expires_at.tzinfo is None
