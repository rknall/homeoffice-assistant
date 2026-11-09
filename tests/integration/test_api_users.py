# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Characterization of the user management API (current behavior)."""

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models import User
from src.services import role_admin_service
from tests.conftest import LoginHelper, UserFactory

USERS = "/api/v1/users"
NEW_USER = {
    "username": "newuser",
    "email": "new@example.com",
    "password": "newpassword123",
}
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def test_list_requires_user_manage(authenticated_client: TestClient) -> None:
    assert authenticated_client.get(USERS).status_code == 403


def test_list_as_admin(admin_client: TestClient) -> None:
    assert admin_client.get(USERS).status_code == 200


def test_list_requires_login(client: TestClient) -> None:
    assert client.get(USERS).status_code == 401


def test_list_returns_users_with_permissions(
    admin_client: TestClient, admin_user: User, test_user: User
) -> None:
    body = admin_client.get(USERS).json()

    assert [u["username"] for u in body] == ["admin", "testuser"]
    member = body[1]
    assert "event.read" in member["permissions"]
    assert "hashed_password" not in member


def test_create_user_gets_member_role(admin_client: TestClient) -> None:
    response = admin_client.post(USERS, json=NEW_USER)

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "newuser"
    assert body["is_active"] is True
    assert "event.write" in body["permissions"]
    assert "user.manage" not in body["permissions"]


def test_created_user_can_log_in(admin_client: TestClient) -> None:
    admin_client.post(USERS, json=NEW_USER)

    other = TestClient(admin_client.app)
    response = other.post(
        "/api/v1/auth/login",
        json={"username": "newuser", "password": "newpassword123"},
    )
    assert response.status_code == 200
    other.close()


def test_create_rejects_duplicates(admin_client: TestClient, test_user: User) -> None:
    dup_name = {**NEW_USER, "username": "testuser"}
    dup_mail = {**NEW_USER, "email": "test@example.com"}

    assert admin_client.post(USERS, json=dup_name).status_code == 400
    assert admin_client.post(USERS, json=dup_mail).status_code == 400


@pytest.mark.parametrize(
    "patch",
    [
        {"username": "a b"},
        {"username": "ab"},
        {"email": "not-an-email"},
        {"password": "short"},
    ],
)
def test_create_validates_input(admin_client: TestClient, patch: dict) -> None:
    assert admin_client.post(USERS, json={**NEW_USER, **patch}).status_code == 422


def test_create_requires_user_manage(authenticated_client: TestClient) -> None:
    assert authenticated_client.post(USERS, json=NEW_USER).status_code == 403


def test_get_user_by_id(authenticated_client: TestClient, test_user: User) -> None:
    ok = authenticated_client.get(f"{USERS}/{test_user.id}")
    missing = authenticated_client.get(f"{USERS}/{uuid.uuid4()}")

    assert ok.status_code == 200
    assert ok.json()["email"] == "test@example.com"
    assert missing.status_code == 404


def test_update_user_fields(admin_client: TestClient, test_user: User) -> None:
    response = admin_client.put(
        f"{USERS}/{test_user.id}",
        json={"full_name": "Test User", "use_gravatar": False, "email": "x@y.com"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Test User"
    assert body["use_gravatar"] is False
    assert body["email"] == "x@y.com"


def test_update_password_changes_login(
    admin_client: TestClient, test_user: User
) -> None:
    admin_client.put(f"{USERS}/{test_user.id}", json={"password": "brandnewpass1"})

    other = TestClient(admin_client.app)
    old = other.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpassword123"},
    )
    new = other.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "brandnewpass1"},
    )
    other.close()
    assert old.status_code == 401
    assert new.status_code == 200


def test_update_rejects_duplicate_username_and_email(
    admin_client: TestClient, test_user: User, second_user: User
) -> None:
    url = f"{USERS}/{test_user.id}"

    assert admin_client.put(url, json={"username": "seconduser"}).status_code == 400
    assert (
        admin_client.put(url, json={"email": "seconduser@example.com"}).status_code
        == 400
    )


def test_update_missing_user_is_404(admin_client: TestClient) -> None:
    response = admin_client.put(f"{USERS}/{uuid.uuid4()}", json={"full_name": "x"})

    assert response.status_code == 404


def test_cannot_deactivate_self(admin_client: TestClient, admin_user: User) -> None:
    response = admin_client.put(f"{USERS}/{admin_user.id}", json={"is_active": False})

    assert response.status_code == 400


def test_deactivate_other_user(admin_client: TestClient, test_user: User) -> None:
    response = admin_client.put(f"{USERS}/{test_user.id}", json={"is_active": False})

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_update_requires_user_manage(
    authenticated_client: TestClient, second_user: User
) -> None:
    response = authenticated_client.put(
        f"{USERS}/{second_user.id}", json={"full_name": "x"}
    )

    assert response.status_code == 403


def test_user_manager_cannot_change_system_admin(
    db_session: Session,
    user_factory: UserFactory,
    login: LoginHelper,
    client: TestClient,
    admin_user: User,
) -> None:
    role = role_admin_service.create_role(
        db_session, "User Manager", None, ["user.manage"]
    )
    manager = user_factory("usermanager", roles=[role.name])
    manager_client = login(client, manager)

    response = manager_client.put(f"{USERS}/{admin_user.id}", json={"full_name": "x"})

    assert response.status_code == 403
    assert "system.admin" in response.json()["detail"]


def test_avatar_upload_and_delete(
    admin_client: TestClient,
    test_user: User,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    url = f"{USERS}/{test_user.id}/avatar"

    uploaded = admin_client.post(url, files={"file": ("me.png", PNG, "image/png")})

    assert uploaded.status_code == 200
    body = uploaded.json()
    assert body["avatar_url"].startswith("/avatars/")
    assert body["use_gravatar"] is False
    assert len(list((tmp_path / "static" / "avatars").iterdir())) == 1

    deleted = admin_client.delete(url)

    assert deleted.status_code == 200
    assert deleted.json()["avatar_url"] is None
    assert deleted.json()["use_gravatar"] is True
    assert list((tmp_path / "static" / "avatars").iterdir()) == []


def test_avatar_rejects_bad_type_and_size(
    admin_client: TestClient,
    test_user: User,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    url = f"{USERS}/{test_user.id}/avatar"

    bad_type = admin_client.post(url, files={"file": ("x.exe", b"abc", "text/plain")})
    too_big = admin_client.post(
        url, files={"file": ("big.png", b"0" * (5 * 1024 * 1024 + 1), "image/png")}
    )

    assert bad_type.status_code == 400
    assert too_big.status_code == 400


def test_avatar_unknown_user_is_404(admin_client: TestClient) -> None:
    response = admin_client.post(
        f"{USERS}/{uuid.uuid4()}/avatar", files={"file": ("a.png", PNG, "image/png")}
    )

    assert response.status_code == 404


def test_avatar_requires_user_manage(
    authenticated_client: TestClient, second_user: User
) -> None:
    response = authenticated_client.post(
        f"{USERS}/{second_user.id}/avatar", files={"file": ("a.png", PNG, "image/png")}
    )

    assert response.status_code == 403
