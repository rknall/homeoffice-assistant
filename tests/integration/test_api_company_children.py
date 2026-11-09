# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Characterization of the company, company contact and company calendar routes."""

import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.models import Company, User
from src.services import file_storage_service
from tests.conftest import LoginHelper

COMPANIES = "/api/v1/companies"
PNG = b"\x89PNG\r\n\x1a\n" + b"png-data"
JPEG = b"\xff\xd8\xff\xe0" + b"jpeg-data"
CLEAN_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="4" height="4"/></svg>'
)


@pytest.fixture
def logo_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point logo storage at a temporary directory."""
    monkeypatch.setattr(file_storage_service, "LOGO_DIR", tmp_path)
    return tmp_path


def _create_company(client: TestClient, name: str = "Acme") -> dict[str, Any]:
    response = client.post(COMPANIES, json={"name": name, "type": "employer"})
    assert response.status_code == 201, response.text
    return response.json()


def _contact(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {"name": "Jane Doe", "email": "jane@example.com"}
    data.update(overrides)
    return data


def _calendar(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "name": "Team",
        "calendar_type": "ical",
        "external_id": "https://example.com/team.ics",
    }
    data.update(overrides)
    return data


def test_company_crud(authenticated_client: TestClient) -> None:
    """A Member may create, read, update, list and delete a company."""
    company = _create_company(authenticated_client)
    url = f"{COMPANIES}/{company['id']}"

    assert authenticated_client.get(url).json()["name"] == "Acme"
    updated = authenticated_client.put(url, json={"name": "Acme 2"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Acme 2"
    listed = authenticated_client.get(COMPANIES)
    assert [c["name"] for c in listed.json()] == ["Acme 2"]
    assert authenticated_client.delete(url).status_code == 204
    assert authenticated_client.get(url).status_code == 404


def test_company_duplicate_name_is_rejected(
    authenticated_client: TestClient,
) -> None:
    """Creating or renaming to an existing name is a 400."""
    _create_company(authenticated_client, "One")
    two = _create_company(authenticated_client, "Two")

    duplicate = authenticated_client.post(
        COMPANIES, json={"name": "One", "type": "employer"}
    )
    rename = authenticated_client.put(f"{COMPANIES}/{two['id']}", json={"name": "One"})

    assert duplicate.status_code == 400
    assert rename.status_code == 400


def test_company_unknown_id_is_not_found(authenticated_client: TestClient) -> None:
    """Unknown company ids are 404 for every verb."""
    url = f"{COMPANIES}/{uuid.uuid4()}"

    assert authenticated_client.get(url).status_code == 404
    assert authenticated_client.put(url, json={"name": "x"}).status_code == 404
    assert authenticated_client.delete(url).status_code == 404


def test_company_viewer_sees_only_own_company(
    client: TestClient,
    login: LoginHelper,
    admin_client: TestClient,
    company_viewer_user: User,
    viewer_company: Company,
) -> None:
    """A company viewer lists only the company it holds a role on."""
    _create_company(admin_client, "Hidden")
    viewer = login(client, company_viewer_user)

    listed = viewer.get(COMPANIES)
    hidden_id = next(
        c["id"] for c in admin_client.get(COMPANIES).json() if c["name"] == "Hidden"
    )

    assert [c["name"] for c in listed.json()] == ["Viewer Company"]
    assert viewer.get(f"{COMPANIES}/{hidden_id}").status_code == 403
    assert (
        viewer.put(f"{COMPANIES}/{viewer_company.id}", json={"name": "x"}).status_code
        == 403
    )
    assert (
        viewer.post(COMPANIES, json={"name": "N", "type": "employer"}).status_code
        == 403
    )


def test_company_requires_login(client: TestClient) -> None:
    """An anonymous caller is rejected."""
    assert client.get(COMPANIES).status_code == 401


def test_logo_upload_serve_and_delete(
    authenticated_client: TestClient, logo_dir: Path
) -> None:
    """A logo can be uploaded, served with its media type and removed."""
    company = _create_company(authenticated_client)
    url = f"{COMPANIES}/{company['id']}/logo"

    assert authenticated_client.get(url).status_code == 404

    uploaded = authenticated_client.post(
        url, files={"file": ("logo.png", PNG, "image/png")}
    )
    assert uploaded.status_code == 200
    stored = logo_dir / uploaded.json()["logo_path"]
    assert stored.read_bytes() == PNG

    served = authenticated_client.get(url)
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/png"
    assert served.content == PNG
    assert served.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in served.headers["content-security-policy"]

    assert authenticated_client.delete(url).status_code == 204
    assert not stored.exists()
    assert authenticated_client.get(url).status_code == 404


def test_logo_rejects_bad_extension(
    authenticated_client: TestClient, logo_dir: Path
) -> None:
    """A file type outside the allowed list is a 400."""
    company = _create_company(authenticated_client)
    response = authenticated_client.post(
        f"{COMPANIES}/{company['id']}/logo",
        files={"file": ("logo.exe", b"x", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert "not allowed" in response.json()["detail"]


def test_logo_rejects_oversized_file(
    authenticated_client: TestClient,
    logo_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A file above the size limit is a 400."""
    monkeypatch.setattr(file_storage_service, "MAX_FILE_SIZE", 4)
    company = _create_company(authenticated_client)
    response = authenticated_client.post(
        f"{COMPANIES}/{company['id']}/logo",
        files={"file": ("logo.png", b"12345", "image/png")},
    )

    assert response.status_code == 400
    assert "too large" in response.json()["detail"]


