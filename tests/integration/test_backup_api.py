# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Integration tests for backup API endpoints."""

import io
import shutil
import sqlite3
import tarfile
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.services import backup_service
from src.services.backup_encryption import decrypt_backup_archive

# Test password used for all backup tests
TEST_PASSWORD = "test_password_123"


@pytest.fixture
def temp_backup_dirs(admin_user):
    """Create temporary directories for backup testing."""
    temp_dir = tempfile.mkdtemp()
    data_dir = Path(temp_dir) / "data"
    data_dir.mkdir()
    avatar_dir = Path(temp_dir) / "static" / "avatars"
    avatar_dir.mkdir(parents=True)

    # Create a test database with required tables
    db_path = data_dir / "travel_manager.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO test VALUES (1, 'test')")
    # Create tables needed for backup service
    conn.execute(
        """CREATE TABLE IF NOT EXISTS integration_configs (
            id TEXT PRIMARY KEY,
            integration_type TEXT,
            name TEXT,
            config_encrypted TEXT,
            is_active INTEGER,
            created_by TEXT,
            created_at TEXT,
            updated_at TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT,
            email TEXT,
            hashed_password TEXT,
            role TEXT DEFAULT 'USER',
            is_admin INTEGER,
            is_active INTEGER,
            full_name TEXT,
            avatar_url TEXT,
            use_gravatar INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS companies (
            id TEXT PRIMARY KEY,
            name TEXT,
            type TEXT,
            paperless_storage_path_id INTEGER,
            report_recipients TEXT,
            webpage TEXT,
            address TEXT,
            country TEXT,
            logo_path TEXT,
            created_at TEXT,
            updated_at TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS company_contacts (
            id TEXT PRIMARY KEY,
            company_id TEXT,
            name TEXT,
            email TEXT,
            phone TEXT,
            title TEXT,
            department TEXT,
            notes TEXT,
            contact_types TEXT DEFAULT '[]',
            is_main_contact INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY(company_id) REFERENCES companies(id)
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS email_templates (
            id TEXT PRIMARY KEY,
            name TEXT,
            reason TEXT,
            company_id TEXT,
            subject TEXT,
            body_html TEXT,
            body_text TEXT,
            is_default INTEGER DEFAULT 0,
            contact_types TEXT DEFAULT '[]',
            created_at TEXT,
            updated_at TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            user_id TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS alembic_version (
            version_num TEXT PRIMARY KEY
        )"""
    )
    # Insert current migration version to prevent migrations from running
    conn.execute("INSERT INTO alembic_version (version_num) VALUES ('3a8f2c9d1e5b')")

    # Insert the admin user into the temp database so restore can find them
    conn.execute(
        """INSERT INTO users (id, username, email, hashed_password, role, is_admin, is_active,
                             full_name, avatar_url, use_gravatar, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            str(admin_user.id),
            admin_user.username,
            admin_user.email,
            admin_user.hashed_password,
            "ADMIN",  # role
            1,  # is_admin
            1,  # is_active
            admin_user.full_name,
            admin_user.avatar_url,
            1 if admin_user.use_gravatar else 0,
            str(admin_user.created_at) if admin_user.created_at else None,
            str(admin_user.updated_at) if admin_user.updated_at else None,
        ),
    )

    conn.commit()
    conn.close()

    # Create some test avatar files
    (avatar_dir / "avatar1.jpg").write_bytes(b"fake image 1")

    yield temp_dir, data_dir, avatar_dir, db_path

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_backup_paths(temp_backup_dirs):
    """Mock the backup service paths for API tests."""
    temp_dir, data_dir, avatar_dir, db_path = temp_backup_dirs

    with (
        patch.object(backup_service, "DATA_DIR", data_dir),
        patch.object(backup_service, "AVATAR_DIR", avatar_dir),
        patch.object(backup_service, "DB_PATH", db_path),
        patch.object(
            backup_service,
            "PRE_RESTORE_BACKUP_DIR",
            Path(temp_dir) / "backups" / "pre_restore",
        ),
    ):
        yield temp_dir, data_dir, avatar_dir, db_path


class TestBackupInfoEndpoint:
    """Tests for GET /api/v1/backup/info endpoint."""

    def test_requires_authentication(self, client):
        """Test that endpoint requires authentication."""
        response = client.get("/api/v1/backup/info")
        assert response.status_code == 401

    def test_requires_admin(self, authenticated_client):
        """Test that endpoint requires admin role."""
        response = authenticated_client.get("/api/v1/backup/info")
        assert response.status_code == 403

    def test_returns_backup_info(self, admin_client, mock_backup_paths):
        """Test that endpoint returns backup information."""
        response = admin_client.get("/api/v1/backup/info")

        assert response.status_code == 200
        data = response.json()
        assert "database_exists" in data
        assert "database_size_bytes" in data
        assert "avatar_count" in data
        assert data["database_exists"] is True
        assert data["avatar_count"] == 1


class TestCreateBackupEndpoint:
    """Tests for POST /api/v1/backup/create endpoint."""

    def test_requires_authentication(self, client):
        """Test that endpoint requires authentication."""
        response = client.post(
            "/api/v1/backup/create",
            json={"password": TEST_PASSWORD},
        )
        assert response.status_code == 401

    def test_requires_admin(self, authenticated_client):
        """Test that endpoint requires admin role."""
        response = authenticated_client.post(
            "/api/v1/backup/create",
            json={"password": TEST_PASSWORD},
        )
        assert response.status_code == 403

    def test_creates_and_downloads_backup(self, admin_client, mock_backup_paths):
        """Test that endpoint creates and returns a backup file."""
        response = admin_client.post(
            "/api/v1/backup/create",
            json={"password": TEST_PASSWORD},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"
        assert "content-disposition" in response.headers
        assert "attachment" in response.headers["content-disposition"]
        assert ".tar.gz.enc" in response.headers["content-disposition"]

        # Decrypt and verify it's a valid tarball
        content = response.content
        salt = content[:16]
        encrypted_data = content[16:]
        decrypted = decrypt_backup_archive(encrypted_data, TEST_PASSWORD, salt)

        with tarfile.open(fileobj=io.BytesIO(decrypted), mode="r:gz") as tar:
            names = tar.getnames()
            assert any("homeoffice_assistant.db" in name for name in names)
            assert any("manifest.json" in name for name in names)

    def test_rejects_short_password(self, admin_client, mock_backup_paths):
        """Test that short passwords are rejected."""
        response = admin_client.post(
            "/api/v1/backup/create",
            json={"password": "short"},
        )

        assert response.status_code == 422  # Validation error


class TestValidateBackupEndpoint:
    """Tests for POST /api/v1/backup/validate endpoint."""

    def test_requires_authentication(self, client, mock_backup_paths):
        """Test that endpoint requires authentication."""
        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)
        response = client.post(
            "/api/v1/backup/validate",
            files={
                "file": (
                    "backup.tar.gz.enc",
                    io.BytesIO(backup_bytes),
                    "application/octet-stream",
                )
            },
            data={"password": TEST_PASSWORD},
        )
        assert response.status_code == 401

    def test_requires_admin(self, authenticated_client, mock_backup_paths):
        """Test that endpoint requires admin role."""
        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)
        response = authenticated_client.post(
            "/api/v1/backup/validate",
            files={
                "file": (
                    "backup.tar.gz.enc",
                    io.BytesIO(backup_bytes),
                    "application/octet-stream",
                )
            },
            data={"password": TEST_PASSWORD},
        )
        assert response.status_code == 403

    def test_validates_valid_backup(self, admin_client, mock_backup_paths):
        """Test validation of a valid backup file."""
        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)
        response = admin_client.post(
            "/api/v1/backup/validate",
            files={
                "file": (
                    "backup.tar.gz.enc",
                    io.BytesIO(backup_bytes),
                    "application/octet-stream",
                )
            },
            data={"password": TEST_PASSWORD},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["metadata"] is not None
        assert data["metadata"]["backup_format_version"] == "0.2.2"
        assert data["metadata"]["is_password_protected"] is True

    def test_rejects_invalid_backup(self, admin_client, mock_backup_paths):
        """Test rejection of invalid backup file."""
        response = admin_client.post(
            "/api/v1/backup/validate",
            files={
                "file": (
                    "backup.tar.gz",
                    io.BytesIO(b"invalid data"),
                    "application/gzip",
                )
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False

    def test_requires_password_for_encrypted_backup(
        self, admin_client, mock_backup_paths
    ):
        """Test that password is required for encrypted backups."""
        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)
        response = admin_client.post(
            "/api/v1/backup/validate",
            files={
                "file": (
                    "backup.tar.gz.enc",
                    io.BytesIO(backup_bytes),
                    "application/octet-stream",
                )
            },
            # No password provided
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "password" in data["message"].lower()
        assert data["metadata"]["is_password_protected"] is True


class TestRestoreBackupEndpoint:
    """Tests for POST /api/v1/backup/restore endpoint."""

    def test_requires_authentication(self, client, mock_backup_paths):
        """Test that endpoint requires authentication."""
        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)
        response = client.post(
            "/api/v1/backup/restore",
            files={
                "file": (
                    "backup.tar.gz.enc",
                    io.BytesIO(backup_bytes),
                    "application/octet-stream",
                )
            },
            data={"password": TEST_PASSWORD},
        )
        assert response.status_code == 401

    def test_requires_admin(self, authenticated_client, mock_backup_paths):
        """Test that endpoint requires admin role."""
        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)
        response = authenticated_client.post(
            "/api/v1/backup/restore",
            files={
                "file": (
                    "backup.tar.gz.enc",
                    io.BytesIO(backup_bytes),
                    "application/octet-stream",
                )
            },
            data={"password": TEST_PASSWORD},
        )
        assert response.status_code == 403

    def test_restores_valid_backup(self, admin_client, mock_backup_paths):
        """Test restore of a valid backup file."""
        backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)
        response = admin_client.post(
            "/api/v1/backup/restore",
            files={
                "file": (
                    "backup.tar.gz.enc",
                    io.BytesIO(backup_bytes),
                    "application/octet-stream",
                )
            },
            data={"password": TEST_PASSWORD},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True, f"Restore failed: {data}"
        assert data["requires_restart"] is True
        assert "restart" in data["message"].lower()
        assert "migrations_run" in data
        assert "configs_imported" in data

    def test_rejects_invalid_backup(self, admin_client, mock_backup_paths):
        """Test rejection of invalid backup during restore."""
        response = admin_client.post(
            "/api/v1/backup/restore",
            files={
                "file": (
                    "backup.tar.gz",
                    io.BytesIO(b"invalid data"),
                    "application/gzip",
                )
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["requires_restart"] is False
