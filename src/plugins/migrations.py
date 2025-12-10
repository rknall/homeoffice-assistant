# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Plugin migration management using Alembic."""

import logging
from datetime import datetime
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

from alembic import command
from src.config import settings
from src.database import SessionLocal

logger = logging.getLogger(__name__)


class PluginMigrationRunner:
    """Handles Alembic migrations for individual plugins.

    Each plugin gets its own version table (alembic_version_{plugin_id})
    to track migration state independently.
    """

    def __init__(self, plugin_path: Path, plugin_id: str) -> None:
        """Initialize the migration runner.

        Args:
            plugin_path: Path to the plugin directory
            plugin_id: Plugin identifier (used for version table name)
        """
        self.plugin_path = plugin_path
        self.plugin_id = plugin_id
        self.migrations_path = plugin_path / "backend" / "migrations"
        self._version_table = f"alembic_version_{plugin_id}"

    def has_migrations(self) -> bool:
        """Check if plugin has migrations.

        Returns:
            True if plugin has a migrations/versions directory
        """
        versions_path = self.migrations_path / "versions"
        return versions_path.exists() and any(versions_path.iterdir())

    def get_alembic_config(self) -> Config:
        """Create Alembic config for this plugin.

        Returns:
            Configured Alembic Config object
        """
        # Check for custom alembic.ini
        ini_path = self.migrations_path / "alembic.ini"
        alembic_cfg = Config(str(ini_path)) if ini_path.exists() else Config()

        # Override/set required options
        alembic_cfg.set_main_option("script_location", str(self.migrations_path))
        alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)

        # Use plugin-specific version table
        alembic_cfg.set_main_option("version_table", self._version_table)

        return alembic_cfg

    def run_migrations(self) -> list[str]:
        """Run pending migrations for this plugin.

        Returns:
            List of applied revision IDs
        """
        if not self.has_migrations():
            logger.debug(f"Plugin {self.plugin_id} has no migrations")
            return []

        applied: list[str] = []
        alembic_cfg = self.get_alembic_config()

        try:
            script = ScriptDirectory.from_config(alembic_cfg)
            engine = create_engine(settings.database_url)

            with engine.connect() as conn:
                context = MigrationContext.configure(
                    conn,
                    opts={"version_table": self._version_table},
                )
                current_rev = context.get_current_revision()
                head_rev = script.get_current_head()

                if current_rev == head_rev:
                    logger.debug(
                        f"Plugin {self.plugin_id} migrations up to date "
                        f"(at {current_rev})"
                    )
                    return []

            # Run upgrade to head
            logger.info(
                f"Running migrations for plugin {self.plugin_id} "
                f"({current_rev} -> {head_rev})"
            )
            command.upgrade(alembic_cfg, "head")

            # Record in our tracking table
            self._record_migration(head_rev or "head")
            applied.append(head_rev or "head")

            logger.info(f"Applied migrations for plugin {self.plugin_id}: {applied}")

        except Exception as e:
            logger.error(f"Migration failed for plugin {self.plugin_id}: {e}")
            raise

        return applied

    def downgrade_all(self) -> None:
        """Downgrade all migrations for this plugin (for uninstall)."""
        if not self.has_migrations():
            return

        alembic_cfg = self.get_alembic_config()

        try:
            logger.info(f"Downgrading all migrations for plugin {self.plugin_id}")
            command.downgrade(alembic_cfg, "base")

            # Clean up version table
            engine = create_engine(settings.database_url)
            with engine.connect() as conn:
                conn.execute(text(f"DROP TABLE IF EXISTS {self._version_table}"))
                conn.commit()

            # Remove from tracking
            self._remove_migration_history()

            logger.info(f"Downgraded all migrations for plugin {self.plugin_id}")

        except Exception as e:
            logger.error(f"Downgrade failed for plugin {self.plugin_id}: {e}")
            raise

    def get_current_revision(self) -> str | None:
        """Get the current migration revision for this plugin.

        Returns:
            Current revision ID or None if no migrations applied
        """
        if not self.has_migrations():
            return None

        try:
            engine = create_engine(settings.database_url)
            with engine.connect() as conn:
                context = MigrationContext.configure(
                    conn,
                    opts={"version_table": self._version_table},
                )
                return context.get_current_revision()
        except Exception:
            return None

    def get_pending_migrations(self) -> list[str]:
        """Get list of pending migration revisions.

        Returns:
            List of revision IDs not yet applied
        """
        if not self.has_migrations():
            return []

        alembic_cfg = self.get_alembic_config()
        script = ScriptDirectory.from_config(alembic_cfg)
        engine = create_engine(settings.database_url)

        with engine.connect() as conn:
            context = MigrationContext.configure(
                conn,
                opts={"version_table": self._version_table},
            )
            current_rev = context.get_current_revision()

        head_rev = script.get_current_head()
        if current_rev == head_rev:
            return []

        # Get all revisions from current to head
        pending = []
        for rev in script.iterate_revisions(head_rev, current_rev):
            if rev.revision != current_rev:
                pending.append(rev.revision)

        return list(reversed(pending))

    def _record_migration(self, revision: str) -> None:
        """Record a migration in the plugin migration history table.

        Args:
            revision: Revision ID that was applied
        """
        from src.models.plugin_config import PluginMigrationHistory

        db = SessionLocal()
        try:
            history = PluginMigrationHistory(
                plugin_id=self.plugin_id,
                revision=revision,
                applied_at=datetime.utcnow().isoformat(),
            )
            db.add(history)
            db.commit()
        finally:
            db.close()

    def _remove_migration_history(self) -> None:
        """Remove all migration history for this plugin."""
        from src.models.plugin_config import PluginMigrationHistory

        db = SessionLocal()
        try:
            db.query(PluginMigrationHistory).filter(
                PluginMigrationHistory.plugin_id == self.plugin_id
            ).delete()
            db.commit()
        finally:
            db.close()


def create_plugin_migration_env(plugin_path: Path, plugin_id: str) -> None:
    """Create a basic migrations environment for a plugin.

    This creates the migrations directory structure and env.py file
    for plugins that want to define their own migrations.

    Args:
        plugin_path: Path to the plugin directory
        plugin_id: Plugin identifier
    """
    migrations_path = plugin_path / "backend" / "migrations"
    versions_path = migrations_path / "versions"

    # Create directories
    versions_path.mkdir(parents=True, exist_ok=True)

    # Create env.py
    env_py_content = f'''"""Alembic environment for plugin {plugin_id}."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={{"paramstyle": "named"}},
        version_table=config.get_main_option("version_table"),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {{}}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table=config.get_main_option("version_table"),
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''

    env_py_path = migrations_path / "env.py"
    if not env_py_path.exists():
        with open(env_py_path, "w", encoding="utf-8") as f:
            f.write(env_py_content)

    # Create script.py.mako template
    mako_content = '''"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
'''

    mako_path = migrations_path / "script.py.mako"
    if not mako_path.exists():
        with open(mako_path, "w", encoding="utf-8") as f:
            f.write(mako_content)

    logger.info(f"Created migrations environment for plugin {plugin_id}")
