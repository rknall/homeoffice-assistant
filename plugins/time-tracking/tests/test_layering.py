# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Time-tracking layering: services own the logic, the manifest owns metadata."""

import importlib
import json
from collections.abc import Generator
from datetime import date, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models import User
from src.rbac.roles import GLOBAL_ADMIN_ROLE
from src.security import get_password_hash
from src.services import rbac_service

services = importlib.import_module("plugins.time-tracking.backend.services")
models = importlib.import_module("plugins.time-tracking.backend.models")
schemas = importlib.import_module("plugins.time-tracking.backend.schemas")
plugin_module = importlib.import_module("plugins.time-tracking.backend.plugin")

BASE = "/api/v1/plugin/time-tracking"
LOGIN = "layering-login-secret-123"


@pytest.fixture
def admin(tt_client: TestClient, db_session: Session) -> Generator[TestClient]:
    """Return a client logged in as a Global Admin."""
    user = User(
        username="layeradmin",
        email="layeradmin@example.com",
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
        "/api/v1/auth/login", json={"username": "layeradmin", "password": LOGIN}
    )
    assert response.status_code == 200, response.text
    yield http
    http.close()


def _manifest() -> dict:
    return json.loads(services.MANIFEST_PATH.read_text(encoding="utf-8"))


def test_enums_are_defined_once() -> None:
    """The schemas re-use the model enums instead of redefining them."""
    assert schemas.EntryType is models.EntryType
    assert schemas.WorkLocation is models.WorkLocation


def test_config_schema_comes_from_the_manifest() -> None:
    """get_config_schema returns the manifest schema; no unused setting."""
    schema = plugin_module.TimeTrackingPlugin.get_config_schema()
    assert schema == _manifest()["config_schema"]
    assert "enable_project_allocation" not in schema["properties"]


def test_plugin_registers_no_log_only_event_handlers() -> None:
    """Login and logout hooks that only logged are gone."""
    assert "get_event_handlers" not in vars(plugin_module.TimeTrackingPlugin)


def test_info_reports_manifest_version(admin: TestClient) -> None:
    """The /info version is the manifest version, not a literal."""
    response = admin.get(f"{BASE}/info")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["version"] == _manifest()["version"]
    assert body["plugin_name"] == _manifest()["name"]


def test_config_defaults_and_overrides() -> None:
    """Missing settings give the built-in values; stored ones override."""
    assert services.TimeTrackingConfig.from_settings({}) == (
        services.TimeTrackingConfig(8.0, 30, "AT")
    )
    config = services.TimeTrackingConfig.from_settings(
        {"default_work_hours": 7.5, "default_break_minutes": 45}
    )
    assert (config.default_work_hours, config.default_break_minutes) == (7.5, 45)


def test_unsupported_country_falls_back_to_default() -> None:
    """A country without a validator cannot break holiday lookups."""
    config = services.TimeTrackingConfig.from_settings({"default_country": "ZZ"})
    assert config.default_country == "AT"
    assert date(2024, 12, 25) in config.holiday_dates(2024)


def test_break_minutes_use_configured_break() -> None:
    """The configured break applies above six hours only."""
    assert services.calculate_break_minutes(7.0, 45) == 45
    assert services.calculate_break_minutes(6.0, 45) == 0
    assert services.calculate_break_minutes(7.0) == 30


def test_monthly_report_expected_hours_follow_config(
    admin: TestClient, db_session: Session
) -> None:
    """Overtime is measured against the configured daily work hours."""
    user = db_session.query(User).filter(User.username == "layeradmin").one()
    entries = services.TimeEntryService(db_session)
    # 2024-01-10 is a Wednesday: eight gross hours, 30 min break -> 7.5 net
    entries.create_entry(
        user.id,
        date(2024, 1, 10),
        models.EntryType.WORK.value,
        check_in=time(8, 0),
        check_out=time(16, 0),
    )
    default = services.ReportService(db_session).monthly_report(user, 2024, 1)
    low = services.ReportService(
        db_session, services.TimeTrackingConfig(default_work_hours=0.0)
    ).monthly_report(user, 2024, 1)
    assert default.total_net_hours == 7.5
    assert default.expected_work_days == low.expected_work_days
    assert default.overtime_hours == 0
    assert low.overtime_hours == 7.5

    response = admin.get(f"{BASE}/reports/monthly?year=2024&month=1")
    assert response.status_code == 200, response.text
    assert response.json()["total_net_hours"] == 7.5
