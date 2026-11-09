# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for plugin migration management."""

import json
import shutil
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from alembic import command
from src.database import engine
from src.models.plugin_config import PluginConfigModel, PluginMigrationHistory
from src.plugins import migrations as migrations_module
from src.plugins.base import PluginCapability, PluginManifest
from src.plugins.loader import PluginLoader
from src.plugins.manifest import PLUGIN_MANIFEST_FILE
from src.plugins.migrations import PluginMigrationRunner
from src.plugins.registry import PluginRegistry

BUNDLED_ENV = (
    Path(__file__).parents[3] / "plugins/time-tracking/backend/migrations/env.py"
)
FIXTURE_ID = "fixture-mig"
FIXTURE_TABLE = "fx_items"
FIXTURE_VERSION_TABLE = f"alembic_version_{FIXTURE_ID}"

REVISION_TEMPLATE = """
import sqlalchemy as sa
from alembic import op

revision = {revision!r}
down_revision = {down!r}
branch_labels = None
depends_on = None


def upgrade():
{upgrade}


def downgrade():
{downgrade}
"""


class TestGetTablePrefix:
    """Tests for _get_table_prefix method."""

    @pytest.fixture
    def plugin_path(self, tmp_path: Path) -> Path:
        """Create a temporary plugin directory."""
        return tmp_path / "test-plugin"

    def test_uses_manifest_table_prefix_when_available(self, plugin_path: Path):
        """Test that manifest table_prefix takes priority over derivation."""
        manifest = PluginManifest(
            id="time-tracking",
            name="Time Tracking",
            version="1.0.0",
            description="Test",
            capabilities={PluginCapability.BACKEND},
            table_prefix="tt_",
        )

        runner = PluginMigrationRunner(plugin_path, "time-tracking", manifest)

        # Should use manifest value, not derived "tt_" (which happens to match)
        assert runner._get_table_prefix() == "tt_"

    def test_uses_manifest_prefix_over_derived(self, plugin_path: Path):
        """Test manifest prefix is used even when different from derived."""
        # For "example" plugin, derivation would produce "example_"
        # but manifest specifies "plugin_example_"
        manifest = PluginManifest(
            id="example",
            name="Example Plugin",
            version="1.0.0",
            description="Test",
            capabilities={PluginCapability.BACKEND},
            table_prefix="plugin_example_",
        )

        runner = PluginMigrationRunner(plugin_path, "example", manifest)

        # Should use manifest value, not derived "example_"
        assert runner._get_table_prefix() == "plugin_example_"

    def test_derives_prefix_when_manifest_missing(self, plugin_path: Path):
        """Test fallback to derivation when no manifest provided."""
        runner = PluginMigrationRunner(plugin_path, "time-tracking", manifest=None)

        # "time-tracking" -> "tt_" (initials of hyphenated words)
        assert runner._get_table_prefix() == "tt_"

    def test_derives_prefix_when_table_prefix_not_set(self, plugin_path: Path):
        """Test fallback to derivation when manifest has no table_prefix."""
        manifest = PluginManifest(
            id="my-cool-plugin",
            name="My Cool Plugin",
            version="1.0.0",
            description="Test",
            capabilities={PluginCapability.BACKEND},
            # table_prefix not set, defaults to None
        )

        runner = PluginMigrationRunner(plugin_path, "my-cool-plugin", manifest)

        # "my-cool-plugin" -> "mcp_" (initials)
        assert runner._get_table_prefix() == "mcp_"

    def test_derives_single_word_prefix(self, plugin_path: Path):
        """Test derivation for single-word plugin IDs."""
        runner = PluginMigrationRunner(plugin_path, "analytics", manifest=None)

        # Single word uses full name as prefix
        assert runner._get_table_prefix() == "analytics_"

    def test_derives_underscore_separated_prefix(self, plugin_path: Path):
        """Test derivation treats underscores like hyphens."""
        runner = PluginMigrationRunner(plugin_path, "data_export", manifest=None)

        # "data_export" -> "de_" (underscores converted to hyphens, then initials)
        assert runner._get_table_prefix() == "de_"


