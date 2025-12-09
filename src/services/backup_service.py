# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Backup and restore service."""
import hashlib
import json
import logging
import shutil
import sqlite3
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from src.config import settings
from src.encryption import decrypt_config, encrypt_config
from src.services.backup_encryption import (
    encrypt_backup_archive,
    try_decrypt_backup,
)

logger = logging.getLogger(__name__)

# Current backup format version
BACKUP_FORMAT_VERSION = "0.2.1"

# Derive paths from database URL
DATA_DIR = Path("./data")
AVATAR_DIR = Path("./static/avatars")
DB_PATH = DATA_DIR / "travel_manager.db"
PRE_RESTORE_BACKUP_DIR = Path("./backups/pre_restore")

# If using custom database URL, extract the path
if settings.database_url.startswith("sqlite:///"):
    db_path_str = settings.database_url.replace("sqlite:///", "")
    if db_path_str.startswith("./"):
        db_path_str = db_path_str[2:]
    DB_PATH = Path(db_path_str)
    DATA_DIR = DB_PATH.parent


def get_backup_info() -> dict:
    """Get information about current data that would be backed up."""
    db_exists = DB_PATH.exists()
    db_size = DB_PATH.stat().st_size if db_exists else 0
    avatar_count = len(list(AVATAR_DIR.glob("*"))) if AVATAR_DIR.exists() else 0

    return {
        "database_exists": db_exists,
        "database_size_bytes": db_size,
        "avatar_count": avatar_count,
    }


