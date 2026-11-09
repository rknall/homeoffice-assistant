# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for the single-source application version."""

import json
import tomllib
from pathlib import Path

from fastapi.testclient import TestClient

from src.version import APP_VERSION

ROOT = Path(__file__).resolve().parents[2]


def test_app_version_matches_pyproject() -> None:
    """APP_VERSION is the written pyproject.toml project.version."""
    with (ROOT / "pyproject.toml").open("rb") as fh:
        pyproject_version = tomllib.load(fh)["project"]["version"]
    assert pyproject_version == APP_VERSION


def test_frontend_version_mirrors_backend() -> None:
    """package.json version equals pyproject version, compared as written."""
    package = json.loads((ROOT / "frontend" / "package.json").read_text())
    assert package["version"] == APP_VERSION


def test_health_returns_version(client: TestClient) -> None:
    """/health reports the application version."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["version"] == APP_VERSION
