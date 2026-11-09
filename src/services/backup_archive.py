# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Backup archive format: building, decrypting, extracting and validating."""

import hashlib
import json
import logging
import shutil
import sqlite3
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from src.encryption import decrypt_config, encrypt_config
from src.services.backup_encryption import try_decrypt_backup

logger = logging.getLogger(__name__)

# Current backup format version
BACKUP_FORMAT_VERSION = "0.2.2"

DB_FILE_NAME = "homeoffice_assistant.db"
CONFIGS_FILE_NAME = "integration_configs.json"
MANIFEST_FILE_NAME = "manifest.json"
SALT_LENGTH = 16


def copy_sqlite(source: Path, dest: Path) -> None:
    """Copy a SQLite database with the online backup API.

    The backup API takes the proper locks, so it is safe while other
    connections have the source or destination open, and it replaces the
    whole destination content in place.

    Args:
        source: Database file to read.
        dest: Database file to write; created when missing.
    """
    src_conn = sqlite3.connect(str(source))
    dest_conn = sqlite3.connect(str(dest))
    try:
        src_conn.backup(dest_conn)
    finally:
        src_conn.close()
        dest_conn.close()


def _export_integration_configs(db_path: Path) -> list[dict]:
    """Extract and decrypt the integration configs of a database.

    Args:
        db_path: Database to read.

    Returns:
        Config dicts with the decrypted ``config_data`` (None when it cannot
        be decrypted). Empty when the table cannot be read.
    """
    configs = []
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, integration_type, name, config_encrypted, is_active,
                   created_by, created_at, updated_at
            FROM integration_configs
            """
        ).fetchall()
        conn.close()
    except Exception as e:
        logger.warning(f"Failed to export integration configs: {e}")
        return configs

    for row in rows:
        config_dict = dict(row)
        encrypted = config_dict.pop("config_encrypted", None)
        config_dict["config_data"] = None
        if encrypted:
            try:
                config_dict["config_data"] = decrypt_config(encrypted)
            except Exception as e:
                logger.warning(f"Failed to decrypt config {row['id']}: {e}")
        configs.append(config_dict)
    return configs


_INSERT_CONFIG = """
    INSERT INTO integration_configs
    (id, integration_type, name, config_encrypted, is_active,
     created_by, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""


def import_integration_configs(
    db_path: Path, configs: list[dict], admin_id_hex: str
) -> int:
    """Re-encrypt the exported integration configs into the restored database.

    The rows go in as raw values exactly as they were exported, so ids and
    timestamps keep their stored form; only ``created_by`` changes to the
    admin.

    Args:
        db_path: The restored database.
        configs: Config dicts with decrypted ``config_data``.
        admin_id_hex: The admin id in its stored (hex) form.

    Returns:
        Number of configs imported.
    """
    imported = 0
    conn = sqlite3.connect(str(db_path))
    try:
        # Existing rows are encrypted with the other instance's SECRET_KEY.
        conn.execute("DELETE FROM integration_configs")
        for config in configs:
            if config.get("config_data") is None:
                logger.warning(f"Skipping config {config.get('id')}: no config_data")
                continue
            conn.execute(
                _INSERT_CONFIG,
                (
                    config["id"],
                    config["integration_type"],
                    config["name"],
                    encrypt_config(config["config_data"]),
                    config["is_active"],
                    admin_id_hex,
                    config["created_at"],
                    config["updated_at"],
                ),
            )
            imported += 1
        conn.commit()
    finally:
        conn.close()
    logger.info(f"Imported {imported}/{len(configs)} integration configs")
    return imported


def _strip_users(db_path: Path) -> None:
    """Remove users and sessions from a backup copy (they are per instance).

    Args:
        db_path: The backup copy of the database.
    """
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("DELETE FROM users")
        conn.execute("DELETE FROM sessions")
        conn.commit()
    finally:
        conn.close()
    logger.info("Cleared users and sessions from backup database")


def _write_manifest(backup_dir: Path, username: str, *, portable: bool) -> None:
    """Write manifest.json describing the files already in ``backup_dir``.

    Args:
        backup_dir: The backup directory being archived.
        username: Name recorded as ``created_by``.
        portable: False marks the archive as an internal pre-restore copy.
    """
    db_file = backup_dir / DB_FILE_NAME
    avatars = backup_dir / "avatars"
    manifest = {
        "backup_format_version": BACKUP_FORMAT_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "created_by": username,
        "db_size_bytes": db_file.stat().st_size if db_file.exists() else 0,
        "avatar_count": len(list(avatars.glob("*"))) if avatars.exists() else 0,
        "checksum": (
            hashlib.sha256(db_file.read_bytes()).hexdigest() if db_file.exists() else ""
        ),
    }
    if not portable:
        manifest["internal_backup"] = True
    with open(backup_dir / MANIFEST_FILE_NAME, "w") as f:
        json.dump(manifest, f, indent=2)


def build_archive(
    db_path: Path, avatar_dir: Path, logo_dir: Path, username: str, *, portable: bool
) -> tuple[bytes, str]:
    """Build a plain tar.gz backup of the database, the avatars and the logos.

    The ``logos/`` directory is always written, empty when there are no
    logos, so a restore can tell a current archive from one made before
    logos were backed up.

    Args:
        db_path: The live database file.
        avatar_dir: The avatar directory.
        logo_dir: The company logo directory.
        username: Name recorded as ``created_by`` in the manifest.
        portable: True for a backup meant for another instance: users and
            sessions are removed and the integration configs are exported
            decrypted, because the other instance has a different SECRET_KEY.
            False for the internal pre-restore copy, kept as it is.

    Returns:
        Tuple of (tar.gz bytes, backup name without extension).
    """
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_name = f"homeoffice_assistant_backup_{timestamp}"

    with tempfile.TemporaryDirectory() as temp_dir:
        backup_dir = Path(temp_dir) / backup_name
        backup_dir.mkdir()
        db_file = backup_dir / DB_FILE_NAME

        if db_path.exists():
            copy_sqlite(db_path, db_file)
            if portable:
                # Users go before the config export, so no config refers to a
                # user the archive does not contain.
                _strip_users(db_file)
                configs = _export_integration_configs(db_file)
                with open(backup_dir / CONFIGS_FILE_NAME, "w") as f:
                    json.dump(configs, f, indent=2, default=str)

        if avatar_dir.exists() and any(avatar_dir.iterdir()):
            shutil.copytree(avatar_dir, backup_dir / "avatars")
        logos = backup_dir / "logos"
        logos.mkdir()
        if logo_dir.exists():
            shutil.copytree(logo_dir, logos, dirs_exist_ok=True)

        _write_manifest(backup_dir, username, portable=portable)

        tarball_path = Path(temp_dir) / f"{backup_name}.tar.gz"
        with tarfile.open(tarball_path, "w:gz") as tar:
            tar.add(backup_dir, arcname=backup_name)
        return tarball_path.read_bytes(), backup_name


def is_encrypted_backup(file_bytes: bytes) -> bool:
    """Tell a password-encrypted backup (v0.2.1+) from a plain tar.gz (v0.2.0).

    Args:
        file_bytes: Uploaded file bytes.

    Returns:
        False when the bytes start with the gzip magic number.
    """
    return not (len(file_bytes) >= 2 and file_bytes[0:2] == b"\x1f\x8b")


def decrypt_upload(
    file_bytes: bytes, password: str | None
) -> tuple[bool, str, bytes | None]:
    """Return the tar.gz bytes of an upload, decrypting it when needed.

    The encrypted format is the 16-byte salt followed by the encrypted data.

    Args:
        file_bytes: Uploaded file bytes.
        password: Backup password; required for encrypted backups.

    Returns:
        Tuple of (success, error message, tar.gz bytes or None).
    """
    if not is_encrypted_backup(file_bytes):
        return True, "", file_bytes
    if not password:
        return (
            False,
            "This backup is password-protected. Please provide the password.",
            None,
        )
    salt, data = file_bytes[:SALT_LENGTH], file_bytes[SALT_LENGTH:]
    success, decrypted, error_msg = try_decrypt_backup(data, password, salt)
    if not success:
        return False, error_msg, None
    return True, "", decrypted


def _manifest_metadata(backup_dir: Path, warnings: list[str]) -> dict:
    """Read the manifest of an extracted backup into the metadata dict.

    Args:
        backup_dir: Extracted backup directory.
        warnings: List the manifest warnings are appended to.

    Returns:
        The metadata from the manifest, or synthetic metadata without one.
    """
    now = datetime.now(UTC).isoformat()
    manifest_path = backup_dir / MANIFEST_FILE_NAME
    if not manifest_path.exists():
        warnings.append("No manifest.json found - backup may be from an older version")
        manifest_data: dict = {"backup_format_version": "unknown"}
    else:
        with open(manifest_path) as f:
            manifest_data = json.load(f)

    metadata = {
        "backup_format_version": manifest_data.get(
            "backup_format_version", manifest_data.get("version", "0.2.0")
        ),
        "created_at": manifest_data.get("created_at", now),
        "created_by": manifest_data.get("created_by", "unknown"),
        "db_size_bytes": manifest_data.get("db_size_bytes", 0),
        "avatar_count": manifest_data.get("avatar_count", 0),
        "checksum": manifest_data.get("checksum", ""),
    }
    if "secret_key" in manifest_data:
        metadata["has_legacy_secret_key"] = True
        warnings.append(
            "This is a legacy backup (v0.2.0). Consider creating a new "
            "password-protected backup for better security."
        )
    return metadata


def extract_archive(
    tar_bytes: bytes, dest: Path
) -> tuple[Path | None, str, dict | None, list[str]]:
    """Extract a tar.gz backup into ``dest`` and check its content.

    Args:
        tar_bytes: Decrypted tar.gz bytes.
        dest: Empty directory to extract into.

    Returns:
        Tuple of (backup directory or None when invalid, message, metadata,
        warnings).
    """
    tarball_path = dest / "upload.tar.gz"
    tarball_path.write_bytes(tar_bytes)
    try:
        with tarfile.open(tarball_path, "r:gz") as tar:
            for member in tar.getmembers():
                if member.name.startswith("/") or ".." in member.name:
                    return None, "Invalid backup file: contains unsafe paths", None, []
            tar.extractall(dest, filter="data")
    except tarfile.TarError:
        return None, "Invalid or corrupted backup file", None, []

    subdirs = [d for d in dest.iterdir() if d.is_dir()]
    if not subdirs:
        return None, "Backup archive is empty", None, []
    backup_dir = subdirs[0]

    warnings: list[str] = []
    metadata = _manifest_metadata(backup_dir, warnings)

    db_path = backup_dir / DB_FILE_NAME
    if not db_path.exists():
        return None, "No database file found in backup", None, []
    with open(db_path, "rb") as f:
        if not f.read(16).startswith(b"SQLite format 3"):
            return None, "Database file is not a valid SQLite database", None, []

    metadata["db_size_bytes"] = db_path.stat().st_size
    avatar_dir = backup_dir / "avatars"
    metadata["avatar_count"] = (
        len(list(avatar_dir.glob("*"))) if avatar_dir.exists() else 0
    )
    metadata["integration_config_count"] = len(read_integration_configs(backup_dir))
    return backup_dir, "Backup is valid", metadata, warnings


def read_integration_configs(backup_dir: Path) -> list[dict]:
    """Read the exported integration configs of an extracted backup.

    Args:
        backup_dir: Extracted backup directory.

    Returns:
        The config dicts, empty for backups before v0.2.1.
    """
    configs_path = backup_dir / CONFIGS_FILE_NAME
    if not configs_path.exists():
        return []
    with open(configs_path) as f:
        return json.load(f)


def read_legacy_secret_key(backup_dir: Path) -> str | None:
    """Return the SECRET_KEY stored in a legacy (v0.2.0) manifest.

    Args:
        backup_dir: Extracted backup directory.

    Returns:
        The key, or None when the manifest has none.
    """
    manifest_path = backup_dir / MANIFEST_FILE_NAME
    if not manifest_path.exists():
        return None
    with open(manifest_path) as f:
        return json.load(f).get("secret_key")


def validate_backup(
    file_bytes: bytes, password: str | None = None
) -> tuple[bool, str, dict | None, list[str]]:
    """Validate an uploaded backup file.

    Args:
        file_bytes: Raw uploaded file bytes.
        password: Password for encrypted backups (required for v0.2.1+).

    Returns:
        Tuple of (valid, message, metadata, warnings).
    """
    encrypted = is_encrypted_backup(file_bytes)
    if encrypted and not password:
        return (
            False,
            "This backup is password-protected. Please provide the password.",
            {"backup_format_version": "0.2.1+", "is_password_protected": True},
            [],
        )
    ok, error, tar_bytes = decrypt_upload(file_bytes, password)
    if not ok or tar_bytes is None:
        return False, error, None, []

    with tempfile.TemporaryDirectory() as temp_dir:
        backup_dir, message, metadata, warnings = extract_archive(
            tar_bytes, Path(temp_dir)
        )
    if backup_dir is None or metadata is None:
        return False, message, None, []
    metadata["is_password_protected"] = encrypted
    return True, message, metadata, warnings
