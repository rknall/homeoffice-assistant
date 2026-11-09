# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Integration tests for backup API endpoints."""

import io
import shutil
import tarfile
import tempfile
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import Session

from alembic import command
from src.encryption import decrypt_config, encrypt_config
from src.models import (
    Base,
    Company,
    Event,
    HolidayCalendar,
    IntegrationConfig,
    Role,
    TodoTemplate,
    User,
    UserRole,
)
from src.models import Session as UserSession
from src.models.enums import CompanyType, IntegrationType
from src.rbac.roles import GLOBAL_ADMIN_ROLE, MEMBER_ROLE
from src.security import get_password_hash
from src.services import backup_restore, backup_service, file_storage_service
from src.services.backup_encryption import decrypt_backup_archive

# Test password used for all backup tests
TEST_PASSWORD = "test_password_123"


@pytest.fixture(scope="module")
def migrated_db_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build a database with the real schema by running ``alembic upgrade head``.

    Built once per module and copied for each test.
    """
    template = tmp_path_factory.mktemp("backup-template") / "template.db"
    command.upgrade(backup_restore.core_alembic_config(f"sqlite:///{template}"), "head")
    return template


@pytest.fixture
def temp_backup_dirs(
    admin_user: User, migrated_db_template: Path
) -> Generator[tuple[str, Path, Path, Path]]:
    """Create a data dir whose database holds the migrated schema and the admin."""
    temp_dir = tempfile.mkdtemp()
    data_dir = Path(temp_dir) / "data"
    data_dir.mkdir()
    logo_dir = data_dir / "logos"
    logo_dir.mkdir()
    (logo_dir / "logo1.png").write_bytes(b"fake logo 1")
    avatar_dir = Path(temp_dir) / "static" / "avatars"
    avatar_dir.mkdir(parents=True)

    db_path = data_dir / "homeoffice_assistant.db"
    shutil.copy2(migrated_db_template, db_path)

    # Copy the admin with the ORM column types, so ids are stored exactly as
    # the application stores them.
    users = User.__table__
    admin_row = {
        column.name: getattr(admin_user, column.key) for column in users.columns
    }
    db_engine = create_engine(f"sqlite:///{db_path}")
    with db_engine.begin() as connection:
        connection.execute(users.insert().values(**admin_row))
    db_engine.dispose()

    # Create some test avatar files
    (avatar_dir / "avatar1.jpg").write_bytes(b"fake image 1")

    yield temp_dir, data_dir, avatar_dir, db_path

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_backup_paths(temp_backup_dirs):
    """Mock the backup service paths for API tests.

    The avatar and logo directories are patched where the service reads them,
    so no test touches the real data/logos or static/avatars.
    """
    temp_dir, data_dir, avatar_dir, db_path = temp_backup_dirs

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

    def test_restores_valid_backup(self, admin_client, admin_user, mock_backup_paths):
        """Restoring an alembic-built backup keeps the admin as Global Admin."""
        _, _, _, db_path = mock_backup_paths
        seed_other_user_data(db_path)

        response = post_restore(admin_client, make_backup())

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True, f"Restore failed: {data}"
        assert data["requires_restart"] is True
        assert "restart" in data["message"].lower()
        assert data["migrations_run"] is True
        assert data["configs_imported"] == 1

        with session_on(db_path) as db:
            assert db.scalars(select(User.username)).all() == ["admin"]
            role_names = db.scalars(
                select(Role.name)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == admin_user.id)
            ).all()
            assert role_names == [GLOBAL_ADMIN_ROLE]
            assert db.scalar(select(func.count()).select_from(UserSession)) == 0
            # The backup user's data now belongs to the admin.
            assert set(db.scalars(select(Event.user_id))) == {admin_user.id}
            assert set(db.scalars(select(TodoTemplate.user_id))) == {admin_user.id}
            assert set(db.scalars(select(HolidayCalendar.user_id))) == {admin_user.id}
            config = db.scalars(select(IntegrationConfig)).one()
            assert config.created_by == admin_user.id
            assert decrypt_config(config.config_encrypted) == {"url": "http://docs"}
            assert orphan_user_references(db) == {}

    def test_failure_before_swap_leaves_database_intact(
        self, admin_client, mock_backup_paths
    ):
        """A failing admin re-insert does not touch the live database."""
        _, _, avatar_dir, db_path = mock_backup_paths
        seed_other_user_data(db_path)
        backup_bytes = make_backup()
        (avatar_dir / "after_backup.jpg").write_bytes(b"new")
        before = snapshot(db_path)

        with patch.object(
            backup_restore.rbac_service,
            "assign_role_to_user",
            side_effect=RuntimeError("boom"),
        ):
            response = post_restore(admin_client, backup_bytes)

        data = response.json()
        assert data["success"] is False
        assert data["message"] == "Restore failed, nothing was changed, see server log"
        assert "boom" not in data["message"]
        assert snapshot(db_path) == before
        assert (avatar_dir / "after_backup.jpg").exists()

    def test_swap_failure_rolls_back(self, admin_client, mock_backup_paths):
        """A failure after the database was swapped restores the old data."""
        _, _, avatar_dir, db_path = mock_backup_paths
        seed_other_user_data(db_path)
        backup_bytes = make_backup()
        (avatar_dir / "after_backup.jpg").write_bytes(b"new")
        before = snapshot(db_path)
        replace = backup_restore._replace_dir_content
        calls: list[Path] = []

        def fail_first(source: Path, target: Path) -> None:
            calls.append(source)
            if len(calls) == 1:
                raise OSError("disk full")
            replace(source, target)

        with patch.object(backup_restore, "_replace_dir_content", fail_first):
            response = post_restore(admin_client, backup_bytes)

        data = response.json()
        assert data["success"] is False
        assert "rolled back" in data["message"]
        assert "disk full" not in data["message"]
        assert snapshot(db_path) == before
        assert sorted(p.name for p in avatar_dir.iterdir()) == [
            "after_backup.jpg",
            "avatar1.jpg",
        ]

    def test_logo_swap_failure_rolls_back_everything(
        self, admin_client, mock_backup_paths
    ):
        """A failure on the logos, after the avatars were swapped, undoes all."""
        _, _, avatar_dir, db_path = mock_backup_paths
        logo_dir = file_storage_service.LOGO_DIR
        seed_other_user_data(db_path)
        backup_bytes = make_backup()
        (avatar_dir / "after_backup.jpg").write_bytes(b"new")
        (logo_dir / "after_backup.png").write_bytes(b"new logo")
        before = snapshot(db_path)
        replace = backup_restore._replace_dir_content
        calls: list[Path] = []

        def fail_second(source: Path, target: Path) -> None:
            calls.append(source)
            if len(calls) == 2:
                raise OSError("disk full")
            replace(source, target)

        with patch.object(backup_restore, "_replace_dir_content", fail_second):
            response = post_restore(admin_client, backup_bytes)

        data = response.json()
        assert data["success"] is False
        assert "rolled back" in data["message"]
        assert "disk full" not in data["message"]
        assert calls[1].name == "logos"
        assert snapshot(db_path) == before
        assert sorted(p.name for p in avatar_dir.iterdir()) == [
            "after_backup.jpg",
            "avatar1.jpg",
        ]
        assert sorted(p.name for p in logo_dir.iterdir()) == [
            "after_backup.png",
            "logo1.png",
        ]

    def test_restore_keeps_avatar_directory_in_read_only_parent(
        self, admin_client, mock_backup_paths
    ):
        """The avatar directory may be a mount point the app cannot remove."""
        _, _, avatar_dir, _ = mock_backup_paths
        backup_bytes = make_backup()
        (avatar_dir / "after_backup.jpg").write_bytes(b"new")
        parent_mode = avatar_dir.parent.stat().st_mode
        avatar_dir.parent.chmod(0o555)
        try:
            response = post_restore(admin_client, backup_bytes)
        finally:
            avatar_dir.parent.chmod(parent_mode)

        assert response.json()["success"] is True, response.text
        assert sorted(p.name for p in avatar_dir.iterdir()) == ["avatar1.jpg"]

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


@contextmanager
def session_on(db_path: Path) -> Iterator[Session]:
    """Open an ORM session on a database file other than the test database."""
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        with Session(engine) as db:
            yield db
    finally:
        engine.dispose()


def make_backup() -> bytes:
    """Create an encrypted backup of the patched database."""
    backup_bytes, _ = backup_service.create_backup("testuser", TEST_PASSWORD)
    return backup_bytes


def post_restore(client, backup_bytes: bytes):
    """Upload a backup to the restore endpoint."""
    return client.post(
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


def seed_other_user_data(db_path: Path) -> None:
    """Give the database a second user who owns rows in user-scoped tables."""
    with session_on(db_path) as db:
        other = User(
            username="other",
            email="other@example.com",
            hashed_password=get_password_hash(TEST_PASSWORD),
            is_active=True,
        )
        company = Company(name="Acme", type=CompanyType.EMPLOYER)
        db.add_all([other, company])
        db.flush()
        member = db.scalar(select(Role).where(Role.name == MEMBER_ROLE))
        db.add_all(
            [
                UserRole(user_id=other.id, role_id=member.id),
                Event(
                    user_id=other.id,
                    company_id=company.id,
                    name="Trip",
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 1, 2),
                ),
                TodoTemplate(
                    user_id=other.id, title="Pack", template_set_name="Travel"
                ),
                HolidayCalendar(
                    user_id=other.id, country_code="AT", display_label="AT"
                ),
                IntegrationConfig(
                    integration_type=IntegrationType.PAPERLESS,
                    name="Docs",
                    config_encrypted=encrypt_config({"url": "http://docs"}),
                    created_by=other.id,
                ),
                UserSession(
                    user_id=other.id,
                    token="t" * 36,
                    expires_at=datetime.now(UTC) + timedelta(days=1),
                ),
            ]
        )
        db.commit()


def orphan_user_references(db: Session) -> dict[str, int]:
    """Count rows per column that reference a user who does not exist."""
    existing = set(inspect(db.get_bind()).get_table_names())
    user_ids = select(User.id)
    orphans = {}
    for table in Base.metadata.sorted_tables:
        if table.name not in existing:
            continue
        for fk in table.foreign_keys:
            if fk.column is not User.__table__.c.id:
                continue
            count = db.scalar(
                select(func.count())
                .select_from(table)
                .where(fk.parent.is_not(None), fk.parent.not_in(user_ids))
            )
            if count:
                orphans[f"{table.name}.{fk.parent.name}"] = count
    return orphans


def snapshot(db_path: Path) -> dict[str, list]:
    """Read the rows of the user-related tables for before/after comparison."""
    with session_on(db_path) as db:
        return {
            "users": sorted(db.scalars(select(User.username))),
            "user_roles": sorted(
                str(row) for row in db.execute(select(UserRole.user_id))
            ),
            "events": sorted(str(row) for row in db.execute(select(Event.user_id))),
            "sessions": sorted(db.scalars(select(UserSession.token))),
        }
