# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for backup service."""

import io
import json
import os
import shutil
import sqlite3
import tarfile
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from alembic import command
from src.config import settings
from src.services import backup_restore, backup_service, file_storage_service
from src.services.backup_encryption import (
    decrypt_backup_archive,
    encrypt_backup_archive,
)

# Test password used for all backup tests
TEST_PASSWORD = "test_password_123"


@pytest.fixture(scope="module")
def migrated_db_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build a database with the real schema by running ``alembic upgrade head``.

    A restore migrates the backup to the current head before swapping it in,
    so the fixture needs an alembic-built schema. Built once per module.
    """
    template = tmp_path_factory.mktemp("backup-unit-template") / "template.db"
    command.upgrade(backup_restore.core_alembic_config(f"sqlite:///{template}"), "head")
    return template


@pytest.fixture
def temp_data_dir(migrated_db_template: Path):
    """Create a data dir with a migrated database plus a marker table."""
    temp_dir = tempfile.mkdtemp()
    data_dir = Path(temp_dir) / "data"
    data_dir.mkdir()
    avatar_dir = Path(temp_dir) / "static" / "avatars"
    avatar_dir.mkdir(parents=True)
    logo_dir = data_dir / "logos"
    logo_dir.mkdir()
    (logo_dir / "company1.png").write_bytes(b"fake logo 1")

    db_path = data_dir / "travel_manager.db"
    shutil.copy2(migrated_db_template, db_path)
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO test VALUES (1, 'test')")
    conn.commit()
    conn.close()

    # Create some test avatar files
    (avatar_dir / "avatar1.jpg").write_bytes(b"fake image 1")
    (avatar_dir / "avatar2.png").write_bytes(b"fake image 2")

    yield temp_dir, data_dir, avatar_dir, db_path

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_paths(temp_data_dir):
    """Mock the backup service paths.

    The avatar and logo directories are patched where the service reads them,
    so no test touches the real data/logos or static/avatars.
    """
    temp_dir, data_dir, avatar_dir, db_path = temp_data_dir

    with (
        patch.object(backup_service, "DATA_DIR", data_dir),
        patch.object(file_storage_service, "AVATAR_DIR", avatar_dir),
        patch.object(file_storage_service, "LOGO_DIR", data_dir / "logos"),
        patch.object(backup_service, "DB_PATH", db_path),
        patch.object(
            backup_service,
            "PRE_RESTORE_BACKUP_DIR",
            Path(temp_dir) / "backups" / "pre_restore",
        ),
    ):
        yield temp_dir, data_dir, avatar_dir, db_path


class TestGetBackupInfo:
    """Tests for get_backup_info function."""

    def test_returns_correct_info(self, mock_paths):
        """Test that get_backup_info returns correct data."""
        info = backup_service.get_backup_info()

        assert info["database_exists"] is True
        assert info["database_size_bytes"] > 0
        assert info["avatar_count"] == 2

    def test_handles_missing_database(self, mock_paths):
        """Test handling when database doesn't exist."""
        _, _, _, db_path = mock_paths
        os.remove(db_path)

        info = backup_service.get_backup_info()

        assert info["database_exists"] is False
        assert info["database_size_bytes"] == 0

    def test_handles_missing_avatar_dir(self, mock_paths):
        """Test handling when avatar directory doesn't exist."""
        _, _, avatar_dir, _ = mock_paths
        shutil.rmtree(avatar_dir)

        info = backup_service.get_backup_info()

        assert info["avatar_count"] == 0


