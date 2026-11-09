# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Company-scoped permission checks on the company level routers."""

from collections.abc import Callable
from datetime import date
from typing import Any

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.main import app
from src.models import Company, Event, User
from src.models.enums import CompanyType
from src.rbac.roles import GLOBAL_ADMIN_ROLE, MEMBER_ROLE

API = "/api/v1"
Login = Callable[[TestClient, User], TestClient]

TEMPLATE = {
    "name": "Report",
    "reason": "expense_report",
    "subject": "Report",
    "body_html": "<p>Report</p>",
    "body_text": "Report",
}


@pytest.fixture
def beta(db_session: Session) -> Company:
    """Create a company the viewer holds no role in."""
    company = Company(name="Beta", type=CompanyType.THIRD_PARTY)
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


@pytest.fixture
def admin(
    client: TestClient, user_factory: Callable[..., User], login: Login
) -> TestClient:
    """Log in a Global Admin."""
    return login(client, user_factory("boss", roles=[GLOBAL_ADMIN_ROLE]))


@pytest.fixture
def member(
    client: TestClient, user_factory: Callable[..., User], login: Login
) -> TestClient:
    """Log in a user holding Member globally."""
    return login(client, user_factory("member", roles=[MEMBER_ROLE]))


@pytest.fixture
def viewer(client: TestClient, company_viewer_user: User, login: Login) -> TestClient:
    """Log in the user holding Company Viewer on ``viewer_company`` only."""
    return login(client, company_viewer_user)


@pytest.fixture
def data(
    db_session: Session,
    admin: TestClient,
    viewer_company: Company,
    beta: Company,
    company_viewer_user: User,
) -> dict[str, str]:
    """Create contacts, calendars and templates of both companies.

    Also creates an event of the viewer on the viewer's company.
    """
    ids: dict[str, str] = {"alpha": str(viewer_company.id), "beta": str(beta.id)}
    for key, company in (("alpha", viewer_company), ("beta", beta)):
        base = f"{API}/companies/{company.id}"
        contact = admin.post(
            f"{base}/contacts", json={"name": "Ann", "email": f"ann@{key}.example"}
        )
        assert contact.status_code == 201, contact.text
        ids[f"{key}_contact"] = contact.json()["id"]
        calendar = admin.post(
            f"{base}/calendars",
            json={"name": "Cal", "calendar_type": "ical", "external_id": "x"},
        )
        assert calendar.status_code == 201, calendar.text
        ids[f"{key}_calendar"] = calendar.json()["id"]
        template = admin.post(
            f"{API}/email-templates",
            json={**TEMPLATE, "name": key, "company_id": str(company.id)},
        )
        assert template.status_code == 201, template.text
        ids[f"{key}_template"] = template.json()["id"]
    template = admin.post(f"{API}/email-templates", json={**TEMPLATE, "name": "g"})
    assert template.status_code == 201, template.text
    ids["global_template"] = template.json()["id"]

    event = Event(
        user_id=company_viewer_user.id,
        company_id=viewer_company.id,
        name="Viewer Event",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 3),
    )
    db_session.add(event)
    db_session.commit()
    ids["event"] = str(event.id)
    return ids


def _request(
    client: TestClient, method: str, path: str, ids: dict[str, str], body: Any
) -> int:
    return client.request(method, API + path.format(**ids), json=body).status_code


VIEWER_READS = [
    "/companies/{alpha}",
    "/companies/{alpha}/contacts",
    "/companies/{alpha}/contacts/{alpha_contact}",
    "/companies/{alpha}/calendars",
    "/companies/{alpha}/calendars/{alpha_calendar}",
    "/email-templates?company_id={alpha}",
    "/email-templates/{alpha_template}",
    "/events/{event}",
    "/events?company_id={alpha}",
    "/events/count?company_id={alpha}",
    "/dashboard/summary",
]

