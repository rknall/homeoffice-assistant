# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Shared pytest setup for core and plugin tests.

Every pytest process gets its own temporary SQLite database, so several test
runs can execute in parallel without sharing a file. The environment is set
before anything from ``src`` is imported, because the settings and the engine
are created at import time. A ``DATABASE_URL`` from the caller (CI sets one) is
deliberately overridden.
"""

import os
import secrets
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

os.environ["HOA_TEST_DIR"] = tempfile.mkdtemp(prefix="hoa-test-")
os.environ["SECRET_KEY"] = secrets.token_urlsafe(32)
os.environ["DATABASE_URL"] = "sqlite:///" + os.environ["HOA_TEST_DIR"] + "/hoa.db"

# The imports below must run after the environment is set.
from src.database import SessionLocal, engine, get_db
from src.main import app
from src.models.base import Base

TEST_DIR = Path(os.environ["HOA_TEST_DIR"])


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Drop the per-process test database directory."""
    engine.dispose()
    shutil.rmtree(TEST_DIR, ignore_errors=True)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session]:
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient]:
    """Create a test client with database override."""

    def override_get_db() -> Generator[Session]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
