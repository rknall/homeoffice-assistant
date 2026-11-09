# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Time-tracking route flows: check-in/out, balance and company settings.

``test_route_permissions`` covers who may call a route; these tests cover
what the routes do for a permitted user.
"""

import importlib
from collections.abc import Generator
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models import Company, User
from src.models.enums import CompanyType
from src.rbac.roles import GLOBAL_ADMIN_ROLE
from src.security import get_password_hash
from src.services import rbac_service

AustrianComplianceValidator = importlib.import_module(
    "plugins.time-tracking.backend.validators"
).AustrianComplianceValidator

BASE = "/api/v1/plugin/time-tracking"
LOGIN = "flow-login-secret-123"


@pytest.fixture
def admin(tt_client: TestClient, db_session: Session) -> Generator[TestClient]:
    """Return a client logged in as a Global Admin."""
    user = User(
        username="flowadmin",
        email="flowadmin@example.com",
        hashed_password=get_password_hash(LOGIN),
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    role = rbac_service.get_role_by_name(db_session, GLOBAL_ADMIN_ROLE)
    assert role is not None
    rbac_service.assign_role_to_user(db_session, user_id=user.id, role_id=role.id)
    db_session.commit()
    http = TestClient(tt_client.app)
    response = http.post(
        "/api/v1/auth/login", json={"username": "flowadmin", "password": LOGIN}
    )
    assert response.status_code == 200, response.text
    yield http
    http.close()


@pytest.fixture
def company(db_session: Session) -> Company:
    """Create one employer company."""
    row = Company(name="Flow Co", type=CompanyType.EMPLOYER)
    db_session.add(row)
    db_session.commit()
    return row


def test_check_in_out_flow(admin: TestClient) -> None:
    """Status follows check-in and check-out; double calls answer 400."""
    assert admin.get(f"{BASE}/status").json()["is_checked_in"] is False
    assert admin.post(f"{BASE}/check-out", json={}).status_code == 400

    opened = admin.post(f"{BASE}/check-in", json={"timezone": "UTC"})
    assert opened.status_code == 200, opened.text
    assert opened.json()["check_out"] is None
    assert admin.post(f"{BASE}/check-in", json={}).status_code == 400

    status = admin.get(f"{BASE}/status").json()
    assert status["is_checked_in"] is True
    assert status["open_entry"]["id"] == opened.json()["id"]

    closed = admin.post(f"{BASE}/check-out", json={"notes": "bye"})
    assert closed.status_code == 200, closed.text
    assert closed.json()["id"] == opened.json()["id"]
    assert closed.json()["check_out"] is not None
    assert admin.get(f"{BASE}/status").json()["is_checked_in"] is False
    today = admin.get(f"{BASE}/today").json()
    assert [entry["id"] for entry in today] == [opened.json()["id"]]


def test_entry_crud_and_overlap(admin: TestClient) -> None:
    """Create, read, update and delete an entry; an overlap answers 400."""
    day = date.today().isoformat()
    body = {"date": day, "check_in": "09:00:00", "check_out": "12:00:00"}
    created = admin.post(f"{BASE}/entries", json=body)
    assert created.status_code == 200, created.text
    entry_id = created.json()["id"]

    overlap = admin.post(
        f"{BASE}/entries",
        json={"date": day, "check_in": "11:00:00", "check_out": "13:00:00"},
    )
    assert overlap.status_code == 400

    changed = admin.put(f"{BASE}/entries/{entry_id}", json={"notes": "edited"})
    assert changed.status_code == 200, changed.text
    assert admin.get(f"{BASE}/entries/{entry_id}").json()["notes"] == "edited"

    assert admin.delete(f"{BASE}/entries/{entry_id}").status_code == 204
    assert admin.get(f"{BASE}/entries/{entry_id}").status_code == 404


def test_leave_balance_read_and_edit(admin: TestClient) -> None:
    """A fresh balance has 25 days; an edit is read back."""
    year = date.today().year
    first = admin.get(f"{BASE}/leave-balance", params={"year": year})
    assert first.status_code == 200, first.text
    assert first.json()["vacation_entitled"] == 25.0
    assert first.json()["vacation_remaining"] == 25.0

    edited = admin.put(
        f"{BASE}/leave-balance",
        params={"year": year},
        json={"vacation_entitled": 30.0, "vacation_carryover": 2.0},
    )
    assert edited.status_code == 200, edited.text
    again = admin.get(f"{BASE}/leave-balance", params={"year": year}).json()
    assert again["vacation_entitled"] == 30.0
    assert again["vacation_carryover"] == 2.0
    assert again["vacation_remaining"] == 32.0


def _working_day_after_today() -> date:
    """Return a weekday, non-holiday date in a later month of this year."""
    holidays = AustrianComplianceValidator().get_public_holidays(date.today().year)
    day = date(date.today().year, date.today().month, 1)
    day = date(day.year + (day.month == 12), day.month % 12 + 1, 12)
    while day.weekday() >= 5 or day in holidays:
        day += timedelta(days=1)
    return day


@pytest.mark.skipif(date.today().month == 12, reason="needs a later month this year")
def test_vacation_entry_reduces_planned_balance(admin: TestClient) -> None:
    """A future vacation day shows as planned in the balance."""
    future = _working_day_after_today()
    created = admin.post(
        f"{BASE}/entries", json={"date": future.isoformat(), "entry_type": "vacation"}
    )
    assert created.status_code == 200, created.text
    balance = admin.get(f"{BASE}/leave-balance", params={"year": future.year}).json()
    assert balance["vacation_planned"] == 1.0
    assert balance["vacation_remaining"] == 24.0


def test_company_settings_flow(admin: TestClient, company: Company) -> None:
    """Settings are absent, created once, then updated and read back."""
    url = f"{BASE}/settings/company/{company.id}"
    assert admin.get(url).json() is None

    created = admin.post(url, json={"vacation_days_per_year": 27.0})
    assert created.status_code == 200, created.text
    assert created.json()["vacation_days_per_year"] == 27.0
    assert created.json()["lock_period_days"] == 7
    assert admin.post(url, json={}).status_code == 400

    updated = admin.put(url, json={"lock_period_days": 21})
    assert updated.status_code == 200, updated.text
    read = admin.get(url).json()
    assert read["lock_period_days"] == 21
    assert read["vacation_days_per_year"] == 27.0


def test_planned_vacation_counts_in_a_later_year(admin: TestClient) -> None:
    """A vacation day in March of next year reduces next year's balance only."""
    year = date.today().year + 1
    holidays = AustrianComplianceValidator().get_public_holidays(year)
    day = date(year, 3, 1)
    while day.weekday() >= 5 or day in holidays:
        day += timedelta(days=1)
    created = admin.post(
        f"{BASE}/entries", json={"date": day.isoformat(), "entry_type": "vacation"}
    )
    assert created.status_code == 200, created.text
    later = admin.get(f"{BASE}/leave-balance", params={"year": year}).json()
    assert later["vacation_planned"] == 1.0
    assert later["vacation_remaining"] == 24.0
    current = admin.get(
        f"{BASE}/leave-balance", params={"year": date.today().year}
    ).json()
    assert current["vacation_planned"] == 0.0


def test_holidays_with_unknown_region_is_422(admin: TestClient) -> None:
    """An invalid region is a client error, not a server error."""
    response = admin.get(f"{BASE}/holidays", params={"year": 2025, "region": "ZZZ"})
    assert response.status_code == 422, response.text
    assert admin.get(f"{BASE}/holidays", params={"year": 2025}).status_code == 200
