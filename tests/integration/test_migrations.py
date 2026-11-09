# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for the core Alembic migration chain on SQLite.

Each test migrates its own temporary database file. The URL reaches env.py as
the ``sqlalchemy.url`` config attribute, the way the restore hands it over, so
the application settings are never touched.
"""

import importlib
import uuid
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import Engine, create_engine, func, select, text
from sqlalchemy import table as table_
from sqlalchemy.orm import Session

from alembic import command
from src.models import Base, Expense, SystemSettings, User, UserRole
from src.models.enums import ExpenseStatus
from src.rbac.roles import MEMBER_PERMISSIONS
from src.services.backup_restore import core_alembic_config

DEV6_REVISION = "a9c8e2f4b1d6"
PRE_MEMBER_REVISION = "c61a0e5f8b37"
MEMBER_REVISION = "5b2d9f3e6a18"
PRE_RBAC_REVISION = "5c9d4e8f3a2b"
TIMESTAMP = "2025-06-01 10:00:00"


@pytest.fixture
def db_url(tmp_path: Path) -> str:
    """Return the URL of an empty temporary SQLite database."""
    return f"sqlite:///{tmp_path / 'migrations.db'}"


@pytest.fixture
def alembic_cfg() -> Config:
    """Return an Alembic config for the project's migration scripts."""
    return core_alembic_config()


def run(alembic_cfg: Config, db_url: str, action: str, revision: str) -> None:
    """Run an Alembic upgrade or downgrade against ``db_url``.

    Args:
        alembic_cfg: The Alembic config.
        db_url: Database URL to migrate.
        action: "upgrade" or "downgrade".
        revision: Target revision.
    """
    alembic_cfg.attributes["sqlalchemy.url"] = db_url
    getattr(command, action)(alembic_cfg, revision)


def insert_dev6_data(engine: Engine) -> dict[str, str]:
    """Insert one row per core table the way a v0.5.0-dev6 install holds them.

    Args:
        engine: Engine bound to a database at the dev6 revision.

    Returns:
        The ids of the inserted rows, keyed by kind.
    """
    ids = {key: uuid.uuid4().hex for key in ("user", "company", "event", "pending")}
    ids["included"] = uuid.uuid4().hex
    ids["user_role"] = uuid.uuid4().hex
    common = {"ts": TIMESTAMP}
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, username, email, hashed_password, is_admin,"
                " is_active, created_at, updated_at) VALUES (:id, 'dev6',"
                " 'dev6@example.com', 'x', 1, 1, :ts, :ts)"
            ),
            {"id": ids["user"], **common},
        )
        role_id = conn.execute(
            text("SELECT id FROM roles WHERE name = 'Global Admin'")
        ).scalar_one()
        # Ids starting with a letter all read as 0 under NUMERIC affinity, so a
        # cast of the RBAC ids to a declared UUID type would collide on them.
        for prefix, name in (("a", "Custom A"), ("b", "Custom B")):
            conn.execute(
                text(
                    "INSERT INTO roles (id, name, is_system, created_at,"
                    " updated_at) VALUES (:id, :name, 0, :ts, :ts)"
                ),
                {"id": prefix + uuid.uuid4().hex[1:], "name": name, **common},
            )
        conn.execute(
            text(
                "INSERT INTO user_roles (id, user_id, role_id) "
                "VALUES (:id, :user_id, :role_id)"
            ),
            {"id": ids["user_role"], "user_id": ids["user"], "role_id": role_id},
        )
        conn.execute(
            text(
                "INSERT INTO companies (id, name, type, created_at, updated_at)"
                " VALUES (:id, 'Acme', 'EMPLOYER', :ts, :ts)"
            ),
            {"id": ids["company"], **common},
        )
        conn.execute(
            text(
                "INSERT INTO events (id, user_id, company_id, name, start_date,"
                " end_date, created_at, updated_at) VALUES (:id, :user_id,"
                " :company_id, 'Trip', '2025-06-01', '2025-06-03', :ts, :ts)"
            ),
            {
                "id": ids["event"],
                "user_id": ids["user"],
                "company_id": ids["company"],
                **common,
            },
        )
        for key, status in (("pending", "PENDING"), ("included", "INCLUDED")):
            conn.execute(
                text(
                    "INSERT INTO expenses (id, event_id, date, amount, currency,"
                    " payment_type, category, status, created_at, updated_at)"
                    " VALUES (:id, :event_id, '2025-06-01', 12.50, 'EUR', 'CASH',"
                    " 'TRAVEL', :status, :ts, :ts)"
                ),
                {"id": ids[key], "event_id": ids["event"], "status": status, **common},
            )
        conn.execute(
            text(
                "INSERT INTO system_settings (key, value, is_encrypted)"
                " VALUES ('locale_timezone', 'Europe/Vienna', 0)"
            )
        )
    return ids


