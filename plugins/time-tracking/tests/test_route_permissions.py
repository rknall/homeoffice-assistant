# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Permission checks on every time-tracking route."""

import importlib
import uuid
from collections.abc import Callable, Generator
from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models import Company, User
from src.models.enums import CompanyType
from src.rbac.roles import GLOBAL_ADMIN_ROLE, MEMBER_ROLE
from src.security import get_password_hash
from src.services import rbac_service

BASE = "/api/v1/plugin/time-tracking"
TT_LOGIN = "tt-login-secret-123"
ENTRY_ID = "00000000-0000-0000-0000-000000000001"
COMPANY_SLOT = "{company}"

# Every route of the plugin router and the code it requires. None marks the
# one route that only needs a login.
ROUTE_CODES: dict[tuple[str, str], str | None] = {
    ("GET", "/entries"): "time-tracking.records.read",
    ("POST", "/entries"): "time-tracking.records.write",
    ("GET", "/entries/{entry_id}"): "time-tracking.records.read",
    ("PUT", "/entries/{entry_id}"): "time-tracking.records.write",
    ("DELETE", "/entries/{entry_id}"): "time-tracking.records.delete",
    ("POST", "/check-in"): "time-tracking.records.write",
    ("POST", "/check-out"): "time-tracking.records.write",
    ("GET", "/status"): "time-tracking.records.read",
    ("GET", "/today"): "time-tracking.records.read",
    ("GET", "/daily-summary"): "time-tracking.records.read",
    ("GET", "/leave-balance"): "time-tracking.records.read",
    ("PUT", "/leave-balance"): "time-tracking.records.write",
    ("GET", "/settings/company/{company_id}"): "time-tracking.records.read",
    ("POST", "/settings/company/{company_id}"): "time-tracking.settings.write",
    ("PUT", "/settings/company/{company_id}"): "time-tracking.settings.write",
    ("GET", "/holidays"): "time-tracking.records.read",
    ("GET", "/holidays/custom"): "time-tracking.records.read",
    ("POST", "/holidays/custom"): "time-tracking.records.write",
    ("GET", "/reports/monthly"): "time-tracking.reports.read",
    ("GET", "/info"): None,
}

TODAY = date.today().isoformat()
YEAR = date.today().year

# One request per route: (method, url, query params, json body). URLs and
# bodies may hold COMPANY_SLOT, replaced by a real company id.
Request = tuple[str, str, dict[str, Any] | None, dict[str, Any] | None]
REQUESTS: dict[tuple[str, str], Request] = {
    ("GET", "/entries"): ("GET", "/entries", None, None),
    ("POST", "/entries"): ("POST", "/entries", None, {"date": TODAY}),
    ("GET", "/entries/{entry_id}"): ("GET", f"/entries/{ENTRY_ID}", None, None),
    ("PUT", "/entries/{entry_id}"): (
        "PUT",
        f"/entries/{ENTRY_ID}",
        None,
        {"notes": "x"},
    ),
    ("DELETE", "/entries/{entry_id}"): (
        "DELETE",
        f"/entries/{ENTRY_ID}",
        None,
        None,
    ),
    ("POST", "/check-in"): ("POST", "/check-in", None, {}),
    ("POST", "/check-out"): ("POST", "/check-out", None, {}),
    ("GET", "/status"): ("GET", "/status", None, None),
    ("GET", "/today"): ("GET", "/today", None, None),
    ("GET", "/daily-summary"): (
        "GET",
        "/daily-summary",
        {"summary_date": TODAY},
        None,
    ),
    ("GET", "/leave-balance"): ("GET", "/leave-balance", None, None),
    ("PUT", "/leave-balance"): (
        "PUT",
        "/leave-balance",
        None,
        {"vacation_entitled": 25},
    ),
    ("GET", "/settings/company/{company_id}"): (
        "GET",
        f"/settings/company/{COMPANY_SLOT}",
        None,
        None,
    ),
    ("POST", "/settings/company/{company_id}"): (
        "POST",
        f"/settings/company/{COMPANY_SLOT}",
        None,
        {},
    ),
    ("PUT", "/settings/company/{company_id}"): (
        "PUT",
        f"/settings/company/{COMPANY_SLOT}",
        None,
        {"lock_period_days": 5},
    ),
    ("GET", "/holidays"): ("GET", "/holidays", {"year": YEAR}, None),
    ("GET", "/holidays/custom"): ("GET", "/holidays/custom", {"year": YEAR}, None),
    ("POST", "/holidays/custom"): (
        "POST",
        "/holidays/custom",
        None,
        {"date": TODAY, "name": "Office closed"},
    ),
    ("GET", "/reports/monthly"): (
        "GET",
        "/reports/monthly",
        {"year": YEAR, "month": 1},
        None,
    ),
    ("GET", "/info"): ("GET", "/info", None, None),
}

