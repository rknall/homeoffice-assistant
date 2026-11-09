# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Plugin migration management using Alembic."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from alembic import command
from src.config import settings
from src.database import SessionLocal, engine
from src.utils.time import utc_now

if TYPE_CHECKING:
    from src.plugins.base import PluginManifest

logger = logging.getLogger(__name__)


class PluginMigrationRunner:
    """Handles Alembic migrations for individual plugins.

    Each plugin gets its own version table (alembic_version_{plugin_id})
    to track migration state independently. Migrations run on a connection
    of the application engine, handed to the plugin's env.py through
    ``Config.attributes["connection"]``.
    """

    def __init__(
        self,
        plugin_path: Path,
        plugin_id: str,
        manifest: PluginManifest | None = None,
    ) -> None:
        """Initialize the migration runner.

        Args:
            plugin_path: Path to the plugin directory
            plugin_id: Plugin identifier (used for version table name)
            manifest: Optional plugin manifest (used for table_prefix)
        """
        self.plugin_path = plugin_path
        self.plugin_id = plugin_id
        self.manifest = manifest
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

        The database URL goes into ``attributes`` instead of the main options:
        main options pass through ConfigParser interpolation, which rejects a
        ``%`` (for example in a URL-encoded password).

        Returns:
            Configured Alembic Config object
        """
        ini_path = self.migrations_path / "alembic.ini"
        alembic_cfg = Config(str(ini_path)) if ini_path.exists() else Config()

        alembic_cfg.set_main_option("script_location", str(self.migrations_path))
        alembic_cfg.set_main_option("version_table", self._version_table)
        alembic_cfg.attributes["sqlalchemy.url"] = settings.database_url

        return alembic_cfg

    def run_migrations(self) -> list[str]:
        """Run pending migrations for this plugin.

        Does nothing when the plugin is already at its head revision.

        Returns:
            Applied revision IDs, oldest first

        Raises:
            Exception: Any migration error is logged and re-raised.
        """
        if not self.has_migrations():
            logger.debug("Plugin %s has no migrations", self.plugin_id)
            return []

        alembic_cfg = self.get_alembic_config()
        try:
            script = ScriptDirectory.from_config(alembic_cfg)
            head_rev = script.get_current_head()
            current_rev = self._current_revision()
            if current_rev == head_rev:
                logger.debug(
                    "Plugin %s migrations up to date (at %s)",
                    self.plugin_id,
                    current_rev,
                )
                return []

            pending = [
                rev.revision
                for rev in script.iterate_revisions(head_rev, current_rev)
                if rev.revision != current_rev
            ]
            pending.reverse()

            logger.info(
                "Running migrations for plugin %s (%s -> %s)",
                self.plugin_id,
                current_rev,
                head_rev,
            )
            with engine.begin() as conn:
                alembic_cfg.attributes["connection"] = conn
                command.upgrade(alembic_cfg, "head")
        except Exception:
            logger.exception("Migration failed for plugin %s", self.plugin_id)
            raise

        self._record_migrations(pending)
        logger.info("Applied migrations for plugin %s: %s", self.plugin_id, pending)
        return pending

    def downgrade_all(self) -> None:
        """Downgrade all migrations for this plugin (for uninstall).

        Runs the Alembic downgrade to base. Only when a migration's
        ``downgrade()`` raises NotImplementedError are the tables matching the
        plugin's table prefix dropped instead; every other error propagates, so
        a real failure (locked database, a bug) never turns into a table drop.
        """
        if not self.has_migrations():
            return

        alembic_cfg = self.get_alembic_config()

        try:
            logger.info("Downgrading all migrations for plugin %s", self.plugin_id)
            with engine.begin() as conn:
                alembic_cfg.attributes["connection"] = conn
                command.downgrade(alembic_cfg, "base")
            logger.info("Downgraded all migrations for plugin %s", self.plugin_id)
        except NotImplementedError as e:
            logger.warning(
                "Plugin %s migration doesn't support downgrade: %s. "
                "Falling back to force drop of plugin tables.",
                self.plugin_id,
                e,
            )
            self._force_drop_plugin_tables()

        # Quote the name: plugin ids may contain hyphens
        with engine.connect() as conn:
            conn.execute(text(f'DROP TABLE IF EXISTS "{self._version_table}"'))
            conn.commit()

        self._remove_migration_history()

    def _force_drop_plugin_tables(self) -> None:
        """Force drop all tables belonging to this plugin.

        Used when a migration's downgrade() raises NotImplementedError. Tables
        are identified by the plugin's table prefix.
        """
        prefix = self._get_table_prefix()
        plugin_tables = [
            t for t in inspect(engine).get_table_names() if t.startswith(prefix)
        ]

        if not plugin_tables:
            logger.warning(
                "No tables found with prefix '%s' for plugin %s",
                prefix,
                self.plugin_id,
            )
            return

        logger.info(
            "Force dropping %d tables for plugin %s: %s",
            len(plugin_tables),
            self.plugin_id,
            plugin_tables,
        )

        # SQLite: disable FK checks while dropping; PostgreSQL: use CASCADE
        is_sqlite = engine.dialect.name == "sqlite"
        cascade = " CASCADE" if engine.dialect.name == "postgresql" else ""
        with engine.connect() as conn:
            if is_sqlite:
                conn.execute(text("PRAGMA foreign_keys = OFF"))
            for table_name in plugin_tables:
                conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"{cascade}'))
            if is_sqlite:
                conn.execute(text("PRAGMA foreign_keys = ON"))
            conn.commit()

        logger.info("Force dropped tables for plugin %s", self.plugin_id)

    def _get_table_prefix(self) -> str:
        """Get the table prefix for this plugin.

        If the plugin manifest specifies a table_prefix, uses that value.
        Otherwise, derives a prefix from the plugin_id. For example:
        - "time-tracking" -> "tt_"
        - "example" -> "example_" (single word uses full name)
        - "my-cool-plugin" -> "mcp_"
        """
        # Use manifest table_prefix if available
        if self.manifest and self.manifest.table_prefix:
            return self.manifest.table_prefix

        # Fallback to deriving from plugin_id
        parts = self.plugin_id.replace("_", "-").split("-")
        if len(parts) == 1:
            # Single word plugin: use full name as prefix
            return f"{parts[0]}_"
        else:
            # Multi-word plugin: use initials
            return "".join(p[0] for p in parts if p) + "_"

    def get_current_revision(self) -> str | None:
        """Get the current migration revision for this plugin.

        Returns:
            Current revision ID, or None if no migrations are applied or the
            version table cannot be read
        """
        if not self.has_migrations():
            return None

        try:
            return self._current_revision()
        except Exception:
            return None

    def _current_revision(self) -> str | None:
        """Read the revision stored in the plugin's version table.

        Returns:
            Current revision ID or None if no migrations applied
        """
        with engine.connect() as conn:
            context = MigrationContext.configure(
                conn,
                opts={"version_table": self._version_table},
            )
            return context.get_current_revision()

    def _record_migrations(self, revisions: list[str]) -> None:
        """Record applied revisions in the plugin migration history table.

        Args:
            revisions: Revision IDs that were applied, oldest first
        """
        from src.models.plugin_config import PluginMigrationHistory

        applied_at = utc_now().isoformat()
        db = SessionLocal()
        try:
            db.add_all(
                PluginMigrationHistory(
                    plugin_id=self.plugin_id,
                    revision=revision,
                    applied_at=applied_at,
                )
                for revision in revisions
            )
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