def _export_integration_configs(db_path: Path) -> list[dict]:
    """Extract and decrypt integration configs from database.

    Returns a list of config dicts with decrypted config_data.
    """
    configs = []
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, integration_type, name, config_encrypted, is_active, created_by,
                   created_at, updated_at
            FROM integration_configs
            """
        )
        rows = cursor.fetchall()

        for row in rows:
            config_dict = dict(row)
            # Decrypt the config data
            encrypted = config_dict.pop("config_encrypted", None)
            if encrypted:
                try:
                    config_dict["config_data"] = decrypt_config(encrypted)
                except Exception as e:
                    logger.warning(f"Failed to decrypt config {row['id']}: {e}")
                    config_dict["config_data"] = None
            else:
                config_dict["config_data"] = None
            configs.append(config_dict)

        conn.close()
    except Exception as e:
        logger.warning(f"Failed to export integration configs: {e}")

    return configs


def create_backup(username: str, password: str) -> tuple[bytes, str]:
    """Create a password-protected backup tarball.

    Args:
        username: Username of the admin creating the backup
        password: Password to encrypt the backup (min 8 chars)

    Returns:
        Tuple of (encrypted_bytes, filename)
    """
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_name = f"travel_manager_backup_{timestamp}"

    with tempfile.TemporaryDirectory() as temp_dir:
        backup_dir = Path(temp_dir) / backup_name
        backup_dir.mkdir()

        # Safe SQLite backup using .backup command
        if DB_PATH.exists():
            dest_db = backup_dir / "travel_manager.db"
            conn = sqlite3.connect(str(DB_PATH))
            backup_conn = sqlite3.connect(str(dest_db))
            conn.backup(backup_conn)
            conn.close()
            backup_conn.close()

            # Clear users and sessions from backup (users are instance-specific)
            # This must happen before exporting configs to avoid foreign key issues
            clean_conn = sqlite3.connect(str(dest_db))
            clean_conn.execute("DELETE FROM users")
            clean_conn.execute("DELETE FROM sessions")
            clean_conn.commit()
            clean_conn.close()
            logger.info("Cleared users and sessions from backup database")

            # Export integration configs (decrypted) before we lose access to SECRET_KEY
            integration_configs = _export_integration_configs(dest_db)
            with open(backup_dir / "integration_configs.json", "w") as f:
                json.dump(integration_configs, f, indent=2, default=str)

        # Copy avatars
        if AVATAR_DIR.exists() and any(AVATAR_DIR.iterdir()):
            shutil.copytree(AVATAR_DIR, backup_dir / "avatars")

        # Create manifest (without SECRET_KEY)
        db_file = backup_dir / "travel_manager.db"
        db_size = db_file.stat().st_size if db_file.exists() else 0
        avatar_dir = backup_dir / "avatars"
        avatar_count = len(list(avatar_dir.glob("*"))) if avatar_dir.exists() else 0

        # Calculate checksum
        checksum = ""
        if db_file.exists():
            with open(db_file, "rb") as f:
                checksum = hashlib.sha256(f.read()).hexdigest()

        manifest = {
            "backup_format_version": BACKUP_FORMAT_VERSION,
            "created_at": datetime.now(UTC).isoformat(),
            "created_by": username,
            "db_size_bytes": db_size,
            "avatar_count": avatar_count,
            "checksum": checksum,
            # Note: salt will be prepended to the encrypted file, not stored in manifest
        }

        with open(backup_dir / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        # Create tarball
        tarball_path = Path(temp_dir) / f"{backup_name}.tar.gz"
        with tarfile.open(tarball_path, "w:gz") as tar:
            tar.add(backup_dir, arcname=backup_name)

        with open(tarball_path, "rb") as f:
            tarball_bytes = f.read()

        # Encrypt with password
        encrypted_bytes, salt = encrypt_backup_archive(tarball_bytes, password)

        # Prepend salt to encrypted data (16 bytes salt + encrypted data)
        final_bytes = salt + encrypted_bytes

        return final_bytes, f"{backup_name}.tar.gz.enc"


def _is_encrypted_backup(file_bytes: bytes) -> bool:
    """Check if backup is password-encrypted (v0.2.1+) or plain tar.gz (v0.2.0)."""
    # Plain tar.gz starts with gzip magic bytes: 1f 8b
    return not (len(file_bytes) >= 2 and file_bytes[0:2] == b"\x1f\x8b")


def _extract_salt_and_data(encrypted_bytes: bytes) -> tuple[bytes, bytes]:
    """Extract salt (first 16 bytes) and encrypted data from v0.2.1 backup."""
    salt = encrypted_bytes[:16]
    data = encrypted_bytes[16:]
    return salt, data


def validate_backup(
    file_bytes: bytes, password: str | None = None
) -> tuple[bool, str, dict | None, list[str]]:
    """Validate an uploaded backup file.

    Args:
        file_bytes: Raw uploaded file bytes
        password: Password for encrypted backups (required for v0.2.1+)

    Returns: (valid, message, metadata, warnings)
    """
    warnings: list[str] = []
    is_encrypted = _is_encrypted_backup(file_bytes)

    # Handle encrypted backup (v0.2.1+)
    if is_encrypted:
        if not password:
            # Return metadata indicating password is required
            return (
                False,
                "This backup is password-protected. Please provide the password.",
                {
                    "backup_format_version": "0.2.1+",
                    "is_password_protected": True,
                },
                [],
            )

        salt, encrypted_data = _extract_salt_and_data(file_bytes)
        success, decrypted_bytes, error_msg = try_decrypt_backup(
            encrypted_data, password, salt
        )
        if not success:
            return False, error_msg, None, []
        file_bytes = decrypted_bytes

    with tempfile.TemporaryDirectory() as temp_dir:
        tarball_path = Path(temp_dir) / "upload.tar.gz"
        with open(tarball_path, "wb") as f:
            f.write(file_bytes)

        # Try to extract
        try:
            with tarfile.open(tarball_path, "r:gz") as tar:
                # Security check: ensure no absolute paths or path traversal
                for member in tar.getmembers():
                    if member.name.startswith("/") or ".." in member.name:
                        return False, "Invalid backup file: contains unsafe paths", None, []
                tar.extractall(temp_dir)
        except tarfile.TarError:
            return False, "Invalid or corrupted backup file", None, []

        # Find the backup directory
        subdirs = [d for d in Path(temp_dir).iterdir() if d.is_dir()]
        if not subdirs:
            return False, "Backup archive is empty", None, []

        backup_dir = subdirs[0]

        # Check for manifest
        manifest_path = backup_dir / "manifest.json"
        if not manifest_path.exists():
            warnings.append("No manifest.json found - backup may be from an older version")
            # Create synthetic metadata
            metadata = {
                "backup_format_version": "unknown",
                "created_at": datetime.now(UTC).isoformat(),
                "created_by": "unknown",
                "db_size_bytes": 0,
                "avatar_count": 0,
                "checksum": "",
                "is_password_protected": is_encrypted,
            }
        else:
            with open(manifest_path) as f:
                manifest_data = json.load(f)

            # Determine format version
            format_version = manifest_data.get(
                "backup_format_version", manifest_data.get("version", "0.2.0")
            )

            metadata = {
                "backup_format_version": format_version,
                "created_at": manifest_data.get("created_at", datetime.now(UTC).isoformat()),
                "created_by": manifest_data.get("created_by", "unknown"),
                "db_size_bytes": manifest_data.get("db_size_bytes", 0),
                "avatar_count": manifest_data.get("avatar_count", 0),
                "checksum": manifest_data.get("checksum", ""),
                "is_password_protected": is_encrypted,
            }

            # Check for legacy secret_key (v0.2.0 format)
            if "secret_key" in manifest_data:
                metadata["has_legacy_secret_key"] = True
                warnings.append(
                    "This is a legacy backup (v0.2.0). Consider creating a new "
                    "password-protected backup for better security."
                )

        # Check database file
        db_path = backup_dir / "travel_manager.db"
        if not db_path.exists():
            return False, "No database file found in backup", None, []

        # Verify SQLite header
        with open(db_path, "rb") as f:
            header = f.read(16)
        if not header.startswith(b"SQLite format 3"):
            return False, "Database file is not a valid SQLite database", None, []

        # Update metadata with actual values
        metadata["db_size_bytes"] = db_path.stat().st_size
        avatar_dir = backup_dir / "avatars"
        metadata["avatar_count"] = len(list(avatar_dir.glob("*"))) if avatar_dir.exists() else 0

        # Check for integration configs (v0.2.1+)
        configs_path = backup_dir / "integration_configs.json"
        if configs_path.exists():
            with open(configs_path) as f:
                configs = json.load(f)
            metadata["integration_config_count"] = len(configs)
        else:
            metadata["integration_config_count"] = 0

        return True, "Backup is valid", metadata, warnings


def _run_migrations() -> tuple[bool, str]:
    """Run Alembic migrations programmatically.

    Returns: (success, message)
    """
    try:
        from alembic.config import Config

        from alembic import command

        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        return True, "Migrations completed successfully"
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False, f"Migration failed: {e!s}"


def _import_integration_configs(db_path: Path, configs: list[dict], admin_id: str) -> int:
    """Re-encrypt and import integration configs into the restored database.

    Args:
        db_path: Path to the restored database
        configs: List of config dicts with decrypted config_data
        admin_id: ID of the admin user to assign as created_by

    Returns:
        Number of configs imported
    """
    imported = 0
    conn = None
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Clear existing integration configs (encrypted with old SECRET_KEY)
        cursor.execute("DELETE FROM integration_configs")
        logger.info(f"Cleared existing integration configs from restored database")

        for config in configs:
            config_id = config.get("id", "unknown")
            config_type = config.get("integration_type", "unknown")

            if config.get("config_data") is None:
                logger.warning(
                    f"Skipping config {config_type} ({config_id}) - no config_data in backup"
                )
                continue

            try:
                # Re-encrypt with current SECRET_KEY
                encrypted = encrypt_config(config["config_data"])

                cursor.execute(
                    """
                    INSERT INTO integration_configs
                    (id, integration_type, name, config_encrypted, is_active, created_by,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        config["id"],
                        config["integration_type"],
                        config["name"],
                        encrypted,
                        config["is_active"],
                        admin_id,  # Use current admin instead of original created_by
                        config["created_at"],
                        config["updated_at"],
                    ),
                )
                imported += 1
                logger.info(f"Re-encrypted and imported config: {config_type}")
            except Exception as e:
                logger.error(
                    f"Failed to import config {config_type} ({config_id}): {e}"
                )
                continue

        conn.commit()
        logger.info(f"Successfully imported {imported}/{len(configs)} integration configs")
    except Exception as e:
        logger.error(f"Failed to import integration configs: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

    return imported


def _preserve_admin_user(db_path: Path, admin_data: dict) -> bool:
    """Preserve the current admin user after restore.

    This replaces all users in the restored database with just the current admin,
    and updates all foreign keys to point to this admin.

    Args:
        db_path: Path to the restored database
        admin_data: Dict with admin user fields (id, username, email, hashed_password, etc.)

    Returns:
        True if successful
    """
    conn = None
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        admin_id = admin_data["id"]
        admin_username = admin_data["username"]

        # Count users before deletion
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count_before = cursor.fetchone()[0]
        logger.info(
            f"Preserving current admin '{admin_username}', removing {user_count_before} users from backup"
        )

        # Delete all existing users from backup
        cursor.execute("DELETE FROM users")

        # Insert the current admin
        # Note: We include all required columns for schema compatibility
        cursor.execute(
            """
            INSERT INTO users (id, username, email, hashed_password, role, is_admin, is_active,
                               avatar_url, use_gravatar, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                admin_id,
                admin_username,
                admin_data["email"],
                admin_data["hashed_password"],
                "ADMIN",  # role - required field
                True,  # is_admin
                True,  # is_active
                admin_data.get("avatar_url"),
                admin_data.get("use_gravatar", True),
                admin_data.get("created_at", datetime.now(UTC).isoformat()),
                datetime.now(UTC).isoformat(),
            ),
        )

        # Update all foreign keys to point to current admin
        # Events
        cursor.execute("SELECT COUNT(*) FROM events")
        event_count = cursor.fetchone()[0]
        if event_count > 0:
            cursor.execute("UPDATE events SET user_id = ?", (admin_id,))
            logger.info(f"Updated {event_count} events to be owned by current admin")

        # Integration configs (created_by)
        cursor.execute("SELECT COUNT(*) FROM integration_configs")
        config_count = cursor.fetchone()[0]
        if config_count > 0:
            cursor.execute("UPDATE integration_configs SET created_by = ?", (admin_id,))
            logger.info(f"Updated {config_count} integration configs to be owned by current admin")

        # Clear all sessions (force re-login)
        cursor.execute("DELETE FROM sessions")
        logger.info("Cleared all sessions - users will need to re-login")

        conn.commit()
        logger.info(
            f"Successfully preserved admin user '{admin_username}' - restore complete"
        )
        return True
    except Exception as e:
        logger.error(f"Failed to preserve admin user: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


def _get_user_data(user_id: str) -> dict | None:
    """Get user data from the current database before restore."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
    except Exception as e:
        logger.error(f"Failed to get user data: {e}")
    return None


ENV_FILE_PATH = Path(".env")


def perform_restore(
    file_bytes: bytes,
    password: str | None = None,
    current_user_id: str | None = None,
) -> tuple[bool, str, dict]:
    """Perform the actual restore operation.

    Args:
        file_bytes: Raw backup file bytes
        password: Password for encrypted backups (required for v0.2.1+)
        current_user_id: ID of the current admin user to preserve

    Returns: (success, message, details)
        details includes: migrations_run, migrations_message, configs_imported
    """
    details = {
        "migrations_run": False,
        "migrations_message": "",
        "configs_imported": 0,
    }

    # Get current admin data before restore
    admin_data = None
    if current_user_id:
        admin_data = _get_user_data(current_user_id)
        if not admin_data:
            return False, "Failed to get current user data for preservation", details

    # Validate backup
    valid, message, metadata, _ = validate_backup(file_bytes, password)
    if not valid:
        return False, message, details

    is_encrypted = _is_encrypted_backup(file_bytes)

    # Decrypt if necessary
    if is_encrypted:
        if not password:
            return False, "Password required for encrypted backup", details
        salt, encrypted_data = _extract_salt_and_data(file_bytes)
        success, decrypted_bytes, error_msg = try_decrypt_backup(
            encrypted_data, password, salt
        )
        if not success:
            return False, error_msg, details
        file_bytes = decrypted_bytes

    # Create pre-restore backup (without password - internal use only)
    try:
        # Create a simple unencrypted backup for rollback purposes
        pre_backup_bytes = _create_unencrypted_backup("system_pre_restore")
        PRE_RESTORE_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        with open(PRE_RESTORE_BACKUP_DIR / f"pre_restore_{timestamp}.tar.gz", "wb") as f:
            f.write(pre_backup_bytes)
    except Exception as e:
        return False, f"Failed to create pre-restore backup: {e!s}", details

    # Extract and restore
    integration_configs = []
    with tempfile.TemporaryDirectory() as temp_dir:
        tarball_path = Path(temp_dir) / "upload.tar.gz"
        with open(tarball_path, "wb") as f:
            f.write(file_bytes)

        with tarfile.open(tarball_path, "r:gz") as tar:
            tar.extractall(temp_dir)

        subdirs = [d for d in Path(temp_dir).iterdir() if d.is_dir()]
        backup_dir = subdirs[0]

        # Load integration configs if present (v0.2.1+)
        configs_path = backup_dir / "integration_configs.json"
        if configs_path.exists():
            with open(configs_path) as f:
                integration_configs = json.load(f)

        # Handle legacy backup with secret_key (v0.2.0)
        manifest_path = backup_dir / "manifest.json"
        backup_secret_key = None
        if manifest_path.exists():
            with open(manifest_path) as f:
                manifest_data = json.load(f)
                backup_secret_key = manifest_data.get("secret_key")

        # Replace database
        src_db = backup_dir / "travel_manager.db"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_db, DB_PATH)

        # Replace avatars
        src_avatars = backup_dir / "avatars"
        if src_avatars.exists():
            if AVATAR_DIR.exists():
                shutil.rmtree(AVATAR_DIR)
            shutil.copytree(src_avatars, AVATAR_DIR)
        elif AVATAR_DIR.exists():
            # Backup had no avatars, clear existing
            shutil.rmtree(AVATAR_DIR)
            AVATAR_DIR.mkdir(parents=True, exist_ok=True)

    # Run migrations
    migration_success, migration_msg = _run_migrations()
    details["migrations_run"] = migration_success
    details["migrations_message"] = migration_msg

    # Import integration configs (v0.2.1+)
    # Backup no longer contains users, so we just need to re-encrypt configs
    # and update foreign keys to point to current admin
    if integration_configs and admin_data:
        logger.info(f"Re-encrypting and importing {len(integration_configs)} integration configs")
        details["configs_imported"] = _import_integration_configs(
            DB_PATH, integration_configs, admin_data["id"]
        )
        if details["configs_imported"] != len(integration_configs):
            logger.warning(
                f"Only imported {details['configs_imported']} of {len(integration_configs)} configs"
            )
    elif backup_secret_key:
        # Legacy backup - update .env with the old secret key so configs remain readable
        _update_env_secret_key(backup_secret_key)
        details["migrations_message"] += (
            " Note: Legacy backup restored with original SECRET_KEY. "
            "Consider creating a new password-protected backup."
        )

    # Re-insert current admin and update foreign keys
    # Backup has no users (cleared during backup creation), so we need to:
    # 1. Insert the current admin user into the restored database
    # 2. Update all foreign keys to point to this admin
    if admin_data:
        try:
            admin_id = admin_data["id"]
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()

            # Insert current admin into the restored database
            cursor.execute(
                """
                INSERT INTO users (id, username, email, hashed_password, role, is_admin, is_active,
                                   full_name, avatar_url, use_gravatar, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    admin_id,
                    admin_data["username"],
                    admin_data["email"],
                    admin_data["hashed_password"],
                    admin_data.get("role", "ADMIN"),
                    True,  # is_admin
                    True,  # is_active
                    admin_data.get("full_name"),
                    admin_data.get("avatar_url"),
                    admin_data.get("use_gravatar", True),
                    admin_data.get("created_at", datetime.now(UTC).isoformat()),
                    datetime.now(UTC).isoformat(),
                ),
            )
            logger.info(f"Inserted current admin '{admin_data['username']}' into restored database")

            # Update events to be owned by current admin
            cursor.execute("UPDATE events SET user_id = ?", (admin_id,))
            event_count = cursor.rowcount
            logger.info(f"Updated {event_count} events to be owned by current admin")

            # Update integration configs ownership
            cursor.execute("UPDATE integration_configs SET created_by = ?", (admin_id,))
            config_count = cursor.rowcount
            logger.info(f"Updated {config_count} integration configs ownership")

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to restore admin user: {e}")
            return (
                False,
                f"Restore failed: could not restore admin user: {e}",
                details,
            )

    return True, "Restore completed. Please restart the application to apply changes.", details


def _create_unencrypted_backup(username: str) -> bytes:
    """Create an unencrypted backup for internal use (pre-restore backup)."""
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_name = f"travel_manager_backup_{timestamp}"

    with tempfile.TemporaryDirectory() as temp_dir:
        backup_dir = Path(temp_dir) / backup_name
        backup_dir.mkdir()

        # Safe SQLite backup
        if DB_PATH.exists():
            dest_db = backup_dir / "travel_manager.db"
            conn = sqlite3.connect(str(DB_PATH))
            backup_conn = sqlite3.connect(str(dest_db))
            conn.backup(backup_conn)
            conn.close()
            backup_conn.close()

        # Copy avatars
        if AVATAR_DIR.exists() and any(AVATAR_DIR.iterdir()):
            shutil.copytree(AVATAR_DIR, backup_dir / "avatars")

        # Create manifest
        db_file = backup_dir / "travel_manager.db"
        db_size = db_file.stat().st_size if db_file.exists() else 0
        avatar_dir = backup_dir / "avatars"
        avatar_count = len(list(avatar_dir.glob("*"))) if avatar_dir.exists() else 0

        checksum = ""
        if db_file.exists():
            with open(db_file, "rb") as f:
                checksum = hashlib.sha256(f.read()).hexdigest()

        manifest = {
            "backup_format_version": BACKUP_FORMAT_VERSION,
            "created_at": datetime.now(UTC).isoformat(),
            "created_by": username,
            "db_size_bytes": db_size,
            "avatar_count": avatar_count,
            "checksum": checksum,
            "internal_backup": True,
        }

        with open(backup_dir / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        # Create tarball
        tarball_path = Path(temp_dir) / f"{backup_name}.tar.gz"
        with tarfile.open(tarball_path, "w:gz") as tar:
            tar.add(backup_dir, arcname=backup_name)

        with open(tarball_path, "rb") as f:
            return f.read()


def _update_env_secret_key(new_secret_key: str) -> None:
    """Update or create the SECRET_KEY in the .env file."""
    env_content = ""
    if ENV_FILE_PATH.exists():
        env_content = ENV_FILE_PATH.read_text()

    # Parse existing .env content
    lines = env_content.splitlines() if env_content else []
    new_lines = []
    secret_key_found = False

    for line in lines:
        if line.strip().startswith("SECRET_KEY="):
            new_lines.append(f"SECRET_KEY={new_secret_key}")
            secret_key_found = True
        else:
            new_lines.append(line)

    if not secret_key_found:
        new_lines.append(f"SECRET_KEY={new_secret_key}")

    ENV_FILE_PATH.write_text("\n".join(new_lines) + "\n")