# Routes that read the company id from the request body.
BODY_ROUTES = [
    ("POST", "/entries"),
    ("POST", "/check-in"),
    ("POST", "/holidays/custom"),
]
PROTECTED = [key for key, code in ROUTE_CODES.items() if code is not None]

UserBuilder = Callable[..., TestClient]


def _send(
    http: TestClient, key: tuple[str, str], company_id: str, with_company: bool
) -> int:
    """Send the sample request for a route and return the status code."""
    method, url, params, body = REQUESTS[key]
    url = url.replace(COMPANY_SLOT, company_id)
    if body is not None and with_company:
        body = {**body, "company_id": company_id}
    response = http.request(method, BASE + url, params=params, json=body)
    return response.status_code


@pytest.fixture
def companies(db_session: Session) -> dict[str, Company]:
    """Create the companies Alpha and Beta."""
    alpha = Company(name="Alpha", type=CompanyType.EMPLOYER)
    beta = Company(name="Beta", type=CompanyType.EMPLOYER)
    db_session.add_all([alpha, beta])
    db_session.commit()
    return {"alpha": alpha, "beta": beta}


@pytest.fixture
def make_user(tt_client: TestClient, db_session: Session) -> Generator[UserBuilder]:
    """Return ``make_user(name, role=None, company=None)``, a logged-in client.

    The role is assigned globally unless a company is given. Each client has
    its own cookie jar on the shared app.
    """
    opened: list[TestClient] = []

    def build(
        name: str, role: str | None = None, company: Company | None = None
    ) -> TestClient:
        user = User(
            username=name,
            email=f"{name}@example.com",
            hashed_password=get_password_hash(TT_LOGIN),
            is_active=True,
        )
        db_session.add(user)
        db_session.flush()
        if role is not None:
            found = rbac_service.get_role_by_name(db_session, role)
            assert found is not None, role
            rbac_service.assign_role_to_user(
                db_session,
                user_id=user.id,
                role_id=found.id,
                company_id=company.id if company else None,
            )
        db_session.commit()
        http = TestClient(tt_client.app)
        opened.append(http)
        response = http.post(
            "/api/v1/auth/login",
            json={"username": name, "password": TT_LOGIN},
        )
        assert response.status_code == 200, response.text
        return http

    yield build
    for http in opened:
        http.close()


def test_route_table_matches_router() -> None:
    """Every plugin route has an entry in ROUTE_CODES, and no entry is stale."""
    routes = importlib.import_module("plugins.time-tracking.backend.routes")
    mounted = {
        (method, route.path)
        for route in routes.router.routes
        for method in route.methods
    }
    assert mounted == set(ROUTE_CODES)
    assert set(REQUESTS) == set(ROUTE_CODES)


@pytest.mark.parametrize("key", PROTECTED, ids=lambda k: f"{k[0]} {k[1]}")
def test_user_without_code_is_denied(
    key: tuple[str, str], make_user: UserBuilder, companies: dict[str, Company]
) -> None:
    """A user without roles gets 403, a Global Admin passes the check."""
    company_id = str(companies["alpha"].id)
    nobody = make_user("nobody")
    admin = make_user("boss", role=GLOBAL_ADMIN_ROLE)
    assert _send(nobody, key, company_id, with_company=False) == 403
    assert _send(admin, key, company_id, with_company=False) not in (401, 403, 422)


@pytest.mark.parametrize("with_company", [True, False], ids=["company", "none"])
@pytest.mark.parametrize("key", BODY_ROUTES, ids=lambda k: f"{k[0]} {k[1]}")
def test_body_company_id_is_checked(
    key: tuple[str, str],
    with_company: bool,
    make_user: UserBuilder,
    companies: dict[str, Company],
) -> None:
    """Body routes deny with and without a company id, and admit an admin."""
    company_id = str(companies["alpha"].id)
    nobody = make_user("nobody")
    admin = make_user("boss", role=GLOBAL_ADMIN_ROLE)
    assert _send(nobody, key, company_id, with_company) == 403
    assert _send(admin, key, company_id, with_company) == 200


def test_body_company_scope(
    make_user: UserBuilder, companies: dict[str, Company]
) -> None:
    """A body company id is checked against that company's roles."""
    alpha, beta = (str(companies[name].id) for name in ("alpha", "beta"))
    beta_member = make_user("betamember", role=MEMBER_ROLE, company=companies["beta"])
    key = ("POST", "/holidays/custom")
    assert _send(beta_member, key, alpha, with_company=True) == 403
    assert _send(beta_member, key, beta, with_company=True) == 200


