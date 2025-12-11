# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Backup and restore API endpoints."""

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from fastapi.responses import Response

from src.api.deps import get_current_admin, require_permission
from src.models import User
from src.schemas.backup import (
    BackupCreateRequest,
    BackupInfoResponse,
    BackupMetadata,
    RestoreResponse,
    RestoreValidationResponse,
)
from src.services import backup_service

router = APIRouter()

MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500MB


@router.get("/info", response_model=BackupInfoResponse)
def get_backup_info(
    current_user: User = Depends(get_current_admin),
) -> BackupInfoResponse:
    """Get information about current backup state."""
    info = backup_service.get_backup_info()
    return BackupInfoResponse(**info)


@router.post("/create")
def create_backup(
    request: BackupCreateRequest,
    current_user: User = Depends(get_current_admin),
) -> Response:
    """Create and download a password-protected backup.

    The backup is encrypted with the provided password. You will need this
    password to restore the backup later.
    """
    try:
        backup_bytes, filename = backup_service.create_backup(
            current_user.username, request.password
        )
        return Response(
            content=backup_bytes,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create backup: {e!s}",
        ) from e


@router.post("/validate", response_model=RestoreValidationResponse)
async def validate_backup(
    file: UploadFile,
    password: str | None = Form(default=None),
    current_user: User = Depends(get_current_admin),
) -> RestoreValidationResponse:
    """Validate an uploaded backup file before restore.

    For password-protected backups (v0.2.1+), provide the password.
    For legacy backups (v0.2.0), no password is needed.
    """
    content = await file.read()

    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max: {MAX_UPLOAD_SIZE // (1024 * 1024)}MB",
        )

    valid, message, metadata, warnings = backup_service.validate_backup(
        content, password
    )

    # Convert metadata dict to BackupMetadata, handling None case
    backup_metadata = None
    if metadata:
        backup_metadata = BackupMetadata(
            backup_format_version=metadata.get("backup_format_version", "unknown"),
            created_at=metadata.get("created_at"),
            created_by=metadata.get("created_by", "unknown"),
            db_size_bytes=metadata.get("db_size_bytes", 0),
            avatar_count=metadata.get("avatar_count", 0),
            checksum=metadata.get("checksum", ""),
            is_password_protected=metadata.get("is_password_protected", False),
            has_legacy_secret_key=metadata.get("has_legacy_secret_key", False),
            integration_config_count=metadata.get("integration_config_count", 0),
        )

    return RestoreValidationResponse(
        valid=valid,
        message=message,
        metadata=backup_metadata,
        warnings=warnings,
    )


@router.post("/restore", response_model=RestoreResponse)
async def restore_backup(
    file: UploadFile,
    password: str | None = Form(default=None),
    current_user: User = Depends(require_permission("system.admin")),
) -> RestoreResponse:
    """Restore from an uploaded backup file.

    For password-protected backups (v0.2.1+), provide the password.
    The current admin user will be preserved during restore.
    """
    content = await file.read()

    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max: {MAX_UPLOAD_SIZE // (1024 * 1024)}MB",
        )

    success, message, details = backup_service.perform_restore(
        content,
        password=password,
        current_user_id=str(current_user.id),
    )

    return RestoreResponse(
        success=success,
        message=message,
        requires_restart=success,
        migrations_run=details.get("migrations_run", False),
        migrations_message=details.get("migrations_message", ""),
        configs_imported=details.get("configs_imported", 0),
    )