CONTACT = {"name": "Bob", "email": "bob@example.com"}
CALENDAR = {"name": "Cal", "calendar_type": "ical", "external_id": "y"}
VIEWER_WRITES = [
    ("POST", "/companies", {"name": "New", "type": "third_party"}),
    ("PUT", "/companies/{alpha}", {"name": "Renamed"}),
    ("DELETE", "/companies/{alpha}", None),
    ("DELETE", "/companies/{alpha}/logo", None),
    ("POST", "/companies/{alpha}/contacts", CONTACT),
    ("PUT", "/companies/{alpha}/contacts/{alpha_contact}", {"name": "X"}),
    ("DELETE", "/companies/{alpha}/contacts/{alpha_contact}", None),
    ("POST", "/companies/{alpha}/contacts/{alpha_contact}/set-main", None),
    ("POST", "/companies/{alpha}/calendars", CALENDAR),
    ("PUT", "/companies/{alpha}/calendars/{alpha_calendar}", {"name": "X"}),
    ("DELETE", "/companies/{alpha}/calendars/{alpha_calendar}", None),
    ("POST", "/companies/{alpha}/calendars/{alpha_calendar}/sync", None),
    ("POST", "/email-templates", {**TEMPLATE, "company_id": "{alpha}"}),
    ("PUT", "/email-templates/{alpha_template}", {"name": "X"}),
    ("DELETE", "/email-templates/{alpha_template}", None),
    ("POST", "/email-templates", TEMPLATE),
    ("PUT", "/email-templates/{global_template}", {"name": "X"}),
    ("DELETE", "/email-templates/{global_template}", None),
    ("PUT", "/events/{event}", {"name": "X"}),
    ("DELETE", "/events/{event}", None),
    ("POST", "/events/{event}/document-references", {"paperless_doc_id": 1}),
    ("PUT", "/settings/locale", {"date_format": "YYYY-MM-DD"}),
    ("PUT", "/settings/currency", {"base_currency": "USD"}),
]

OTHER_COMPANY_READS = [
    "/companies/{beta}",
    "/companies/{beta}/contacts",
    "/companies/{beta}/contacts/{beta_contact}",
    "/companies/{beta}/calendars",
    "/email-templates?company_id={beta}",
    "/email-templates/{beta_template}",
    "/events?company_id={beta}",
    "/events/count?company_id={beta}",
]


@pytest.mark.parametrize("path", VIEWER_READS)
def test_viewer_reads_own_company(
    viewer: TestClient, data: dict[str, str], path: str
) -> None:
    """A Company Viewer reads the company data of the company it is scoped to."""
    assert _request(viewer, "GET", path, data, None) == 200


@pytest.mark.parametrize(("method", "path", "body"), VIEWER_WRITES)
def test_viewer_cannot_write(
    viewer: TestClient, data: dict[str, str], method: str, path: str, body: Any
) -> None:
    """A Company Viewer gets 403 on every write, also in its own company."""
    if isinstance(body, dict):
        body = {
            k: v.format(**data) if isinstance(v, str) else v for k, v in body.items()
        }
    assert _request(viewer, method, path, data, body) == 403


def test_viewer_cannot_create_event(viewer: TestClient, data: dict[str, str]) -> None:
    """Creating an event needs event.write for the company in the body."""
    body = {
        "name": "Trip",
        "start_date": "2026-04-01",
        "end_date": "2026-04-02",
        "company_id": data["alpha"],
    }
    assert viewer.post(f"{API}/events", json=body).status_code == 403


@pytest.mark.parametrize("path", OTHER_COMPANY_READS)
def test_viewer_cannot_read_other_company(
    viewer: TestClient, data: dict[str, str], path: str
) -> None:
    """A viewer of Alpha gets 403 on the data of Beta."""
    assert _request(viewer, "GET", path, data, None) == 403


def test_viewer_lists_only_permitted_data(
    viewer: TestClient, data: dict[str, str]
) -> None:
    """Unfiltered lists only show the companies the viewer may view."""
    companies = viewer.get(f"{API}/companies").json()
    assert [c["id"] for c in companies] == [data["alpha"]]

    templates = {t["id"] for t in viewer.get(f"{API}/email-templates").json()}
    assert data["alpha_template"] in templates
    assert data["beta_template"] not in templates

    events = viewer.get(f"{API}/events").json()
    assert [e["id"] for e in events] == [data["event"]]
    assert viewer.get(f"{API}/events/count").json() == {"count": 1}


@pytest.mark.parametrize(
    "path",
    [
        "/integrations",
        "/email-templates/global",
    ],
)
def test_viewer_has_no_global_access(
    viewer: TestClient, data: dict[str, str], path: str
) -> None:
    """Company Viewer grants no global codes (integrations, system settings)."""
    assert _request(viewer, "GET", path, data, None) == 403


PAGE_REFERENCE_READS = [
    "/settings/locale",
    "/settings/currency",
    "/integrations/event-custom-field-choices",
]