class TestCreateBackup:
    """Tests for create_backup function."""

    def test_creates_valid_encrypted_tarball(self, mock_paths):
        """Test that create_backup creates a valid encrypted tarball."""
        backup_bytes, filename = backup_service.create_backup("testuser", TEST_PASSWORD)

        assert filename.startswith("homeoffice_assistant_backup_")
        assert filename.endswith(".tar.gz.enc")
        assert len(backup_bytes) > 0

    def test_tarball_contains_database(self, mock_paths):
        """Test that tarball contains the database file."""
        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)

        # Decrypt backup
        salt = backup_bytes[:16]
        encrypted_data = backup_bytes[16:]
        decrypted = decrypt_backup_archive(encrypted_data, TEST_PASSWORD, salt)

        with tempfile.TemporaryDirectory() as temp_dir:
            tarball_path = Path(temp_dir) / "backup.tar.gz"
            with open(tarball_path, "wb") as f:
                f.write(decrypted)

            with tarfile.open(tarball_path, "r:gz") as tar:
                names = tar.getnames()
                assert any("homeoffice_assistant.db" in name for name in names)
        """Test that tarball contains the database file."""
        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)

        # Decrypt backup
        salt = backup_bytes[:16]
        encrypted_data = backup_bytes[16:]
        decrypted = decrypt_backup_archive(encrypted_data, TEST_PASSWORD, salt)

        with tempfile.TemporaryDirectory() as temp_dir:
            tarball_path = Path(temp_dir) / "backup.tar.gz"
            with open(tarball_path, "wb") as f:
                f.write(decrypted)

            with tarfile.open(tarball_path, "r:gz") as tar:
                names = tar.getnames()
                assert any("homeoffice_assistant.db" in name for name in names)

    def test_tarball_contains_manifest(self, mock_paths):
        """Test that tarball contains manifest.json."""
        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)

        # Decrypt backup
        salt = backup_bytes[:16]
        encrypted_data = backup_bytes[16:]
        decrypted = decrypt_backup_archive(encrypted_data, TEST_PASSWORD, salt)

        with tempfile.TemporaryDirectory() as temp_dir:
            tarball_path = Path(temp_dir) / "backup.tar.gz"
            with open(tarball_path, "wb") as f:
                f.write(decrypted)

            with tarfile.open(tarball_path, "r:gz") as tar:
                names = tar.getnames()
                assert any("manifest.json" in name for name in names)

    def test_manifest_contains_correct_data(self, mock_paths):
        """Test that manifest contains correct metadata."""
        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)

        # Decrypt backup
        salt = backup_bytes[:16]
        encrypted_data = backup_bytes[16:]
        decrypted = decrypt_backup_archive(encrypted_data, TEST_PASSWORD, salt)

        with tempfile.TemporaryDirectory() as temp_dir:
            tarball_path = Path(temp_dir) / "backup.tar.gz"
            with open(tarball_path, "wb") as f:
                f.write(decrypted)

            with tarfile.open(tarball_path, "r:gz") as tar:
                tar.extractall(temp_dir, filter="data")

            # Find manifest
            for root, _, files in os.walk(temp_dir):
                if "manifest.json" in files:
                    with open(Path(root) / "manifest.json") as f:
                        manifest = json.load(f)
                    break

            assert manifest["backup_format_version"] == "0.2.2"
            assert manifest["created_by"] == "testuser"
            assert manifest["db_size_bytes"] > 0
            assert manifest["avatar_count"] == 2
            assert "checksum" in manifest
            # Secret key should NOT be in manifest (password-protected backup)
            assert "secret_key" not in manifest

    def test_tarball_contains_avatars(self, mock_paths):
        """Test that tarball contains avatar files."""
        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)

        # Decrypt backup
        salt = backup_bytes[:16]
        encrypted_data = backup_bytes[16:]
        decrypted = decrypt_backup_archive(encrypted_data, TEST_PASSWORD, salt)

        with tempfile.TemporaryDirectory() as temp_dir:
            tarball_path = Path(temp_dir) / "backup.tar.gz"
            with open(tarball_path, "wb") as f:
                f.write(decrypted)

            with tarfile.open(tarball_path, "r:gz") as tar:
                names = tar.getnames()
                assert any("avatars" in name for name in names)

    def test_tarball_contains_integration_configs(self, mock_paths):
        """Test that tarball contains integration_configs.json."""
        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)

        # Decrypt backup
        salt = backup_bytes[:16]
        encrypted_data = backup_bytes[16:]
        decrypted = decrypt_backup_archive(encrypted_data, TEST_PASSWORD, salt)

        with tempfile.TemporaryDirectory() as temp_dir:
            tarball_path = Path(temp_dir) / "backup.tar.gz"
            with open(tarball_path, "wb") as f:
                f.write(decrypted)

            with tarfile.open(tarball_path, "r:gz") as tar:
                names = tar.getnames()
                assert any("integration_configs.json" in name for name in names)

    def test_tarball_contains_logos(self, mock_paths):
        """The company logos are packed as logos/<file>."""
        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)

        names = tar_names(decrypt(backup_bytes))

        assert any(name.endswith("/logos/company1.png") for name in names)


