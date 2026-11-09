# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Time-tracking API fixtures.

The database and the ``db_session``/``client`` fixtures live in the repository
root ``conftest.py``; this file only mounts the plugin router on that client.
"""

import importlib
from collections.abc import Generator
from pathlib import Path
from types import ModuleType

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.main import plugin_router_manager
from src.models.base import Base
from src.plugins.manifest import parse_manifest
from src.services import rbac_service
from src.services.rbac_seed_service import seed_rbac_data

PLUGIN_ID = "time-tracking"
PLUGIN_DIR = Path(__file__).resolve().parents[1]

ROUTES_MODULE = "plugins.time-tracking.backend.routes"


def load_routes() -> ModuleType:
    """Import the plugin routes under the name the plugin loader uses.

    The package path contains a hyphen (``time-tracking``), so a plain import
    statement cannot name it. The module is imported by string under the same
    name the plugin loader uses, which also registers the plugin models in the
    shared metadata.
    """
    return importlib.import_module(ROUTES_MODULE)


@pytest.fixture
def tt_client(client: TestClient, db_session: Session) -> Generator[TestClient]:
    """Return the root client with the time-tracking routes mounted.

    The routes answer under ``/api/v1/plugin/time-tracking``. The plugin
    tables are created next to the core tables, which the root ``db_session``
    drops again afterwards. Core RBAC data and the plugin's provided
    permissions are registered as a plugin install does, so Global Admin and
    Member hold the plugin codes.
    """
    routes = load_routes()
    Base.metadata.create_all(bind=db_session.get_bind())
    seed_rbac_data(db_session)
    manifest = parse_manifest(PLUGIN_DIR / "plugin.manifest.json")
    rbac_service.register_plugin_permissions(
        db_session, PLUGIN_ID, manifest.provided_permissions
    )
    plugin_router_manager.add_plugin_router(PLUGIN_ID, routes.router, client.app)
    try:
        yield client
    finally:
        plugin_router_manager.remove_plugin_router(PLUGIN_ID)