@pytest.mark.parametrize("path", PAGE_REFERENCE_READS)
def test_viewer_reads_page_reference_data(
    client: TestClient, viewer: TestClient, data: dict[str, str], path: str
) -> None:
    """The reads every events page needs only require a login."""
    assert _request(viewer, "GET", path, data, None) == 200
    assert _request(client, "GET", path, data, None) == 401


def test_member_keeps_access(member: TestClient, data: dict[str, str]) -> None:
    """Member keeps the company, event and settings access of a regular user."""
    alpha = data["alpha"]
    company = {"name": "Mine", "type": "third_party"}
    created = member.post(f"{API}/companies", json=company)
    assert created.status_code == 201
    assert (
        member.put(f"{API}/companies/{alpha}", json={"name": "A2"}).status_code == 200
    )
    contacts = f"{API}/companies/{alpha}/contacts"
    assert member.post(contacts, json=CONTACT).status_code == 201
    calendars = f"{API}/companies/{alpha}/calendars"
    assert member.post(calendars, json=CALENDAR).status_code == 201
    company_template = {**TEMPLATE, "company_id": alpha}
    templates = f"{API}/email-templates"
    assert member.post(templates, json=company_template).status_code == 201
    assert member.get(f"{API}/email-templates/global").status_code == 200

    event = member.post(
        f"{API}/events",
        json={
            "name": "Trip",
            "start_date": "2026-04-01",
            "end_date": "2026-04-02",
            "company_id": alpha,
        },
    )
    assert event.status_code == 201
    event_url = f"{API}/events/{event.json()['id']}"
    assert member.put(event_url, json={"company_id": data["beta"]}).status_code == 200
    assert member.get(f"{API}/settings/locale").status_code == 200
    assert member.get(f"{API}/integrations").status_code == 200
    assert member.get(f"{API}/dashboard/summary").status_code == 200
    assert member.delete(event_url).status_code == 204

    companies = {c["id"] for c in member.get(f"{API}/companies").json()}
    assert {alpha, data["beta"]} <= companies


def test_member_cannot_change_system_scope(
    member: TestClient, data: dict[str, str]
) -> None:
    """Global templates, settings and integrations need admin codes."""
    assert member.post(f"{API}/email-templates", json=TEMPLATE).status_code == 403
    global_url = f"{API}/email-templates/{data['global_template']}"
    assert member.put(global_url, json={"name": "X"}).status_code == 403
    locale = {"date_format": "YYYY-MM-DD"}
    assert member.put(f"{API}/settings/locale", json=locale).status_code == 403
    integration = {"integration_type": "smtp", "name": "Mail", "config": {}}
    assert member.post(f"{API}/integrations", json=integration).status_code == 403


def test_admin_has_all_access(admin: TestClient, data: dict[str, str]) -> None:
    """A Global Admin reaches every company and the global scope."""
    global_url = f"{API}/email-templates/{data['global_template']}"
    assert admin.put(global_url, json={"name": "G2"}).status_code == 200
    beta_template = f"{API}/email-templates/{data['beta_template']}"
    assert admin.delete(beta_template).status_code == 204
    beta = data["beta"]
    contact = f"{API}/companies/{beta}/contacts/{data['beta_contact']}"
    assert admin.delete(contact).status_code == 204
    assert admin.delete(f"{API}/companies/{beta}").status_code == 204
    locale = admin.get(f"{API}/settings/locale").json()
    assert admin.put(f"{API}/settings/locale", json=locale).status_code == 200


REMOVED_ROUTES = [
    ("GET", "/currencies/rate"),
    ("POST", "/currencies/backfill"),
    ("GET", "/email-templates/variables/{reason}"),
    ("GET", "/email-templates/{template_id}/validate-contacts/{company_id}"),
    ("GET", "/companies/{company_id}/contacts/by-type/{contact_type}"),
    ("POST", "/events/{event_id}/sync-paperless"),
    ("GET", "/integrations/{config_id}/tags"),
    ("GET", "/integrations/{config_id}/custom-fields"),
    ("GET", "/integrations/{config_id}/custom-fields/{field_id}"),
    ("GET", "/integrations/{config_id}/custom-fields/{field_id}/choices"),
    ("POST", "/integrations/{config_id}/custom-fields/{field_id}/choices"),
]


@pytest.mark.parametrize(("method", "path"), REMOVED_ROUTES)
def test_unused_routes_removed(method: str, path: str) -> None:
    """Endpoints without any caller are no longer mounted."""
    mounted = {
        (m, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        for m in route.methods
    }
    assert (method, API + path) not in mounted