class TestValidateBackup:
    """Tests for validate_backup function."""

    def test_validates_valid_backup(self, mock_paths):
        """Test validation of a valid backup."""
        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)

        valid, message, metadata, _ = backup_service.validate_backup(
            backup_bytes, TEST_PASSWORD
        )

        assert valid is True
        assert "valid" in message.lower()
        assert metadata is not None
        assert metadata["backup_format_version"] == "0.2.2"
        assert metadata["is_password_protected"] is True

    def test_rejects_invalid_tarball(self, mock_paths):
        """Test rejection of invalid tarball data."""
        valid, _, _, _ = backup_service.validate_backup(b"not a tarball")

        assert valid is False

    def test_rejects_empty_archive(self, mock_paths):
        """Test rejection of empty archive."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tarball_path = Path(temp_dir) / "empty.tar.gz"
            with tarfile.open(tarball_path, "w:gz"):
                pass  # Create empty tarball

            with open(tarball_path, "rb") as f:
                backup_bytes = f.read()

        valid, _, _, _ = backup_service.validate_backup(backup_bytes)

        assert valid is False

    def test_rejects_missing_database(self, mock_paths):
        """Test rejection when database file is missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir) / "homeoffice_assistant_backup_test"
            backup_dir.mkdir()

            # Create manifest but no database
            with open(backup_dir / "manifest.json", "w") as f:
                json.dump({"version": "0.1.1"}, f)

            tarball_path = Path(temp_dir) / "backup.tar.gz"
            with tarfile.open(tarball_path, "w:gz") as tar:
                tar.add(backup_dir, arcname="homeoffice_assistant_backup_test")

            with open(tarball_path, "rb") as f:
                backup_bytes = f.read()

        valid, message, _, _ = backup_service.validate_backup(backup_bytes)

        assert valid is False
        assert "database" in message.lower()

    def test_rejects_invalid_sqlite(self, mock_paths):
        """Test rejection when database is not valid SQLite."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir) / "homeoffice_assistant_backup_test"
            backup_dir.mkdir()

            # Create manifest and fake database
            with open(backup_dir / "manifest.json", "w") as f:
                json.dump({"version": "0.1.1"}, f)
            with open(backup_dir / "homeoffice_assistant.db", "w") as f:
                f.write("not a sqlite database")

            tarball_path = Path(temp_dir) / "backup.tar.gz"
            with tarfile.open(tarball_path, "w:gz") as tar:
                tar.add(backup_dir, arcname="homeoffice_assistant_backup_test")

            with open(tarball_path, "rb") as f:
                backup_bytes = f.read()

        valid, message, _, _ = backup_service.validate_backup(backup_bytes)

        assert valid is False
        assert "sqlite" in message.lower()

    def test_warns_missing_manifest(self, mock_paths):
        """Test warning when manifest is missing."""
        _, _, _, db_path = mock_paths

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir) / "homeoffice_assistant_backup_test"
            backup_dir.mkdir()

            # Copy database but no manifest
            shutil.copy(db_path, backup_dir / "homeoffice_assistant.db")

            tarball_path = Path(temp_dir) / "backup.tar.gz"
            with tarfile.open(tarball_path, "w:gz") as tar:
                tar.add(backup_dir, arcname="homeoffice_assistant_backup_test")

            with open(tarball_path, "rb") as f:
                backup_bytes = f.read()

        valid, _, _, warnings = backup_service.validate_backup(backup_bytes)

        assert valid is True
        assert len(warnings) > 0
        assert any("manifest" in w.lower() for w in warnings)

    def test_requires_password_for_encrypted_backup(self, mock_paths):
        """Test that password is required for encrypted backups."""
        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)

        # Try to validate without password
        valid, message, metadata, _ = backup_service.validate_backup(backup_bytes)

        assert valid is False
        assert "password" in message.lower()
        assert metadata is not None
        assert metadata["is_password_protected"] is True

    def test_rejects_wrong_password(self, mock_paths):
        """Test rejection of wrong password."""
        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)

        valid, message, _, _ = backup_service.validate_backup(
            backup_bytes, "wrong_password"
        )

        assert valid is False
        assert "invalid" in message.lower() or "password" in message.lower()


class TestPerformRestore:
    """Tests for perform_restore function."""

    def test_restores_database(self, mock_paths):
        """Test that restore replaces the database."""
        _, _, _, db_path = mock_paths

        # Create a backup
        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)

        # Modify the current database
        conn = sqlite3.connect(str(db_path))
        conn.execute("INSERT INTO test VALUES (2, 'modified')")
        conn.commit()
        conn.close()

        # Verify modification
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT COUNT(*) FROM test")
        count_before = cursor.fetchone()[0]
        conn.close()
        assert count_before == 2

        # Perform restore
        success, _, details = backup_service.perform_restore(
            backup_bytes, password=TEST_PASSWORD
        )

        assert success is True
        assert "migrations_run" in details

        # Verify database was restored
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT COUNT(*) FROM test")
        count_after = cursor.fetchone()[0]
        conn.close()
        assert count_after == 1  # Back to original

    def test_creates_pre_restore_backup(self, mock_paths):
        """Test that pre-restore backup is created."""
        temp_dir, _, _, _ = mock_paths
        pre_restore_dir = Path(temp_dir) / "backups" / "pre_restore"

        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)
        success, _, _ = backup_service.perform_restore(
            backup_bytes, password=TEST_PASSWORD
        )

        assert success is True
        assert pre_restore_dir.exists()
        pre_restore_files = list(pre_restore_dir.glob("*.tar.gz"))
        assert len(pre_restore_files) == 1

    def test_migrates_outside_the_project_directory(
        self, mock_paths, tmp_path, monkeypatch
    ):
        """The core upgrade finds the migrations from any working directory."""
        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)
        monkeypatch.chdir(tmp_path)

        success, message, details = backup_service.perform_restore(
            backup_bytes, password=TEST_PASSWORD
        )

        assert success is True, message
        assert details["migrations_run"] is True

    def test_rejects_invalid_backup(self, mock_paths):
        """Test rejection of invalid backup during restore."""
        success, _, _ = backup_service.perform_restore(b"invalid data")

        assert success is False

    def test_restores_avatars(self, mock_paths):
        """Test that avatars are restored."""
        _, _, avatar_dir, _ = mock_paths

        # Create a backup
        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)

        # Delete current avatars
        for f in avatar_dir.iterdir():
            f.unlink()

        # Add a new avatar that shouldn't exist after restore
        (avatar_dir / "new_avatar.jpg").write_bytes(b"new avatar")

        # Perform restore
        success, _, _ = backup_service.perform_restore(
            backup_bytes, password=TEST_PASSWORD
        )

        assert success is True

        # Verify avatars were restored
        avatar_files = list(avatar_dir.glob("*"))
        assert len(avatar_files) == 2
        assert not (avatar_dir / "new_avatar.jpg").exists()

    def test_restores_logos(self, mock_paths):
        """The logo directory ends up holding exactly the archive's logos."""
        logo_dir = file_storage_service.LOGO_DIR
        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)
        (logo_dir / "company1.png").unlink()
        (logo_dir / "new_logo.png").write_bytes(b"new logo")

        success, message, _ = backup_service.perform_restore(
            backup_bytes, password=TEST_PASSWORD
        )

        assert success is True, message
        assert sorted(p.name for p in logo_dir.iterdir()) == ["company1.png"]
        assert (logo_dir / "company1.png").read_bytes() == b"fake logo 1"

    def test_archive_without_logos_keeps_current_logos(self, mock_paths, tmp_path):
        """An archive made before logos were backed up leaves the logos alone."""
        logo_dir = file_storage_service.LOGO_DIR
        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)
        old_bytes = without_logos(decrypt(backup_bytes), tmp_path)
        assert not any("/logos" in name for name in tar_names(old_bytes))
        encrypted, salt = encrypt_backup_archive(old_bytes, TEST_PASSWORD)
        (logo_dir / "current.png").write_bytes(b"current logo")

        success, message, _ = backup_service.perform_restore(
            salt + encrypted, password=TEST_PASSWORD
        )

        assert success is True, message
        assert sorted(p.name for p in logo_dir.iterdir()) == [
            "company1.png",
            "current.png",
        ]

    def test_requires_password_for_encrypted_backup(self, mock_paths):
        """Test that password is required for encrypted backups."""
        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)

        # Try to restore without password
        success, message, _ = backup_service.perform_restore(backup_bytes)

        assert success is False
        assert "password" in message.lower()


