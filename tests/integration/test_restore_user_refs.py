# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for re-pointing user references when a restore keeps the admin.

The tests run on the service level against copies of a migrated database. The
plugin-like tables are raw SQL, never part of ``Base.metadata``, so the result
does not depend on which models the test process imported. User ids contain
letters, so a NUMERIC column never converts the stored hex text.
"""

import shutil
import sqlite3
import uuid
from pathlib import Path

import pytest
from sqlalchemy import column, create_engine, select, table
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from src.models import Role, User, UserRole
from src.plugins.migrations import PluginMigrationRunner
from src.rbac.roles import GLOBAL_ADMIN_ROLE, MEMBER_ROLE
from src.services import backup_restore, restore_user_refs

ADMIN = "a" * 32
USER_B = "b" * 32
USER_C = "c" * 32
PROJECT_ROOT = Path(__file__).resolve().parents[2]

PLUGIN_DDL = """
CREATE TABLE xp_items (
    id INTEGER PRIMARY KEY,
    user_id NUMERIC NOT NULL REFERENCES users(id)
);
CREATE TABLE xp_prefs (
    id INTEGER PRIMARY KEY,
    user_id CHAR(32) NOT NULL UNIQUE REFERENCES users(id),
    value TEXT
);
CREATE TABLE xp_balances (
    id INTEGER PRIMARY KEY,
    user_id NUMERIC REFERENCES users(id),
    company_id CHAR(32) NULL,
    year INT,
    value TEXT,
    UNIQUE(user_id, company_id, year)
);
CREATE TABLE xp_tags (
    user_id NUMERIC REFERENCES users(id),
    tag TEXT,
    PRIMARY KEY(user_id, tag)
);
CREATE TABLE xp_flags (
    id INTEGER PRIMARY KEY,
    user_id NUMERIC REFERENCES users(id),
    on_ INT
);
CREATE UNIQUE INDEX xp_flags_user ON xp_flags(user_id) WHERE on_ = 1;
"""


def add_user(path: Path, hex_id: str, username: str) -> None:
    """Insert a user with a fixed id, like the ORM stores it."""
    engine = create_engine(f"sqlite:///{path}")
    with engine.begin() as conn:
        conn.execute(
            User.__table__.insert().values(
                id=uuid.UUID(hex_id),
                username=username,
                email=f"{username}@example.com",
                hashed_password="x",
            )
        )
    engine.dispose()


def add_user_role(path: Path, hex_id: str, role_name: str) -> None:
    """Assign a seeded role globally to a user."""
    engine = create_engine(f"sqlite:///{path}")
    with engine.begin() as conn:
        role_id = conn.scalar(select(Role.id).where(Role.name == role_name))
        conn.execute(
            UserRole.__table__.insert().values(
                user_id=uuid.UUID(hex_id), role_id=role_id
            )
        )
    engine.dispose()


def run(path: Path, sql: str, *params: object) -> None:
    """Run one raw statement and commit."""
    with sqlite3.connect(path) as conn:
        conn.execute(sql, params)


def rows(path: Path, sql: str) -> list[tuple]:
    """Return the rows of a raw query."""
    with sqlite3.connect(path) as conn:
        return conn.execute(sql).fetchall()


def insert_row(path: Path, name: str, **values: object) -> None:
    """Insert a row, filling the other required columns from the table schema."""
    with sqlite3.connect(path) as conn:
        info = conn.execute(f"PRAGMA table_info({name})").fetchall()
        row = dict(values)
        for _, col, col_type, notnull, default, pk in info:
            if col in row or default is not None or not (notnull or pk):
                continue
            kind = col_type.upper()
            if "INT" in kind or "NUM" in kind or "FLOAT" in kind or "BOOL" in kind:
                row[col] = 0
            elif kind == "DATE":
                row[col] = "2026-01-01"
            elif "DATETIME" in kind or "TIMESTAMP" in kind:
                row[col] = "2026-01-01 00:00:00"
            elif kind == "TIME":
                row[col] = "00:00:00"
            elif pk:
                row[col] = uuid.uuid4().hex
            else:
                row[col] = "x"
    engine = create_engine(f"sqlite:///{path}")
    with engine.begin() as conn:
        target = table(name, *(column(key) for key in row))
        conn.execute(target.insert().values(row))
    engine.dispose()


def owners(path: Path, name: str) -> list[tuple]:
    """Return the user_id of every row of a table."""
    engine = create_engine(f"sqlite:///{path}")
    with engine.connect() as conn:
        found = conn.execute(select(column("user_id")).select_from(table(name))).all()
    engine.dispose()
    return [tuple(row) for row in found]


@pytest.fixture
def live(migrated_db_template: Path, tmp_path: Path) -> Path:
    """The live database: migrated schema holding only the admin."""
    path = tmp_path / "live.db"
    shutil.copy2(migrated_db_template, path)
    add_user(path, ADMIN, "admin")
    return path


@pytest.fixture
def staged(migrated_db_template: Path, tmp_path: Path) -> Path:
    """The restored file: migrated schema, user b and c, plugin-like tables."""
    path = tmp_path / "staged.db"
    shutil.copy2(migrated_db_template, path)
    add_user(path, USER_B, "bee")
    add_user(path, USER_C, "cee")
    with sqlite3.connect(path) as conn:
        conn.executescript(PLUGIN_DDL)
    return path


def restore(live: Path, staged: Path) -> None:
    """Run the admin preservation like the restore does."""
    admin_row = backup_restore.load_admin_row(live, ADMIN)
    assert admin_row is not None
    backup_restore._preserve_admin(staged, admin_row)


def orphans(path: Path) -> dict[str, int]:
    """Orphans of a database file according to the production guard."""
    engine = create_engine(f"sqlite:///{path}")
    try:
        with Session(engine) as db:
            return restore_user_refs.find_user_orphans(db)
    finally:
        engine.dispose()


def test_plugin_rows_taken_over(live: Path, staged: Path) -> None:
    """Rows of a removed user in unloaded plugin tables go to the admin."""
    run(staged, "INSERT INTO xp_items (user_id) VALUES (?)", USER_B)
    run(staged, "INSERT INTO xp_prefs (user_id, value) VALUES (?, 'p')", USER_B)
    run(
        staged,
        "INSERT INTO xp_balances (user_id, company_id, year, value) "
        "VALUES (?, NULL, 2026, 'v')",
        USER_B,
    )
    run(staged, "INSERT INTO xp_tags (user_id, tag) VALUES (?, 'x')", USER_B)

    restore(live, staged)

    for table_name in ("xp_items", "xp_prefs", "xp_balances", "xp_tags"):
        assert owners(staged, table_name) == [(ADMIN,)], table_name
    assert orphans(staged) == {}


def test_conflicting_unique_rows_keep_admin_rows(live: Path, staged: Path) -> None:
    """The admin's own rows win; NULL keys clash; other rows are taken over."""
    add_user(staged, ADMIN, "admin")
    run(staged, "INSERT INTO xp_prefs (user_id, value) VALUES (?, 'admin')", ADMIN)
    run(staged, "INSERT INTO xp_prefs (user_id, value) VALUES (?, 'b')", USER_B)
    balances = (
        "INSERT INTO xp_balances (user_id, company_id, year, value) "
        "VALUES (?, ?, 2026, ?)"
    )
    run(staged, balances, ADMIN, None, "admin")
    run(staged, balances, USER_B, None, "b-null")
    run(staged, balances, USER_B, "c1", "b-c1")
    tags = "INSERT INTO xp_tags (user_id, tag) VALUES (?, ?)"
    run(staged, tags, ADMIN, "x")
    run(staged, tags, USER_B, "x")
    run(staged, tags, USER_B, "y")

    restore(live, staged)

    assert rows(staged, "SELECT user_id, value FROM xp_prefs") == [(ADMIN, "admin")]
    assert rows(
        staged, "SELECT user_id, company_id, value FROM xp_balances ORDER BY value"
    ) == [(ADMIN, None, "admin"), (ADMIN, "c1", "b-c1")]
    assert rows(staged, "SELECT user_id, tag FROM xp_tags ORDER BY tag") == [
        (ADMIN, "x"),
        (ADMIN, "y"),
    ]
    assert orphans(staged) == {}


