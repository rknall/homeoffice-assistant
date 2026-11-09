"""Tests for the UX seed script."""

import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.services import file_storage_service

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "seed_ux_data.py"


def _load_seed():
    spec = importlib.util.spec_from_file_location("seed_ux_data", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_seed_on_empty_db_leaves_viewer_with_single_scoped_role(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The seed uploads Beta's logo; keep it out of the real data/logos.
    monkeypatch.setattr(file_storage_service, "LOGO_DIR", tmp_path)
    credentials = _load_seed().seed(client)
    assert set(credentials) == {"ux_admin", "ux_member", "ux_viewer"}

    users = {u["username"]: u for u in client.get("/api/v1/users").json()}
    viewer_id = users["ux_viewer"]["id"]
    companies = {c["name"]: c for c in client.get("/api/v1/companies").json()}
    assert companies["Beta"]["logo_path"]
    assert (tmp_path / companies["Beta"]["logo_path"]).is_file()

    assignments = client.get(f"/api/v1/rbac/users/{viewer_id}/roles").json()
    assert len(assignments) == 1
    assert assignments[0]["role"]["name"] == "Company Viewer"
    assert assignments[0]["company_id"] == companies["Alpha"]["id"]

    member_id = users["ux_member"]["id"]
    member_roles = client.get(f"/api/v1/rbac/users/{member_id}/roles").json()
    assert [(a["role"]["name"], a["company_id"]) for a in member_roles] == [
        ("Member", None)
    ]

    calendars = client.get("/api/v1/holiday-calendars").json()
    assert [c["country_code"] for c in calendars] == ["AT"]