class TestBackupEncryption:
    """Tests for backup encryption functionality."""

    def test_decrypt_with_correct_password(self, mock_paths):
        """Test decryption with correct password."""
        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)

        salt = backup_bytes[:16]
        encrypted_data = backup_bytes[16:]
        decrypted = decrypt_backup_archive(encrypted_data, TEST_PASSWORD, salt)

        # Should be valid gzip data
        assert decrypted[:2] == b"\x1f\x8b"

    def test_decrypt_with_wrong_password_fails(self, mock_paths):
        """Test that decryption with wrong password fails."""
        from cryptography.fernet import InvalidToken

        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)

        salt = backup_bytes[:16]
        encrypted_data = backup_bytes[16:]

        with pytest.raises(InvalidToken):
            decrypt_backup_archive(encrypted_data, "wrong_password", salt)


def test_pre_restore_dir_lives_under_the_data_dir(tmp_path: Path) -> None:
    """Pre-restore archives go to the data volume, not the container layer."""
    assert backup_service.pre_restore_dir_for(tmp_path) == (
        tmp_path / "backups" / "pre_restore"
    )
    assert (
        backup_service.pre_restore_dir_for(backup_service.DATA_DIR)
    ) == backup_service.PRE_RESTORE_BACKUP_DIR


def test_upgrade_core_leaves_settings_alone(tmp_path: Path) -> None:
    """The core upgrade reaches head without repointing the settings URL."""
    db_path = tmp_path / "fresh.db"
    configured_url = settings.database_url
    seen: list[str] = []
    upgrade = command.upgrade

    def recording_upgrade(config, revision: str) -> None:
        seen.append(settings.database_url)
        upgrade(config, revision)
        seen.append(settings.database_url)

    with patch.object(backup_restore.command, "upgrade", recording_upgrade):
        backup_restore.upgrade_core(db_path)

    assert seen == [configured_url, configured_url]
    head = ScriptDirectory.from_config(
        backup_restore.core_alembic_config()
    ).get_current_head()
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        with engine.connect() as conn:
            current = MigrationContext.configure(conn).get_current_revision()
    finally:
        engine.dispose()
    assert current == head