def test_lowest_rowid_wins_between_users(live: Path, staged: Path) -> None:
    """Two removed users with the same key: the first row survives."""
    balances = (
        "INSERT INTO xp_balances (id, user_id, company_id, year, value) "
        "VALUES (?, ?, 'c2', 2025, ?)"
    )
    run(staged, balances, 1, USER_B, "b")
    run(staged, balances, 2, USER_C, "c")

    restore(live, staged)

    assert rows(staged, "SELECT id, user_id, value FROM xp_balances") == [
        (1, ADMIN, "b")
    ]


def test_role_assignments_of_other_users_deleted(live: Path, staged: Path) -> None:
    """Roles of removed users are not taken over; the admin keeps its own."""
    add_user(staged, ADMIN, "admin")
    add_user_role(staged, ADMIN, MEMBER_ROLE)
    add_user_role(staged, USER_B, MEMBER_ROLE)

    restore(live, staged)

    assert {row[0] for row in rows(staged, "SELECT user_id FROM user_roles")} == {ADMIN}
    engine = create_engine(f"sqlite:///{staged}")
    with Session(engine) as db:
        names = db.scalars(
            select(Role.name).join(UserRole, UserRole.role_id == Role.id)
        ).all()
    engine.dispose()
    assert sorted(names) == sorted([MEMBER_ROLE, GLOBAL_ADMIN_ROLE])


def test_time_tracking_schema_without_loaded_plugin(live: Path, staged: Path) -> None:
    """The real time-tracking tables are found through the file, not models."""
    runner = PluginMigrationRunner(
        PROJECT_ROOT / "plugins" / "time-tracking", "time-tracking"
    )
    cfg = runner.get_alembic_config()
    engine = create_engine(f"sqlite:///{staged}")
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")
    engine.dispose()
    tables = ("tt_time_entries", "tt_leave_balances", "tt_user_preferences")
    for table_name in tables:
        insert_row(staged, table_name, user_id=USER_B)

    restore(live, staged)

    for table_name in tables:
        assert owners(staged, table_name) == [(ADMIN,)], table_name
    assert orphans(staged) == {}


def test_partial_unique_conflict_fails_loud(live: Path, staged: Path) -> None:
    """A clash on a partial unique index aborts without committing."""
    add_user(staged, ADMIN, "admin")
    flags = "INSERT INTO xp_flags (user_id, on_) VALUES (?, 1)"
    run(staged, flags, ADMIN)
    run(staged, flags, USER_B)

    with pytest.raises(IntegrityError):
        restore(live, staged)

    assert (USER_B,) in rows(staged, "SELECT user_id FROM xp_flags")
    assert (USER_B,) in rows(staged, "SELECT id FROM users")
