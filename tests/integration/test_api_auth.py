# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Session cookie, username check, profile and avatar routes of the auth API."""

from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.main import app
from src.models import SystemSettings, User

AUTH = "/api/v1/auth"
LOGIN = {"username": "testuser", "password": "testpassword123"}
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def _session_cookie_header(response: httpx.Response) -> str:
    """Return the Set-Cookie header of the session cookie."""
    headers = response.headers.get_list("set-cookie")
    return next(h for h in headers if h.startswith("session="))


def test_login_cookie_not_secure_over_http(client: TestClient, test_user: User) -> None:
    response = client.post(f"{AUTH}/login", json=LOGIN)

    assert response.status_code == 200
    header = _session_cookie_header(response).lower()
    assert "httponly" in header
    assert "secure" not in header


def test_login_cookie_secure_over_https(client: TestClient, test_user: User) -> None:
    https_client = TestClient(app, base_url="https://testserver")

    response = https_client.post(f"{AUTH}/login", json=LOGIN)

    assert response.status_code == 200
    assert "secure" in _session_cookie_header(response).lower()


def test_check_username_answers_on_first_run(client: TestClient) -> None:
    response = client.get(f"{AUTH}/check-username/somebody")

    assert response.status_code == 200
    assert response.json() == {"available": True, "username": "somebody"}


def test_check_username_forbidden_after_setup(
    client: TestClient, test_user: User
) -> None:
    response = client.get(f"{AUTH}/check-username/testuser")

    assert response.status_code == 403


def test_check_username_answers_when_registration_enabled(
    client: TestClient, test_user: User, db_session: Session
) -> None:
    db_session.add(SystemSettings(key="registration_enabled", value="true"))
    db_session.commit()

    response = client.get(f"{AUTH}/check-username/testuser")

    assert response.status_code == 200
    assert response.json()["available"] is False


def test_profile_password_change_needs_current_password(
    authenticated_client: TestClient,
) -> None:
    missing = authenticated_client.put(f"{AUTH}/me", json={"new_password": "x" * 10})
    wrong = authenticated_client.put(
        f"{AUTH}/me",
        json={"new_password": "x" * 10, "current_password": "not-the-password"},
    )

    assert missing.status_code == 400
    assert "required" in missing.json()["detail"]
    assert wrong.status_code == 400
    assert "incorrect" in wrong.json()["detail"]


def test_profile_update_changes_name(authenticated_client: TestClient) -> None:
    response = authenticated_client.put(
        f"{AUTH}/me", json={"full_name": "Test Person", "use_gravatar": False}
    )

    assert response.status_code == 200
    user = response.json()["user"]
    assert user["full_name"] == "Test Person"
    assert user["use_gravatar"] is False


def test_own_avatar_is_served_at_its_url(
    authenticated_client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The avatar_url the API returns loads the uploaded image."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "static").mkdir()
    (tmp_path / "static" / "index.html").write_text("<html></html>")

    uploaded = authenticated_client.post(
        f"{AUTH}/me/avatar", files={"file": ("me.png", PNG, "image/png")}
    )

    assert uploaded.status_code == 200
    avatar_url = uploaded.json()["user"]["avatar_url"]
    assert avatar_url.startswith("/avatars/")
    served = authenticated_client.get(avatar_url)
    assert served.status_code == 200
    assert served.content == PNG

    deleted = authenticated_client.delete(f"{AUTH}/me/avatar")
    assert deleted.json()["user"]["avatar_url"] is None
    assert list((tmp_path / "static" / "avatars").iterdir()) == []


def test_own_avatar_rejects_content_not_matching_type(
    authenticated_client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    response = authenticated_client.post(
        f"{AUTH}/me/avatar", files={"file": ("me.png", b"<svg/>", "image/png")}
    )

    assert response.status_code == 400
    assert "does not match" in response.json()["detail"]


def test_legacy_avatar_url_is_reported_at_served_path(
    authenticated_client: TestClient, test_user: User, db_session: Session
) -> None:
    """Rows stored with /static/avatars/... are returned as /avatars/..."""
    test_user.avatar_url = "/static/avatars/old.png"
    db_session.commit()

    response = authenticated_client.get(f"{AUTH}/me")

    assert response.json()["user"]["avatar_url"] == "/avatars/old.png"