def count_rows(engine: Engine, table: str) -> int:
    """Return the number of rows in ``table``."""
    with engine.connect() as conn:
        return conn.execute(
            select(func.count()).select_from(table_(table))
        ).scalar_one()


def test_fresh_upgrade_head_matches_models(alembic_cfg: Config, db_url: str) -> None:
    """A fresh database at head has no drift against the models."""
    run(alembic_cfg, db_url, "upgrade", "head")
    command.check(core_alembic_config(db_url))


def test_check_ignores_loaded_plugin_models(alembic_cfg: Config, db_url: str) -> None:
    """Plugin models in the shared metadata are not core drift.

    The import name is the one the plugin loader uses, so the models are
    registered once per process whichever test imports them first.
    """
    importlib.import_module("plugins.time-tracking.backend.models")
    assert any(name.startswith("tt_") for name in Base.metadata.tables)
    run(alembic_cfg, db_url, "upgrade", "head")
    command.check(core_alembic_config(db_url))


def test_upgrade_from_dev6_keeps_data(alembic_cfg: Config, db_url: str) -> None:
    """A dev6 database with data upgrades to head and round trips back."""
    run(alembic_cfg, db_url, "upgrade", DEV6_REVISION)
    engine = create_engine(db_url)
    ids = insert_dev6_data(engine)
    tables = ("users", "roles", "user_roles", "companies", "events", "expenses")
    before = {table: count_rows(engine, table) for table in tables}
    settings_before = count_rows(engine, "system_settings")

    run(alembic_cfg, db_url, "upgrade", "head")

    # The Member role is the only row the chain adds; the dev6 user already
    # holds a role, so it gets no Member assignment.
    after = {**before, "roles": before["roles"] + 1}
    assert {table: count_rows(engine, table) for table in tables} == after
    assert count_rows(engine, "system_settings") == settings_before
    with Session(engine) as session:
        included = session.get(Expense, uuid.UUID(ids["included"]))
        pending = session.get(Expense, uuid.UUID(ids["pending"]))
        assert included is not None and pending is not None
        assert included.status == ExpenseStatus.SUBMITTED
        assert included.submitted_at is not None
        assert pending.status == ExpenseStatus.PENDING
        user = session.get(User, uuid.UUID(ids["user"]))
        assert user is not None and user.username == "dev6"
        assert session.get(UserRole, uuid.UUID(ids["user_role"])) is not None
        timezone = session.get(SystemSettings, "locale_timezone")
        assert timezone is not None and timezone.value == "Europe/Vienna"

    run(alembic_cfg, db_url, "downgrade", DEV6_REVISION)
    assert {table: count_rows(engine, table) for table in tables} == before
    run(alembic_cfg, db_url, "upgrade", "head")
    assert {table: count_rows(engine, table) for table in tables} == after
    engine.dispose()


def test_upgrade_pre_rbac_database_with_admin(alembic_cfg: Config, db_url: str) -> None:
    """A pre-RBAC admin is migrated to a Global Admin role assignment."""
    run(alembic_cfg, db_url, "upgrade", PRE_RBAC_REVISION)
    engine = create_engine(db_url)
    user_id = uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, username, email, hashed_password, role,"
                " is_admin, is_active, created_at, updated_at) VALUES (:id,"
                " 'admin', 'admin@example.com', 'x', 'ADMIN', 1, 1, :ts, :ts)"
            ),
            {"id": user_id, "ts": TIMESTAMP},
        )

    run(alembic_cfg, db_url, "upgrade", "head")

    with engine.connect() as conn:
        role_names = (
            conn.execute(
                text(
                    "SELECT roles.name FROM user_roles JOIN roles"
                    " ON roles.id = user_roles.role_id"
                    " WHERE user_roles.user_id = :user_id"
                ),
                {"user_id": user_id},
            )
            .scalars()
            .all()
        )
    engine.dispose()
    assert role_names == ["Global Admin"]


def test_downgrade_base_and_upgrade_head(alembic_cfg: Config, db_url: str) -> None:
    """Every revision downgrades and upgrades again on SQLite."""
    run(alembic_cfg, db_url, "upgrade", "head")
    run(alembic_cfg, db_url, "downgrade", "base")
    run(alembic_cfg, db_url, "upgrade", "head")
    command.check(core_alembic_config(db_url))


