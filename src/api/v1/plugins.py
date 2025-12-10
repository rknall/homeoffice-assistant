# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Plugin management API endpoints."""

import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_admin, get_current_user, get_db
from src.models import PluginConfigModel, User
from src.plugins import (
    PluginCapability,
    PluginLoader,
    PluginLoadError,
    PluginRegistry,
    PluginValidationError,
)
from src.plugins.loader import PLUGIN_MANIFEST_FILE, parse_manifest
from src.schemas.plugin import (
    PluginEnableResponse,
    PluginInfoResponse,
    PluginInstallResponse,
    PluginListResponse,
    PluginSettingsResponse,
    PluginSettingsUpdate,
    PluginSummary,
    PluginUninstallResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/plugins", tags=["plugins"])


def _get_loader() -> PluginLoader:
    """Get the plugin loader instance."""
    return PluginLoader()


@router.get("", response_model=PluginListResponse)
async def list_plugins(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> PluginListResponse:
    """List all installed plugins."""
    configs = db.query(PluginConfigModel).all()
    loader = _get_loader()

    plugins: list[PluginSummary] = []
    for config in configs:
        # Try to get manifest for additional info
        plugin_path = loader.get_plugin_path(config.plugin_id)
        manifest = None
        has_frontend = False
        has_backend = False

        if plugin_path:
            manifest_path = plugin_path / PLUGIN_MANIFEST_FILE
            if manifest_path.exists():
                try:
                    manifest_data = parse_manifest(manifest_path)
                    has_frontend = loader.has_frontend(config.plugin_id)
                    has_backend = loader.has_backend(config.plugin_id)

                    # Convert to response format
                    from src.schemas.plugin import (
                        PluginCapabilitiesResponse,
                        PluginManifestResponse,
                    )

                    manifest = PluginManifestResponse(
                        id=manifest_data.id,
                        name=manifest_data.name,
                        version=manifest_data.version,
                        description=manifest_data.description,
                        author=manifest_data.author,
                        homepage=manifest_data.homepage,
                        license=manifest_data.license,
                        capabilities=PluginCapabilitiesResponse(
                            backend=PluginCapability.BACKEND
                            in manifest_data.capabilities,
                            frontend=PluginCapability.FRONTEND
                            in manifest_data.capabilities,
                            config=PluginCapability.CONFIG
                            in manifest_data.capabilities,
                        ),
                        permissions=[p.value for p in manifest_data.permissions],
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not load manifest for {config.plugin_id}: {e}"
                    )

        plugins.append(
            PluginSummary(
                plugin_id=config.plugin_id,
                plugin_version=config.plugin_version,
                is_enabled=config.is_enabled,
                manifest=manifest,
                has_frontend=has_frontend,
                has_backend=has_backend,
                created_at=config.created_at,
                updated_at=config.updated_at,
            )
        )

    return PluginListResponse(plugins=plugins)


@router.get("/{plugin_id}", response_model=PluginInfoResponse)
async def get_plugin(
    plugin_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> PluginInfoResponse:
    """Get details for a specific plugin."""
    config = (
        db.query(PluginConfigModel)
        .filter(PluginConfigModel.plugin_id == plugin_id)
        .first()
    )

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin {plugin_id} not found",
        )

    loader = _get_loader()
    plugin_path = loader.get_plugin_path(plugin_id)

    manifest_dict = None
    config_schema: dict = {}

    if plugin_path:
        manifest_path = plugin_path / PLUGIN_MANIFEST_FILE
        if manifest_path.exists():
            try:
                manifest_data = parse_manifest(manifest_path)
                manifest_dict = {
                    "id": manifest_data.id,
                    "name": manifest_data.name,
                    "version": manifest_data.version,
                    "description": manifest_data.description,
                    "author": manifest_data.author,
                    "homepage": manifest_data.homepage,
                    "license": manifest_data.license,
                    "min_host_version": manifest_data.min_host_version,
                    "max_host_version": manifest_data.max_host_version,
                    "capabilities": [c.value for c in manifest_data.capabilities],
                    "permissions": [p.value for p in manifest_data.permissions],
                    "dependencies": manifest_data.dependencies,
                }
            except Exception as e:
                logger.warning(f"Could not load manifest for {plugin_id}: {e}")

    # Try to get config schema from loaded plugin
    registry = PluginRegistry.get_instance()
    plugin = registry.get_plugin(plugin_id)
    if plugin:
        config_schema = plugin.get_config_schema()

    return PluginInfoResponse(
        plugin_id=config.plugin_id,
        plugin_version=config.plugin_version,
        is_enabled=config.is_enabled,
        manifest=manifest_dict,
        config_schema=config_schema,
        settings=config.get_decrypted_settings(),
        migration_version=config.migration_version,
        has_frontend=loader.has_frontend(plugin_id) if plugin_path else False,
        has_backend=loader.has_backend(plugin_id) if plugin_path else False,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.post("/install", response_model=PluginInstallResponse)
async def install_plugin(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> PluginInstallResponse:
    """Install a plugin from a ZIP file.

    Requires admin privileges.
    """
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a ZIP archive",
        )

    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        registry = PluginRegistry.get_instance()
        plugin = await registry.install_plugin(tmp_path, db)

        return PluginInstallResponse(
            success=True,
            plugin_id=plugin.id,
            plugin_name=plugin.name,
            version=plugin.manifest.version,
            message=f"Plugin {plugin.name} installed successfully",
        )

    except PluginValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except PluginLoadError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load plugin: {e}",
        ) from e
    finally:
        tmp_path.unlink(missing_ok=True)


@router.delete("/{plugin_id}", response_model=PluginUninstallResponse)
async def uninstall_plugin(
    plugin_id: str,
    drop_tables: bool = False,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> PluginUninstallResponse:
    """Uninstall a plugin.

    Requires admin privileges.

    Args:
        plugin_id: Plugin to uninstall
        drop_tables: If True, also drops the plugin's database tables
        db: Database session
    """
    config = (
        db.query(PluginConfigModel)
        .filter(PluginConfigModel.plugin_id == plugin_id)
        .first()
    )

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin {plugin_id} not found",
        )

    registry = PluginRegistry.get_instance()
    await registry.uninstall_plugin(plugin_id, db, drop_tables=drop_tables)

    return PluginUninstallResponse(
        success=True,
        plugin_id=plugin_id,
        tables_dropped=drop_tables,
        message=f"Plugin {plugin_id} uninstalled successfully",
    )


@router.post("/{plugin_id}/enable", response_model=PluginEnableResponse)
async def enable_plugin(
    plugin_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> PluginEnableResponse:
    """Enable a disabled plugin.

    Requires admin privileges.
    """
    config = (
        db.query(PluginConfigModel)
        .filter(PluginConfigModel.plugin_id == plugin_id)
        .first()
    )

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin {plugin_id} not found",
        )

    if config.is_enabled:
        return PluginEnableResponse(
            success=True,
            plugin_id=plugin_id,
            is_enabled=True,
            message="Plugin is already enabled",
        )

    registry = PluginRegistry.get_instance()
    await registry.enable_plugin(plugin_id, db)

    return PluginEnableResponse(
        success=True,
        plugin_id=plugin_id,
        is_enabled=True,
        message=f"Plugin {plugin_id} enabled successfully",
    )


@router.post("/{plugin_id}/disable", response_model=PluginEnableResponse)
async def disable_plugin(
    plugin_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> PluginEnableResponse:
    """Disable an enabled plugin.

    Requires admin privileges.
    """
    config = (
        db.query(PluginConfigModel)
        .filter(PluginConfigModel.plugin_id == plugin_id)
        .first()
    )

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin {plugin_id} not found",
        )

    if not config.is_enabled:
        return PluginEnableResponse(
            success=True,
            plugin_id=plugin_id,
            is_enabled=False,
            message="Plugin is already disabled",
        )

    registry = PluginRegistry.get_instance()
    await registry.disable_plugin(plugin_id, db)

    return PluginEnableResponse(
        success=True,
        plugin_id=plugin_id,
        is_enabled=False,
        message=f"Plugin {plugin_id} disabled successfully",
    )


@router.put("/{plugin_id}/settings", response_model=PluginSettingsResponse)
async def update_plugin_settings(
    plugin_id: str,
    settings_update: PluginSettingsUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> PluginSettingsResponse:
    """Update plugin settings.

    Requires admin privileges.
    """
    config = (
        db.query(PluginConfigModel)
        .filter(PluginConfigModel.plugin_id == plugin_id)
        .first()
    )

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin {plugin_id} not found",
        )

    registry = PluginRegistry.get_instance()
    await registry.update_plugin_settings(plugin_id, settings_update.settings, db)

    return PluginSettingsResponse(
        success=True,
        plugin_id=plugin_id,
        settings=config.get_decrypted_settings(),
        message="Settings updated successfully",
    )
