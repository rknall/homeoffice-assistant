# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Restore of a backup archive into the live database.

The archive database is prepared in a temporary location first: migrated to
the current schema, the current admin inserted and every reference to a user
of the backup re-pointed. Only when all of that succeeded is it copied over the
live database. A failure during the swap rolls the live database, the
avatars and the company logos back from the copy taken just before.
"""

import logging
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alembic.config import Config
from sqlalchemy import Column, UniqueConstraint, create_engine, delete, inspect
from sqlalchemy import update as sql_update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from alembic import command
from src.database import SessionLocal
from src.models import Base, User
from src.models import Session as UserSession
from src.plugins.registry import PluginRegistry
from src.rbac.roles import GLOBAL_ADMIN_ROLE
from src.services import rbac_service
from src.services.backup_archive import (
    DB_FILE_NAME,
    build_archive,
    copy_sqlite,
    decrypt_upload,
    extract_archive,
    import_integration_configs,
    is_encrypted_backup,
    read_integration_configs,
    read_legacy_secret_key,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"


@dataclass(frozen=True)
class RestorePaths:
    """Locations a restore reads from and writes to."""

    db_path: Path
    avatar_dir: Path
    logo_dir: Path
    pre_restore_dir: Path
    env_file: Path


def _sqlite_engine(db_path: Path) -> Engine:
    """Create a throwaway engine for one SQLite file."""
    return create_engine(f"sqlite:///{db_path}", poolclass=NullPool)


def load_admin_row(db_path: Path, user_id: str) -> dict[str, Any] | None:
    """Load a user through the ORM and return its row keyed by column name.

    Args:
        db_path: The live database file.
        user_id: The user's UUID as a string.

    Returns:
        The column values of ``User.__table__``, or None when not found.
    """
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        return None
    engine = _sqlite_engine(db_path)
    try:
        with Session(engine) as db:
            user = db.get(User, uid)
            if user is None:
                return None
            return {
                column.name: getattr(user, column.key)
                for column in User.__table__.columns
            }
    except Exception as e:
        logger.error(f"Failed to load user {user_id} for preservation: {e}")
        return None
    finally:
        engine.dispose()


def core_alembic_config(url: str | None = None) -> Config:
    """Build an Alembic config for the core migration chain.

    The script location is read from alembic.ini at the project root, so the
    config does not depend on the working directory. The ini file itself is
    not handed to alembic: env.py would apply its logging section to the
    running application.

    Args:
        url: Database to migrate, handed to env.py as the ``sqlalchemy.url``
            attribute. None leaves env.py on the application settings.

    Returns:
        The config.
    """
    script_location = Config(str(ALEMBIC_INI)).get_main_option("script_location")
    alembic_cfg = Config()
    alembic_cfg.set_main_option(
        "script_location", str(PROJECT_ROOT / (script_location or "alembic"))
    )
    if url is not None:
        alembic_cfg.attributes["sqlalchemy.url"] = url
    return alembic_cfg


def upgrade_core(db_path: Path) -> None:
    """Upgrade a database file to the core migration head.

    Args:
        db_path: The database file to upgrade.

    Raises:
        Exception: Whatever alembic raises when a migration fails.
    """
    command.upgrade(core_alembic_config(f"sqlite:///{db_path}"), "head")


def _is_unique(column: Column) -> bool:
    """Tell whether a column is part of a primary key or unique constraint."""
    if column.primary_key or column.unique:
        return True
    table = column.table
    for constraint in table.constraints:
        if isinstance(constraint, UniqueConstraint) and any(
            col is column for col in constraint.columns
        ):
            return True
    return any(
        index.unique and any(col is column for col in index.columns)
        for index in table.indexes
    )


def _user_fk_columns(db: Session) -> list[Column]:
    """List every column of an existing table that references ``users.id``."""
    existing = set(inspect(db.get_bind()).get_table_names())
    return [
        fk.parent
        for table in Base.metadata.sorted_tables
        if table.name in existing
        for fk in table.foreign_keys
        if fk.column is User.__table__.c.id
    ]


def _reassign_user_rows(db: Session, admin_id: uuid.UUID) -> None:
    """Point every reference to a backup user at the admin, or drop the row.

    A column that must be unique per user (role assignments, per-user
    preferences) cannot take the admin for every row, so rows not belonging
    to the admin are deleted. Everything else is data the admin takes over.
    NULL stays NULL.

    Args:
        db: Session on the restored database.
        admin_id: The preserved admin.
    """
    for column in _user_fk_columns(db):
        table = column.table
        if _is_unique(column):
            stmt = delete(table).where(column != admin_id)
            action = "deleted"
        else:
            stmt = (
                sql_update(table)
                .where(column.is_not(None), column != admin_id)
                .values({column.key: admin_id})
            )
            action = "re-pointed"
        count = db.execute(stmt).rowcount
        logger.info(f"{table.name}.{column.name}: {count} rows {action}")


def _grant_global_admin(db: Session, admin_id: uuid.UUID) -> None:
    """Give the admin the global Global Admin role unless it holds it.

    Args:
        db: Session on the restored database.
        admin_id: The preserved admin.

    Raises:
        RuntimeError: The restored database has no Global Admin role.
    """
    role = rbac_service.get_role_by_name(db, GLOBAL_ADMIN_ROLE)
    if role is None:
        raise RuntimeError(f"Restored database has no {GLOBAL_ADMIN_ROLE} role")
    admin = db.get(User, admin_id)
    if admin is None:
        raise RuntimeError("Admin missing from the restored database")
    if role not in rbac_service.get_user_roles(db, admin):
        rbac_service.assign_role_to_user(db, user_id=admin_id, role_id=role.id)


def _preserve_admin(db_path: Path, admin_row: dict[str, Any]) -> None:
    """Replace the users of the restored database with the current admin.

    Args:
        db_path: The restored database.
        admin_row: The admin's ``User.__table__`` column values.
    """
    users = User.__table__
    admin_id = admin_row["id"]
    engine = _sqlite_engine(db_path)
    try:
        with Session(engine) as db:
            db.execute(delete(UserSession.__table__))
            db.execute(delete(users))
            db.execute(users.insert().values(**admin_row))
            _reassign_user_rows(db, admin_id)
            _grant_global_admin(db, admin_id)
            db.commit()
    finally:
        engine.dispose()
    logger.info(f"Preserved admin '{admin_row['username']}' in restored database")


def _prepare(
    backup_dir: Path, staged: Path, admin_row: dict[str, Any] | None, details: dict
) -> None:
    """Build the database to swap in, without touching the live data.

    Args:
        backup_dir: Extracted backup directory.
        staged: Where the prepared database is written.
        admin_row: The admin to preserve, None to keep the users as they are.
        details: Result details, updated in place.
    """
    shutil.copy2(backup_dir / DB_FILE_NAME, staged)
    upgrade_core(staged)
    details["migrations_run"] = True
    details["migrations_message"] = "Migrations completed successfully"
    if admin_row is None:
        return
    configs = read_integration_configs(backup_dir)
    if configs:
        details["configs_imported"] = import_integration_configs(
            staged, configs, admin_row["id"].hex
        )
    _preserve_admin(staged, admin_row)


def _replace_dir_content(source: Path, target: Path) -> None:
    """Make ``target`` hold exactly the files of ``source`` (none if absent).

    Only the directory's content is replaced, never the directory itself: in
    the image the avatar directory is a volume mount point inside a read-only
    parent.
    """
    target.mkdir(parents=True, exist_ok=True)
    for entry in target.iterdir():
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry)
        else:
            entry.unlink()
    if source.exists():
        shutil.copytree(source, target, dirs_exist_ok=True)


def _save_pre_restore(paths: RestorePaths, work: Path) -> None:
    """Keep the current data: an archive for the admin, copies for rollback.

    Args:
        paths: Restore locations.
        work: Temporary directory holding the rollback copies.
    """
    archive, _ = build_archive(
        paths.db_path,
        paths.avatar_dir,
        paths.logo_dir,
        "system_pre_restore",
        portable=False,
    )
    paths.pre_restore_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    (paths.pre_restore_dir / f"pre_restore_{timestamp}.tar.gz").write_bytes(archive)
    if paths.db_path.exists():
        copy_sqlite(paths.db_path, work / "pre_restore.db")
    if paths.avatar_dir.exists():
        shutil.copytree(paths.avatar_dir, work / "avatars_before")
    # Always present, so a rollback also restores "no logos yet".
    logos_before = work / "logos_before"
    logos_before.mkdir()
    if paths.logo_dir.exists():
        shutil.copytree(paths.logo_dir, logos_before, dirs_exist_ok=True)


def _swap_in(staged: Path, backup_dir: Path, paths: RestorePaths) -> None:
    """Copy the prepared database, the avatars and the logos into place.

    Archives made before logos were backed up have no ``logos/`` directory;
    the current logos then stay as they are.
    """
    paths.db_path.parent.mkdir(parents=True, exist_ok=True)
    copy_sqlite(staged, paths.db_path)
    _replace_dir_content(backup_dir / "avatars", paths.avatar_dir)
    if (backup_dir / "logos").is_dir():
        _replace_dir_content(backup_dir / "logos", paths.logo_dir)


def _roll_back(work: Path, paths: RestorePaths) -> None:
    """Put back the database, avatars and logos saved by ``_save_pre_restore``."""
    pre_db = work / "pre_restore.db"
    if pre_db.exists():
        copy_sqlite(pre_db, paths.db_path)
    else:
        paths.db_path.unlink(missing_ok=True)
    _replace_dir_content(work / "avatars_before", paths.avatar_dir)
    _replace_dir_content(work / "logos_before", paths.logo_dir)
    logger.warning("Restore rolled back to the pre-restore data")


def _migrate_plugins() -> str:
    """Bring every registered plugin's tables to its migration head.

    A failing plugin is skipped, as at startup, so the result is a note for
    the response rather than a failed restore.

    Returns:
        Text to append to the migrations message, empty when all passed.
    """
    try:
        with SessionLocal() as db:
            failed = PluginRegistry.get_instance().run_plugin_migrations(db)
    except Exception:
        logger.exception("Plugin migrations after restore failed")
        return " Plugin migrations failed, see server log."
    if failed:
        return f" Plugin migrations failed for: {', '.join(failed)}."
    return ""


def _update_env_secret_key(env_file: Path, new_secret_key: str) -> None:
    """Update or create the SECRET_KEY line in the .env file."""
    lines = env_file.read_text().splitlines() if env_file.exists() else []
    key_line = f"SECRET_KEY={new_secret_key}"
    found = False
    new_lines = []
    for line in lines:
        if line.strip().startswith("SECRET_KEY="):
            new_lines.append(key_line)
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(key_line)
    env_file.write_text("\n".join(new_lines) + "\n")


def _restore_archive(
    tar_bytes: bytes,
    admin_row: dict[str, Any] | None,
    paths: RestorePaths,
    details: dict,
) -> tuple[bool, str, str | None]:
    """Extract, prepare and swap in an archive, rolling back a failed swap.

    Args:
        tar_bytes: Decrypted tar.gz bytes.
        admin_row: The admin to preserve, None to keep the backup's users.
        paths: Restore locations.
        details: Result details, updated in place.

    Returns:
        Tuple of (success, error message, the legacy SECRET_KEY to adopt).
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        work = Path(temp_dir)
        extract_dir = work / "archive"
        extract_dir.mkdir()
        backup_dir, message, _metadata, _warnings = extract_archive(
            tar_bytes, extract_dir
        )
        if backup_dir is None:
            return False, message, None

        staged = work / "restored.db"
        try:
            _prepare(backup_dir, staged, admin_row, details)
        except Exception:
            logger.exception("Restore preparation failed, live data untouched")
            return False, "Restore failed, nothing was changed, see server log", None
        try:
            _save_pre_restore(paths, work)
        except Exception:
            logger.exception("Pre-restore backup failed")
            return False, "Failed to create pre-restore backup, see server log", None
        try:
            _swap_in(staged, backup_dir, paths)
        except Exception:
            logger.exception("Restore swap failed, rolling back")
            _roll_back(work, paths)
            return False, "Restore failed and was rolled back, see server log", None

        # Legacy backups carry no exported configs; theirs stay encrypted with
        # the old key, which therefore has to become this instance's key.
        if admin_row and read_integration_configs(backup_dir):
            return True, "", None
        return True, "", read_legacy_secret_key(backup_dir)


