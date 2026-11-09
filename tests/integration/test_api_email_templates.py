# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Characterization of the email template endpoints."""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models import Company, User
from src.models.enums import CompanyType
from tests.conftest import LoginHelper

BASE = "/api/v1/email-templates"


def _payload(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "name": "Custom report",
        "reason": "expense_report",
        "subject": "Report {{ event_name }}",
        "body_html": "<p>Hello</p>",
        "body_text": "Hello",
    }
    data.update(overrides)
    return data


@pytest.fixture
def company(db_session: Session) -> Company:
    """Create a company for company-scoped templates."""
    company = Company(name="Template Company", type=CompanyType.EMPLOYER)
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


def test_reasons_lists_variables(authenticated_client: TestClient) -> None:
    """The reasons endpoint lists each reason with its variables."""
    response = authenticated_client.get(f"{BASE}/reasons")

    assert response.status_code == 200
    reasons = {r["reason"]: r for r in response.json()}
    assert "expense_report" in reasons
    assert reasons["expense_report"]["variables"]


def test_default_content_known_and_unknown_reason(
    authenticated_client: TestClient,
) -> None:
    """Default content exists for a known reason and is a 404 otherwise."""
    known = authenticated_client.get(f"{BASE}/default-content/expense_report")
    unknown = authenticated_client.get(f"{BASE}/default-content/no_such_reason")

    assert known.status_code == 200
    assert unknown.status_code == 404


def test_admin_creates_global_template(admin_client: TestClient) -> None:
    """Global Admin holds system.settings.write and may create a global template."""
    created = admin_client.post(BASE, json=_payload())

    assert created.status_code == 201
    assert created.json()["company_id"] is None


def test_member_cannot_create_global_template(
    authenticated_client: TestClient,
) -> None:
    """A Member lacks system.settings.write and gets 403."""
    response = authenticated_client.post(BASE, json=_payload())

    assert response.status_code == 403
    assert "system.settings.write" in response.json()["detail"]


def test_member_manages_company_template(
    authenticated_client: TestClient, company: Company
) -> None:
    """A Member holds company.manage and may create, read, update, delete."""
    created = authenticated_client.post(
        BASE, json=_payload(company_id=str(company.id), contact_types=["billing"])
    )
    assert created.status_code == 201
    template_id = created.json()["id"]
    assert created.json()["company_id"] == str(company.id)

    fetched = authenticated_client.get(f"{BASE}/{template_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Custom report"

    updated = authenticated_client.put(
        f"{BASE}/{template_id}", json={"name": "Renamed", "subject": "New"}
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Renamed"
    assert updated.json()["subject"] == "New"

    deleted = authenticated_client.delete(f"{BASE}/{template_id}")
    assert deleted.status_code == 204
    assert authenticated_client.get(f"{BASE}/{template_id}").status_code == 404


def test_create_validates_company_and_reason(
    admin_client: TestClient, company: Company
) -> None:
    """Unknown company is 404, unknown reason is 400."""
    missing = admin_client.post(BASE, json=_payload(company_id=str(uuid.uuid4())))
    bad_reason = admin_client.post(
        BASE, json=_payload(company_id=str(company.id), reason="bogus")
    )

    assert missing.status_code == 404
    assert bad_reason.status_code == 400
    assert "Invalid template reason" in bad_reason.json()["detail"]


def test_update_validates_reason(admin_client: TestClient, company: Company) -> None:
    """Updating to an unknown reason is a 400; unknown template is a 404."""
    created = admin_client.post(BASE, json=_payload(company_id=str(company.id)))
    template_id = created.json()["id"]

    bad = admin_client.put(f"{BASE}/{template_id}", json={"reason": "bogus"})
    missing = admin_client.put(f"{BASE}/{uuid.uuid4()}", json={"name": "x"})

    assert bad.status_code == 400
    assert missing.status_code == 404


def test_cannot_delete_last_global_template(admin_client: TestClient) -> None:
    """The last global template cannot be deleted, a second one can."""
    first = admin_client.post(BASE, json=_payload(name="First")).json()

    blocked = admin_client.delete(f"{BASE}/{first['id']}")
    assert blocked.status_code == 400
    assert "last global template" in blocked.json()["detail"]

    second = admin_client.post(BASE, json=_payload(name="Second")).json()
    allowed = admin_client.delete(f"{BASE}/{second['id']}")
    assert allowed.status_code == 204


def test_list_filters_by_reason_and_company(
    admin_client: TestClient, company: Company
) -> None:
    """The list endpoint filters by reason and by company (globals included)."""
    admin_client.post(BASE, json=_payload(name="Global"))
    admin_client.post(BASE, json=_payload(name="Scoped", company_id=str(company.id)))

    everything = admin_client.get(BASE)
    by_company = admin_client.get(BASE, params={"company_id": str(company.id)})
    other_reason = admin_client.get(BASE, params={"reason": "no_match"})
    globals_only = admin_client.get(f"{BASE}/global")

    assert {t["name"] for t in everything.json()} == {"Global", "Scoped"}
    assert {t["name"] for t in by_company.json()} == {"Global", "Scoped"}
    assert other_reason.json() == []
    assert [t["name"] for t in globals_only.json()] == ["Global"]


def test_list_global_requires_settings_read(
    client: TestClient, login: LoginHelper, user_factory: Any
) -> None:
    """A user without any role cannot read the global list."""
    user = user_factory("norole", roles=())
    response = login(client, user).get(f"{BASE}/global")

    assert response.status_code == 403


def test_company_viewer_reads_but_cannot_write(
    client: TestClient,
    login: LoginHelper,
    db_session: Session,
    admin_client: TestClient,
    company_viewer_user: User,
    viewer_company: Company,
) -> None:
    """A company viewer may read the company's template but not change it."""
    created = admin_client.post(
        BASE, json=_payload(company_id=str(viewer_company.id))
    ).json()
    viewer = login(client, company_viewer_user)

    read = viewer.get(f"{BASE}/{created['id']}")
    write = viewer.put(f"{BASE}/{created['id']}", json={"name": "Nope"})

    assert read.status_code == 200
    assert write.status_code == 403


def test_preview_with_sample_data(authenticated_client: TestClient) -> None:
    """Without event_id the preview renders against sample data."""
    response = authenticated_client.post(
        f"{BASE}/preview",
        json={
            "reason": "expense_report",
            "subject": "Report",
            "body_html": "<p>Body</p>",
            "body_text": "Body",
        },
    )

    assert response.status_code == 200
    assert response.json()["subject"] == "Report"
    assert response.json()["body_text"] == "Body"


def test_preview_unknown_event_is_not_found(
    authenticated_client: TestClient,
) -> None:
    """A preview for an event the user does not own is a 404."""
    response = authenticated_client.post(
        f"{BASE}/preview",
        json={
            "reason": "expense_report",
            "subject": "s",
            "body_html": "h",
            "body_text": "t",
            "event_id": str(uuid.uuid4()),
        },
    )

    assert response.status_code == 404