def test_member_keeps_time_tracking(
    make_user: UserBuilder, companies: dict[str, Company]
) -> None:
    """A global Member can do what a role-less user could do before."""
    alpha = str(companies["alpha"].id)
    member = make_user("member", role=MEMBER_ROLE)

    response = member.put(
        f"{BASE}/settings/company/{alpha}", json={"lock_period_days": 3}
    )
    assert response.status_code == 200, response.text
    assert response.json()["lock_period_days"] == 3

    response = member.put(f"{BASE}/leave-balance", json={"vacation_entitled": 30})
    assert response.status_code == 200, response.text

    response = member.post(
        f"{BASE}/holidays/custom",
        json={"date": TODAY, "name": "Company day", "company_id": alpha},
    )
    assert response.status_code == 200, response.text

    response = member.post(f"{BASE}/check-in", json={"company_id": alpha})
    assert response.status_code == 200, response.text
    response = member.post(f"{BASE}/check-out", json={})
    assert response.status_code == 200, response.text


def test_company_viewer_cannot_write_settings(
    make_user: UserBuilder, companies: dict[str, Company]
) -> None:
    """Company Viewer on Alpha holds no plugin code."""
    alpha = companies["alpha"]
    viewer = make_user("viewer", role="Company Viewer", company=alpha)
    response = viewer.put(
        f"{BASE}/settings/company/{alpha.id}", json={"lock_period_days": 3}
    )
    assert response.status_code == 403


def test_settings_write_is_company_scoped(
    make_user: UserBuilder, companies: dict[str, Company]
) -> None:
    """settings.write held only on Beta does not reach Alpha."""
    beta_member = make_user("betamember", role=MEMBER_ROLE, company=companies["beta"])
    body = {"lock_period_days": 3}
    alpha_url = f"{BASE}/settings/company/{companies['alpha'].id}"
    beta_url = f"{BASE}/settings/company/{companies['beta'].id}"
    assert beta_member.put(alpha_url, json=body).status_code == 403
    assert beta_member.put(beta_url, json=body).status_code == 200


def test_info_needs_login_only(tt_client: TestClient, make_user: UserBuilder) -> None:
    """GET /info answers any logged-in user and rejects anonymous calls."""
    assert tt_client.get(f"{BASE}/info").status_code == 401
    assert make_user("nobody").get(f"{BASE}/info").status_code == 200


@pytest.mark.parametrize(
    ("url", "params"),
    [
        ("/entries/not-a-uuid", None),
        ("/settings/company/not-a-uuid", None),
        ("/entries", {"company_id": "not-a-uuid"}),
        ("/reports/monthly", {"year": YEAR, "month": 13}),
        ("/reports/monthly", {"year": YEAR, "month": 0}),
    ],
)
def test_invalid_params_give_422(
    url: str, params: dict[str, Any] | None, make_user: UserBuilder
) -> None:
    """Malformed ids and out-of-range months are rejected by validation."""
    member = make_user("member", role=MEMBER_ROLE)
    assert member.get(BASE + url, params=params).status_code == 422


def test_invalid_body_company_id_gives_422(make_user: UserBuilder) -> None:
    """A malformed company id in a body is rejected before the check."""
    member = make_user("member", role=MEMBER_ROLE)
    response = member.post(f"{BASE}/check-in", json={"company_id": "nope"})
    assert response.status_code == 422


def test_unknown_entry_returns_404_for_member(make_user: UserBuilder) -> None:
    """Ownership still applies on top of the code: unknown entries are 404."""
    member = make_user("member", role=MEMBER_ROLE)
    response = member.get(f"{BASE}/entries/{uuid.uuid4()}")
    assert response.status_code == 404


def test_entry_move_checks_target_company(
    make_user: UserBuilder, companies: dict[str, Company]
) -> None:
    """Moving an entry needs the write code for the company it moves to."""
    alpha, beta = (str(companies[name].id) for name in ("alpha", "beta"))
    beta_member = make_user("betamember", role=MEMBER_ROLE, company=companies["beta"])
    created = beta_member.post(
        f"{BASE}/entries", json={"date": TODAY, "company_id": beta}
    )
    assert created.status_code == 200, created.text
    url = f"{BASE}/entries/{created.json()['id']}"

    assert beta_member.put(url, json={"company_id": alpha}).status_code == 403
    assert beta_member.put(url, json={"notes": "x"}).status_code == 403
    moved = beta_member.put(url, json={"company_id": beta, "notes": "x"})
    assert moved.status_code == 200, moved.text
    assert moved.json()["company_id"] == beta