def perform_restore(
    file_bytes: bytes,
    password: str | None,
    current_user_id: str | None,
    paths: RestorePaths,
) -> tuple[bool, str, dict]:
    """Restore a backup, keeping the current admin.

    Args:
        file_bytes: Raw backup file bytes.
        password: Password for encrypted backups (required for v0.2.1+).
        current_user_id: The admin to preserve; None keeps the backup's users.
        paths: Restore locations.

    Returns:
        Tuple of (success, message, details); details holds migrations_run,
        migrations_message and configs_imported.
    """
    details: dict = {
        "migrations_run": False,
        "migrations_message": "",
        "configs_imported": 0,
    }
    admin_row = None
    if current_user_id:
        admin_row = load_admin_row(paths.db_path, current_user_id)
        if admin_row is None:
            return False, "Failed to get current user data for preservation", details

    if is_encrypted_backup(file_bytes) and not password:
        return False, "Password required for encrypted backup", details
    ok, error, tar_bytes = decrypt_upload(file_bytes, password)
    if not ok or tar_bytes is None:
        return False, error, details

    ok, message, legacy_secret_key = _restore_archive(
        tar_bytes, admin_row, paths, details
    )
    if not ok:
        return False, message, details

    details["migrations_message"] += _migrate_plugins()

    if legacy_secret_key:
        _update_env_secret_key(paths.env_file, legacy_secret_key)
        details["migrations_message"] += (
            " Note: Legacy backup restored with original SECRET_KEY. "
            "Consider creating a new password-protected backup."
        )

    return (
        True,
        "Restore completed. Please restart the application to apply changes.",
        details,
    )