def test_logo_replace_removes_old_file(
    authenticated_client: TestClient, logo_dir: Path
) -> None:
    """Uploading a second logo deletes the first file."""
    company = _create_company(authenticated_client)
    url = f"{COMPANIES}/{company['id']}/logo"
    first = authenticated_client.post(
        url, files={"file": ("a.png", PNG, "image/png")}
    ).json()["logo_path"]
    second = authenticated_client.post(
        url, files={"file": ("b.jpg", JPEG, "image/jpeg")}
    ).json()["logo_path"]

    assert not (logo_dir / first).exists()
    assert (logo_dir / second).exists()


def test_logo_rejects_content_not_matching_extension(
    authenticated_client: TestClient, logo_dir: Path
) -> None:
    """A .png whose bytes are not a PNG is a 400 and nothing is stored."""
    company = _create_company(authenticated_client)
    response = authenticated_client.post(
        f"{COMPANIES}/{company['id']}/logo",
        files={"file": ("logo.png", b"<html>", "image/png")},
    )

    assert response.status_code == 400
    assert list(logo_dir.iterdir()) == []


@pytest.mark.parametrize(
    "svg",
    [
        b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>',
        b'<svg xmlns="http://www.w3.org/2000/svg"><foreignObject/></svg>',
        b'<svg xmlns="http://www.w3.org/2000/svg" xmlns:x="http://www.w3.org/1999/xlink">'
        b'<a x:href="javascript:alert(1)"><text>x</text></a></svg>',
        b'<svg xmlns="http://www.w3.org/2000/svg"><image href="https://evil/x.png"/></svg>',
        b'<!DOCTYPE svg [<!ENTITY a "b">]><svg xmlns="http://www.w3.org/2000/svg"/>',
    ],
)
def test_logo_rejects_unsafe_svg(
    authenticated_client: TestClient, logo_dir: Path, svg: bytes
) -> None:
    """SVGs that could run script or load external content are rejected."""
    company = _create_company(authenticated_client)
    response = authenticated_client.post(
        f"{COMPANIES}/{company['id']}/logo",
        files={"file": ("logo.svg", svg, "image/svg+xml")},
    )

    assert response.status_code == 400
    assert list(logo_dir.iterdir()) == []


def test_clean_svg_logo_is_served_with_csp(
    authenticated_client: TestClient, logo_dir: Path
) -> None:
    """A clean SVG is stored and served sandboxed, with nosniff."""
    company = _create_company(authenticated_client)
    url = f"{COMPANIES}/{company['id']}/logo"

    uploaded = authenticated_client.post(
        url, files={"file": ("logo.svg", CLEAN_SVG, "image/svg+xml")}
    )
    served = authenticated_client.get(url)

    assert uploaded.status_code == 200
    assert served.status_code == 200
    assert served.headers["content-type"].startswith("image/svg+xml")
    assert served.headers["content-security-policy"] == (
        "default-src 'none'; style-src 'unsafe-inline'; sandbox"
    )
    assert served.headers["x-content-type-options"] == "nosniff"
    assert served.content == CLEAN_SVG


def test_company_list_returns_logo_path(
    authenticated_client: TestClient, logo_dir: Path
) -> None:
    """After an upload the list response carries the logo for each company."""
    company = _create_company(authenticated_client)
    logo_path = authenticated_client.post(
        f"{COMPANIES}/{company['id']}/logo",
        files={"file": ("logo.png", PNG, "image/png")},
    ).json()["logo_path"]

    listed = authenticated_client.get(COMPANIES).json()

    assert [c["logo_path"] for c in listed] == [logo_path]


def test_company_delete_removes_logo_file(
    authenticated_client: TestClient, logo_dir: Path
) -> None:
    """Deleting a company deletes its stored logo."""
    company = _create_company(authenticated_client)
    logo_path = authenticated_client.post(
        f"{COMPANIES}/{company['id']}/logo",
        files={"file": ("logo.png", PNG, "image/png")},
    ).json()["logo_path"]
    assert (logo_dir / logo_path).exists()

    assert (
        authenticated_client.delete(f"{COMPANIES}/{company['id']}").status_code == 204
    )

    assert not (logo_dir / logo_path).exists()