def member_codes(engine: Engine) -> set[str]:
    """Return the permission codes linked to the Member role."""
    with engine.connect() as conn:
        return set(
            conn.execute(
                text(
                    "SELECT role_permissions.permission_code FROM role_permissions"
                    " JOIN roles ON roles.id = role_permissions.role_id"
                    " WHERE roles.name = 'Member'"
                )
            ).scalars()
        )


def test_member_role_migration(alembic_cfg: Config, db_url: str) -> None:
    """Member gets the core and existing plugin codes and role-less users."""
    run(alembic_cfg, db_url, "upgrade", PRE_MEMBER_REVISION)
    engine = create_engine(db_url)
    user_id = uuid.uuid4().hex
    tt_codes = {
        "time-tracking.records.read",
        "time-tracking.reports.read",
        "time-tracking.settings.write",
    }
    with engine.begin() as conn:
        for code in sorted(tt_codes):
            conn.execute(
                text(
                    "INSERT INTO permissions (code, module, plugin_id)"
                    " VALUES (:code, 'time-tracking', 'time-tracking')"
                ),
                {"code": code},
            )
        conn.execute(
            text(
                "INSERT INTO users (id, username, email, hashed_password, is_admin,"
                " is_active, created_at, updated_at) VALUES (:id, 'plain',"
                " 'plain@example.com', 'x', 0, 1, :ts, :ts)"
            ),
            {"id": user_id, "ts": TIMESTAMP},
        )

    run(alembic_cfg, db_url, "upgrade", MEMBER_REVISION)

    assert member_codes(engine) == set(MEMBER_PERMISSIONS) | tt_codes
    with engine.connect() as conn:
        example_rows = conn.execute(
            text("SELECT count(*) FROM permissions WHERE code LIKE 'example.%'")
        ).scalar_one()
        assignments = conn.execute(
            text(
                "SELECT roles.name, user_roles.company_id FROM user_roles"
                " JOIN roles ON roles.id = user_roles.role_id"
                " WHERE user_roles.user_id = :user_id"
            ),
            {"user_id": user_id},
        ).all()
    assert example_rows == 0
    assert [tuple(row) for row in assignments] == [("Member", None)]

    run(alembic_cfg, db_url, "downgrade", PRE_MEMBER_REVISION)

    assert member_codes(engine) == set()
    with engine.connect() as conn:
        member_roles = conn.execute(
            text("SELECT count(*) FROM roles WHERE name = 'Member'")
        ).scalar_one()
        links = count_rows(engine, "role_permissions")
    assert member_roles == 0
    assert count_rows(engine, "user_roles") == 0
    # Only the links seeded with the RBAC tables remain: Global Admin (16 core
    # codes), Company Admin (7) and Company Viewer (3).
    assert links == 16 + 7 + 3
    engine.dispose()


def test_drop_is_admin_migration(alembic_cfg: Config, db_url: str) -> None:
    """is_admin is dropped and on downgrade rebuilt from Global Admin."""
    run(alembic_cfg, db_url, "upgrade", MEMBER_REVISION)
    engine = create_engine(db_url)
    admin_id, member_id = uuid.uuid4().hex, uuid.uuid4().hex
    with engine.begin() as conn:
        for user_id, name in ((admin_id, "boss"), (member_id, "plain")):
            conn.execute(
                text(
                    "INSERT INTO users (id, username, email, hashed_password,"
                    " is_admin, is_active, created_at, updated_at) VALUES (:id,"
                    " :name, :name || '@example.com', 'x', 0, 1, :ts, :ts)"
                ),
                {"id": user_id, "name": name, "ts": TIMESTAMP},
            )
        for user_id, role in ((admin_id, "Global Admin"), (member_id, "Member")):
            conn.execute(
                text(
                    "INSERT INTO user_roles (id, user_id, role_id) SELECT :id,"
                    " :user_id, id FROM roles WHERE name = :role"
                ),
                {"id": uuid.uuid4().hex, "user_id": user_id, "role": role},
            )

    run(alembic_cfg, db_url, "upgrade", "head")

    with engine.connect() as conn:
        columns = {row[1] for row in conn.execute(text("PRAGMA table_info(users)"))}
        assert count_rows(engine, "users") == 2
    assert "is_admin" not in columns

    run(alembic_cfg, db_url, "downgrade", MEMBER_REVISION)

    with engine.connect() as conn:
        flags = dict(conn.execute(text("SELECT username, is_admin FROM users")).all())
    engine.dispose()
    assert flags == {"boss": 1, "plain": 0}
