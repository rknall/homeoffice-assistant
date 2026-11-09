# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for SPA static serving (path traversal) and application startup."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src import main

INDEX_BYTES = b"<html>spa-index</html>"
SECRET_BYTES = b"top-secret-bytes"


@pytest.fixture
def static_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the SPA routes at a temp static dir with a secret next to it."""
    root = tmp_path / "static"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_bytes(INDEX_BYTES)
    (root / "app.js").write_bytes(b"console.log(1)")
    (tmp_path / "secret.txt").write_bytes(SECRET_BYTES)
    monkeypatch.setattr(main, "static_path", root)
    return root


@pytest.mark.parametrize(
    "url",
    [
        "/..%2fsecret.txt",
        "/%2e%2e/secret.txt",
        "/assets/../../secret.txt",
        "/..%2f..%2fsecret.txt",
    ],
)
def test_traversal_returns_index(static_dir: Path, url: str) -> None:
    """Traversal attempts never return the file outside the static dir."""
    client = TestClient(main.app)
    response = client.get(url)
    assert SECRET_BYTES not in response.content
    assert response.content == INDEX_BYTES


def test_existing_static_file_is_served(static_dir: Path) -> None:
    """A real file under the static dir is still served."""
    response = TestClient(main.app).get("/app.js")
    assert response.status_code == 200
    assert response.content == b"console.log(1)"


def test_unknown_path_falls_back_to_index(static_dir: Path) -> None:
    """Client-side routes fall back to index.html."""
    response = TestClient(main.app).get("/some/spa/route")
    assert response.content == INDEX_BYTES


def test_seeding_failure_aborts_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    """A seeding failure re-raises so the app does not start."""

    def boom(db: object) -> None:
        raise RuntimeError("seed failed")

    monkeypatch.setattr(main.rbac_seed_service, "seed_rbac_data", boom)
    with pytest.raises(RuntimeError, match="seed failed"), TestClient(main.app):
        pass


def test_plugin_load_failure_is_logged_and_startup_continues(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A plugin load failure is logged and startup completes."""

    async def boom(self: object, db: object) -> None:
        raise RuntimeError("plugin load failed")

    monkeypatch.setattr(main.rbac_seed_service, "seed_rbac_data", lambda db: None)
    monkeypatch.setattr(
        main.todo_template_service, "seed_default_templates", lambda db: 0
    )
    monkeypatch.setattr(main.PluginRegistry, "load_all_plugins", boom)
    with (
        caplog.at_level("ERROR", logger=main.logger.name),
        TestClient(main.app) as client,
    ):
        assert client.get("/health").status_code == 200
    assert "Plugin loading failed during startup" in caplog.text
