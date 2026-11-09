# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Backup and restore service.

Holds the data locations and the public entry points. The archive format
lives in ``backup_archive`` and the restore steps in ``backup_restore``; the
locations are read here on every call, so they can be pointed elsewhere.
"""

from pathlib import Path

from sqlalchemy.engine import make_url

from src.config import settings
from src.services import backup_restore, file_storage_service
from src.services.backup_archive import (
    BACKUP_FORMAT_VERSION,
    build_archive,
    validate_backup,
)
from src.services.backup_encryption import encrypt_backup_archive

__all__ = [
    "BACKUP_FORMAT_VERSION",
    "create_backup",
    "get_backup_info",
    "perform_restore",
    "validate_backup",
]

ENV_FILE_PATH = Path(".env")


def _sqlite_db_path(database_url: str) -> Path:
    """Return the SQLite file of a database URL, the default file otherwise.

    Args:
        database_url: The configured database URL.

    Returns:
        The database file a backup reads and a restore replaces.
    """
    url = make_url(database_url)
    if url.drivername.startswith("sqlite") and url.database:
        return Path(url.database)
    return Path("data") / "homeoffice_assistant.db"


DB_PATH = _sqlite_db_path(settings.database_url)
DATA_DIR = DB_PATH.parent


def pre_restore_dir_for(data_dir: Path) -> Path:
    """Return where pre-restore archives go: inside the persistent data dir.

    Args:
        data_dir: Directory holding the database (the mounted data volume).

    Returns:
        The pre-restore archive directory.
    """
    return data_dir / "backups" / "pre_restore"


PRE_RESTORE_BACKUP_DIR = pre_restore_dir_for(DATA_DIR)


def get_backup_info() -> dict:
    """Get information about current data that would be backed up."""
    db_exists = DB_PATH.exists()
    db_size = DB_PATH.stat().st_size if db_exists else 0
    avatar_dir = file_storage_service.AVATAR_DIR
    avatar_count = len(list(avatar_dir.glob("*"))) if avatar_dir.exists() else 0

    return {
        "database_exists": db_exists,
        "database_size_bytes": db_size,
        "avatar_count": avatar_count,
    }


def create_backup(username: str, password: str) -> tuple[bytes, str]:
    """Create a password-protected backup tarball.

    Args:
        username: Username of the admin creating the backup
        password: Password to encrypt the backup (min 8 chars)

    Returns:
        Tuple of (encrypted_bytes, filename); the bytes are the 16-byte salt
        followed by the encrypted tar.gz.
    """
    tarball_bytes, backup_name = build_archive(
        DB_PATH,
        file_storage_service.AVATAR_DIR,
        file_storage_service.LOGO_DIR,
        username,
        portable=True,
    )
    encrypted_bytes, salt = encrypt_backup_archive(tarball_bytes, password)
    return salt + encrypted_bytes, f"{backup_name}.tar.gz.enc"


def perform_restore(
    file_bytes: bytes,
    password: str | None = None,
    current_user_id: str | None = None,
) -> tuple[bool, str, dict]:
    """Restore a backup into the live data, keeping the current admin.

    Args:
        file_bytes: Raw backup file bytes
        password: Password for encrypted backups (required for v0.2.1+)
        current_user_id: ID of the current admin user to preserve

    Returns: (success, message, details)
        details includes: migrations_run, migrations_message, configs_imported
    """
    return backup_restore.perform_restore(
        file_bytes,
        password,
        current_user_id,
        backup_restore.RestorePaths(
            db_path=DB_PATH,
            avatar_dir=file_storage_service.AVATAR_DIR,
            logo_dir=file_storage_service.LOGO_DIR,
            pre_restore_dir=PRE_RESTORE_BACKUP_DIR,
            env_file=ENV_FILE_PATH,
        ),
    )