def decrypt(backup_bytes: bytes) -> bytes:
    """Return the tar.gz bytes of a backup made by ``create_backup``."""
    return decrypt_backup_archive(backup_bytes[16:], TEST_PASSWORD, backup_bytes[:16])


def tar_names(tar_bytes: bytes) -> list[str]:
    """List the member names of a tar.gz archive."""
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tar:
        return tar.getnames()


def without_logos(tar_bytes: bytes, work: Path) -> bytes:
    """Rebuild an archive without its logos/ members, like an older backup."""
    source = work / "with_logos.tar.gz"
    source.write_bytes(tar_bytes)
    target = work / "without_logos.tar.gz"
    with (
        tarfile.open(source, "r:gz") as old,
        tarfile.open(target, "w:gz") as new,
    ):
        for member in old.getmembers():
            if "/logos" in member.name:
                continue
            new.addfile(member, old.extractfile(member) if member.isfile() else None)
    return target.read_bytes()


def test_try_decrypt_unexpected_error_hides_raw_text():
    """An unexpected decryption failure reports no library exception text."""
    from src.services.backup_encryption import try_decrypt_backup

    with patch(
        "src.services.backup_encryption.decrypt_backup_archive",
        side_effect=RuntimeError("secret internals"),
    ):
        ok, data, message = try_decrypt_backup(b"x", "pw", b"salt")

    assert ok is False
    assert data is None
    assert message == "Decryption error, see server log"