def test_contact_crud_and_main_contact(authenticated_client: TestClient) -> None:
    """The first contact becomes main; deleting it promotes the next one."""
    company = _create_company(authenticated_client)
    base = f"{COMPANIES}/{company['id']}/contacts"

    first = authenticated_client.post(base, json=_contact())
    assert first.status_code == 201
    assert first.json()["is_main_contact"] is True
    second = authenticated_client.post(
        base, json=_contact(name="John", email="john@example.com")
    )
    assert second.json()["is_main_contact"] is False

    promoted = authenticated_client.post(f"{base}/{second.json()['id']}/set-main")
    assert promoted.status_code == 200
    assert promoted.json()["is_main_contact"] is True
    contacts = {c["name"]: c for c in authenticated_client.get(base).json()}
    assert contacts["Jane Doe"]["is_main_contact"] is False

    updated = authenticated_client.put(
        f"{base}/{first.json()['id']}", json={"title": "CFO"}
    )
    assert updated.json()["title"] == "CFO"

    assert (
        authenticated_client.delete(f"{base}/{second.json()['id']}").status_code == 204
    )
    remaining = authenticated_client.get(base).json()
    assert [c["name"] for c in remaining] == ["Jane Doe"]
    assert remaining[0]["is_main_contact"] is True


def test_contact_not_found_cases(authenticated_client: TestClient) -> None:
    """Unknown company or contact ids are 404 with distinct messages."""
    company = _create_company(authenticated_client)
    base = f"{COMPANIES}/{company['id']}/contacts"
    missing_company = f"{COMPANIES}/{uuid.uuid4()}/contacts"

    unknown_contact = authenticated_client.get(f"{base}/{uuid.uuid4()}")
    assert unknown_contact.status_code == 404
    assert unknown_contact.json()["detail"] == "Contact not found"
    unknown_company = authenticated_client.get(missing_company)
    assert unknown_company.status_code == 404


def test_contact_rejects_invalid_email(authenticated_client: TestClient) -> None:
    """An invalid email address is a 422."""
    company = _create_company(authenticated_client)
    response = authenticated_client.post(
        f"{COMPANIES}/{company['id']}/contacts", json=_contact(email="not-an-email")
    )

    assert response.status_code == 422


def test_contact_viewer_reads_but_cannot_write(
    client: TestClient,
    login: LoginHelper,
    admin_client: TestClient,
    company_viewer_user: User,
    viewer_company: Company,
) -> None:
    """A company viewer may list contacts but not create one."""
    base = f"{COMPANIES}/{viewer_company.id}/contacts"
    admin_client.post(base, json=_contact())
    viewer = login(client, company_viewer_user)

    assert viewer.get(base).status_code == 200
    assert viewer.post(base, json=_contact(email="x@example.com")).status_code == 403


def test_calendar_crud_and_sync(authenticated_client: TestClient) -> None:
    """Calendars can be created, normalised, updated, synced and deleted."""
    company = _create_company(authenticated_client)
    base = f"{COMPANIES}/{company['id']}/calendars"

    created = authenticated_client.post(base, json=_calendar(color="#aabbcc"))
    assert created.status_code == 201
    body = created.json()
    assert body["color"] == "#AABBCC"
    assert body["last_synced_at"] is None

    got = authenticated_client.get(f"{base}/{body['id']}")
    assert got.json()["name"] == "Team"
    assert len(authenticated_client.get(base).json()) == 1

    updated = authenticated_client.put(
        f"{base}/{body['id']}", json={"name": "Renamed", "is_active": False}
    )
    assert updated.json()["name"] == "Renamed"
    assert updated.json()["is_active"] is False

    synced = authenticated_client.post(f"{base}/{body['id']}/sync")
    assert synced.status_code == 200
    assert synced.json()["last_synced_at"] is not None

    assert authenticated_client.delete(f"{base}/{body['id']}").status_code == 204
    assert authenticated_client.get(f"{base}/{body['id']}").status_code == 404


@pytest.mark.parametrize(
    "overrides",
    [
        {"color": "red"},
        {"sync_interval_minutes": 1},
        {"calendar_type": "unknown"},
        {"name": ""},
    ],
)
def test_calendar_validation(
    authenticated_client: TestClient, overrides: dict[str, Any]
) -> None:
    """Invalid colour, interval, type or name is a 422."""
    company = _create_company(authenticated_client)
    response = authenticated_client.post(
        f"{COMPANIES}/{company['id']}/calendars", json=_calendar(**overrides)
    )

    assert response.status_code == 422


def test_calendar_unknown_id_is_not_found(authenticated_client: TestClient) -> None:
    """An unknown calendar id is a 404 for get, update, delete and sync."""
    company = _create_company(authenticated_client)
    url = f"{COMPANIES}/{company['id']}/calendars/{uuid.uuid4()}"

    assert authenticated_client.get(url).status_code == 404
    assert authenticated_client.put(url, json={"name": "x"}).status_code == 404
    assert authenticated_client.delete(url).status_code == 404
    assert authenticated_client.post(f"{url}/sync").status_code == 404


def test_calendar_viewer_reads_but_cannot_write(
    client: TestClient,
    login: LoginHelper,
    admin_client: TestClient,
    company_viewer_user: User,
    viewer_company: Company,
) -> None:
    """A company viewer may list calendars but not create one."""
    base = f"{COMPANIES}/{viewer_company.id}/calendars"
    viewer = login(client, company_viewer_user)

    assert viewer.get(base).status_code == 200
    assert viewer.post(base, json=_calendar()).status_code == 403