def _write_revision(
    versions: Path, revision: str, down: str | None, upgrade: str, downgrade: str
) -> None:
    """Write one Alembic revision file for the fixture plugin."""
    (versions / f"{revision}.py").write_text(
        REVISION_TEMPLATE.format(
            revision=revision, down=down, upgrade=upgrade, downgrade=downgrade
        )
    )


def _drop_fixture_tables() -> None:
    """Remove every table the fixture plugin may have created."""
    with engine.connect() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {FIXTURE_TABLE}"))
        conn.execute(text(f'DROP TABLE IF EXISTS "{FIXTURE_VERSION_TABLE}"'))
        conn.commit()


@pytest.fixture
def fixture_plugin(tmp_path: Path, db_session: Session) -> Generator[Path]:
    """A plugin on disk with two migrations, using a bundled plugin's env.py.

    Revision fx_r1 creates fx_items, fx_r2 adds a column. The table and the
    version table are dropped afterwards, because they are not part of the
    core metadata the db_session fixture drops.
    """
    plugins_dir = tmp_path / "plugins"
    plugin_dir = plugins_dir / FIXTURE_ID
    versions = plugin_dir / "backend" / "migrations" / "versions"
    versions.mkdir(parents=True)
    shutil.copy(BUNDLED_ENV, versions.parent / "env.py")
    (plugin_dir / PLUGIN_MANIFEST_FILE).write_text(
        json.dumps(
            {
                "id": FIXTURE_ID,
                "name": "Fixture",
                "version": "2.0.0",
                "description": "Migration fixture",
                "table_prefix": "fx_",
            }
        )
    )
    _write_revision(
        versions,
        "fx_r1",
        None,
        f"    op.create_table('{FIXTURE_TABLE}', "
        "sa.Column('id', sa.Integer, primary_key=True))",
        f"    op.drop_table('{FIXTURE_TABLE}')",
    )
    _write_revision(
        versions,
        "fx_r2",
        "fx_r1",
        f"    op.add_column('{FIXTURE_TABLE}', sa.Column('name', sa.String(50)))",
        f"    op.drop_column('{FIXTURE_TABLE}', 'name')",
    )
    _drop_fixture_tables()
    yield plugin_dir
    _drop_fixture_tables()


def _manifest(prefix: str = "fx_") -> PluginManifest:
    return PluginManifest(
        id=FIXTURE_ID,
        name="Fixture",
        version="2.0.0",
        description="Migration fixture",
        table_prefix=prefix,
    )


def _history(db: Session) -> list[str]:
    db.expire_all()
    rows = (
        db.query(PluginMigrationHistory)
        .filter(PluginMigrationHistory.plugin_id == FIXTURE_ID)
        .all()
    )
    return sorted(row.revision for row in rows)


def _registry_for(plugin_dir: Path) -> PluginRegistry:
    registry = PluginRegistry()
    registry._loader = PluginLoader(plugin_dir.parent)
    return registry


class TestAlembicConfig:
    """The database URL bypasses ConfigParser interpolation."""

    def test_percent_in_database_url(self, tmp_path: Path, monkeypatch):
        """A URL-encoded password with % does not raise and is passed as is."""
        url = "postgresql://hoa:p%40ss%25word@db:5432/hoa"
        monkeypatch.setattr(migrations_module.settings, "database_url", url)

        cfg = PluginMigrationRunner(tmp_path, "p").get_alembic_config()

        assert cfg.attributes["sqlalchemy.url"] == url
        assert cfg.get_main_option("version_table") == "alembic_version_p"


class TestRunMigrations:
    """Applying plugin migrations on the application engine."""

    def test_fresh_run_records_each_revision(self, fixture_plugin, db_session):
        """Every applied revision is recorded, not only the head."""
        runner = PluginMigrationRunner(fixture_plugin, FIXTURE_ID, _manifest())

        assert runner.run_migrations() == ["fx_r1", "fx_r2"]

        assert runner.get_current_revision() == "fx_r2"
        columns = {c["name"] for c in inspect(engine).get_columns(FIXTURE_TABLE)}
        assert columns == {"id", "name"}
        assert _history(db_session) == ["fx_r1", "fx_r2"]
        assert runner.run_migrations() == []

    @pytest.mark.asyncio
    async def test_startup_applies_upgraded_plugin_migration(
        self, fixture_plugin, db_session
    ):
        """A plugin left at an older revision reaches head before it loads."""
        runner = PluginMigrationRunner(fixture_plugin, FIXTURE_ID, _manifest())
        cfg = runner.get_alembic_config()
        with engine.begin() as conn:
            cfg.attributes["connection"] = conn
            command.upgrade(cfg, "fx_r1")
        db_session.add(PluginConfigModel(plugin_id=FIXTURE_ID, plugin_version="1.0"))
        db_session.commit()

        registry = _registry_for(fixture_plugin)
        load = AsyncMock()
        registry._load_single_plugin = load
        await registry.load_all_plugins(db_session)

        assert runner.get_current_revision() == "fx_r2"
        assert _history(db_session) == ["fx_r2"]
        load.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_failed_migration_skips_plugin(
        self, fixture_plugin, db_session, caplog
    ):
        """A failing migration is logged and that plugin is not loaded."""
        _write_revision(
            fixture_plugin / "backend" / "migrations" / "versions",
            "fx_r3",
            "fx_r2",
            "    raise RuntimeError('broken migration')",
            "    pass",
        )
        db_session.add(PluginConfigModel(plugin_id=FIXTURE_ID, plugin_version="2.0.0"))
        db_session.commit()

        registry = _registry_for(fixture_plugin)
        load = AsyncMock()
        registry._load_single_plugin = load
        await registry.load_all_plugins(db_session)

        load.assert_not_awaited()
        assert f"Migrations failed for plugin {FIXTURE_ID}" in caplog.text
        assert _registry_for(fixture_plugin).run_plugin_migrations(db_session) == [
            FIXTURE_ID
        ]


class TestDowngradeAll:
    """Uninstall downgrades fall back to a table drop only when unsupported."""

    def test_clean_downgrade(self, fixture_plugin, db_session):
        """A full downgrade removes the tables, version table and history."""
        runner = PluginMigrationRunner(fixture_plugin, FIXTURE_ID, _manifest())
        runner.run_migrations()

        runner.downgrade_all()

        tables = inspect(engine).get_table_names()
        assert FIXTURE_TABLE not in tables
        assert FIXTURE_VERSION_TABLE not in tables
        assert _history(db_session) == []

    def test_not_implemented_falls_back_to_force_drop(self, fixture_plugin, db_session):
        """NotImplementedError in downgrade() drops the prefixed tables."""
        _write_revision(
            fixture_plugin / "backend" / "migrations" / "versions",
            "fx_r3",
            "fx_r2",
            "    pass",
            "    raise NotImplementedError('one-way migration')",
        )
        runner = PluginMigrationRunner(fixture_plugin, FIXTURE_ID, _manifest())
        runner.run_migrations()

        runner.downgrade_all()

        assert FIXTURE_TABLE not in inspect(engine).get_table_names()

    def test_other_errors_propagate_without_drop(self, fixture_plugin, db_session):
        """A real downgrade failure is raised and the tables stay."""
        _write_revision(
            fixture_plugin / "backend" / "migrations" / "versions",
            "fx_r3",
            "fx_r2",
            "    pass",
            "    raise RuntimeError('database is locked')",
        )
        runner = PluginMigrationRunner(fixture_plugin, FIXTURE_ID, _manifest())
        runner.run_migrations()

        with pytest.raises(RuntimeError, match="database is locked"):
            runner.downgrade_all()

        assert FIXTURE_TABLE in inspect(engine).get_table_names()
        assert runner.get_current_revision() == "fx_r3"
