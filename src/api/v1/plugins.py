# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Plugin management API endpoints."""

import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_admin, get_current_user
from src.database import get_db
from src.models import PluginConfigModel, User
from src.plugins import (
    PluginLoader,
    PluginLoadError,
    PluginManifest,
    PluginRegistry,
    PluginValidationError,
)
from src.plugins.manifest import PLUGIN_MANIFEST_FILE, parse_manifest
from src.schemas.plugin import (
    DiscoveredPlugin,
    DiscoveredPluginsResponse,
    PluginInfoResponse,
    PluginInstallResponse,
    PluginListResponse,
    PluginManifestResponse,
    PluginSettingsResponse,
    PluginSettingsUpdate,
    PluginSummary,
    PluginUninstallResponse,
    manifest_detail,
)
from src.services import config_secrets

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/plugins", tags=["plugins"])


def _get_loader() -> PluginLoader:
    """Get the plugin loader instance."""
    return PluginLoader()


def _read_manifest(plugin_path: Path | None, plugin_id: str) -> PluginManifest | None:
    """Parse a plugin's manifest from disk.

    Args:
        plugin_path: Plugin directory, or None when it is not on disk.
        plugin_id: Plugin identifier, used in the log message.

    Returns:
        The parsed manifest, or None when it is missing or invalid.
    """
    if not plugin_path:
        return None
    manifest_path = plugin_path / PLUGIN_MANIFEST_FILE
    if not manifest_path.exists():
        return None
    try:
        return parse_manifest(manifest_path)
    except PluginValidationError as e:
        logger.warning(f"Could not load manifest for {plugin_id}: {e}")
        return None


def _masked_settings(plugin_id: str, settings: dict) -> dict:
    """Mask a plugin's secret settings for a response.

    Secrets are never sent back, not even to admins; the edit form sends the
    blank mask back and the stored value is kept. A plugin that is registered
    but not loaded has no config schema, so nothing tells which values are
    secrets, and every value is masked.

    Args:
        plugin_id: Plugin identifier.
        settings: Decrypted settings.

    Returns:
        The settings with secrets (or, without a schema, all values) masked.
    """
    registry = PluginRegistry.get_instance()
    if not registry.is_plugin_loaded(plugin_id):
        return dict.fromkeys(settings, config_secrets.MASK)
    return config_secrets.mask(settings, registry.get_config_schema(plugin_id))


def _secrets_set(plugin_id: str, settings: dict) -> list[str]:
    """List the settings that hold a stored secret, without their values.

    A plugin that is registered but not loaded has no config schema, so every
    non-empty setting counts, matching ``_masked_settings``.

    Args:
        plugin_id: Plugin identifier.
        settings: Decrypted settings.

    Returns:
        Sorted names of the settings that hold a secret value.
    """
    registry = PluginRegistry.get_instance()
    if not registry.is_plugin_loaded(plugin_id):
        return sorted(name for name, value in settings.items() if value)
    return config_secrets.set_secret_fields(
        settings, registry.get_config_schema(plugin_id)
    )


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
        plugin_path = loader.get_plugin_path(config.plugin_id)
        manifest_data = _read_manifest(plugin_path, config.plugin_id)
        manifest = None
        has_frontend = False
        has_backend = False
        if manifest_data:
            manifest = PluginManifestResponse.from_manifest(manifest_data)
            has_frontend = loader.has_frontend(config.plugin_id)
            has_backend = loader.has_backend(config.plugin_id)

        plugins.append(
            PluginSummary(
                plugin_id=config.plugin_id,
                plugin_version=config.plugin_version,
                manifest=manifest,
                has_frontend=has_frontend,
                has_backend=has_backend,
                created_at=config.created_at,
                updated_at=config.updated_at,
            )
        )

    return PluginListResponse(plugins=plugins)


@router.get("/discovered", response_model=DiscoveredPluginsResponse)
async def list_discovered_plugins(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> DiscoveredPluginsResponse:
    """List plugins discovered on disk but not yet installed.

    These are plugin directories with valid manifests that haven't been
    registered in the database yet.
    """
    loader = _get_loader()
    discovered = loader.discover_plugins()

    # Get list of installed plugin IDs
    installed_ids = {config.plugin_id for config in db.query(PluginConfigModel).all()}

    plugins = []
    for _plugin_path, manifest in discovered:
        if manifest.id not in installed_ids:
            plugins.append(
                DiscoveredPlugin(
                    plugin_id=manifest.id,
                    name=manifest.name,
                    version=manifest.version,
                    description=manifest.description,
                    author=manifest.author,
                    has_frontend=loader.has_frontend(manifest.id),
                    has_backend=loader.has_backend(manifest.id),
                )
            )

    return DiscoveredPluginsResponse(plugins=plugins)


@router.post("/discovered/{plugin_id}/install", response_model=PluginInstallResponse)
async def install_discovered_plugin(
    plugin_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> PluginInstallResponse:
    """Install a plugin that was discovered on disk.

    This registers the plugin in the database and enables it.
    Requires admin privileges.
    """
    try:
        plugin = await PluginRegistry.get_instance().install_discovered(plugin_id, db)
    except PluginValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except (PluginLoadError, OSError, ImportError, RuntimeError) as e:
        logger.error(f"Failed to install discovered plugin {plugin_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to install plugin",
        ) from e

    return PluginInstallResponse(
        success=True,
        plugin_id=plugin.id,
        plugin_name=plugin.name,
        version=plugin.manifest.version,
        message=f"Plugin {plugin.name} installed successfully",
    )


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
    decrypted = config.get_decrypted_settings()

    manifest_data = _read_manifest(plugin_path, plugin_id)
    config_schema = PluginRegistry.get_instance().get_config_schema(plugin_id)

    return PluginInfoResponse(
        plugin_id=config.plugin_id,
        plugin_version=config.plugin_version,
        manifest=manifest_detail(manifest_data) if manifest_data else None,
        config_schema=config_schema,
        settings=_masked_settings(plugin_id, decrypted),
        secrets_set=_secrets_set(plugin_id, decrypted),
        migration_version=config.migration_version,
        has_frontend=loader.has_frontend(plugin_id) if plugin_path else False,
        has_backend=loader.has_backend(plugin_id) if plugin_path else False,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.post("/install", response_model=PluginInstallResponse)
async def install_plugin(
    file: UploadFile = File(...),
    upgrade: bool = False,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> PluginInstallResponse:
    """Install a plugin from a ZIP file, or upgrade an existing one.

    Requires admin privileges.

    Args:
        file: Plugin ZIP archive
        upgrade: If True, allows replacing an existing plugin with a new version
        db: Database session
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
        plugin, old_version = await registry.install_plugin(tmp_path, db, upgrade)

        if old_version:
            message = (
                f"Plugin {plugin.name} upgraded successfully "
                f"({old_version} -> {plugin.manifest.version})"
            )
        else:
            message = f"Plugin {plugin.name} installed successfully"

        return PluginInstallResponse(
            success=True,
            plugin_id=plugin.id,
            plugin_name=plugin.name,
            version=plugin.manifest.version,
            message=message,
        )

    except PluginValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except PluginLoadError as e:
        logger.error(f"Failed to load uploaded plugin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load plugin: see server log",
        ) from e
    finally:
        tmp_path.unlink(missing_ok=True)


@router.delete("/{plugin_id}", response_model=PluginUninstallResponse)
async def uninstall_plugin(
    plugin_id: str,
    drop_tables: bool = False,
    remove_permissions: bool = False,
    keep_files: bool = False,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> PluginUninstallResponse:
    """Uninstall a plugin.

    Requires admin privileges.

    Args:
        plugin_id: Plugin to uninstall
        drop_tables: If True, also drops the plugin's database tables
        remove_permissions: If True, also removes plugin-provided permissions
        keep_files: If True, keep plugin files on disk (for dev workflow).
            The plugin will appear in "discovered" list and can be reinstalled.
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
    await registry.uninstall_plugin(
        plugin_id,
        db,
        drop_tables=drop_tables,
        remove_permissions=remove_permissions,
        keep_files=keep_files,
    )

    message = f"Plugin {plugin_id} uninstalled successfully"
    if keep_files:
        message += " (files kept for reinstallation)"

    return PluginUninstallResponse(
        success=True,
        plugin_id=plugin_id,
        tables_dropped=drop_tables,
        permissions_removed=remove_permissions,
        message=message,
    )


@router.put("/{plugin_id}/settings", response_model=PluginSettingsResponse)
async def update_plugin_settings(
    plugin_id: str,
    settings_update: PluginSettingsUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> PluginSettingsResponse:
    """Update plugin settings.

    Requires admin privileges. A plugin that is registered but not loaded is
    rejected with 409 and keeps its stored settings.
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
    # Without a loaded plugin there is no config schema telling which fields
    # are secrets; a blank (masked) secret would replace the stored value.
    if not registry.is_plugin_loaded(plugin_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Plugin {plugin_id} is not loaded; its settings cannot be changed",
        )

    stored = await registry.update_plugin_settings(
        plugin_id, settings_update.settings, db
    )

    return PluginSettingsResponse(
        success=True,
        plugin_id=plugin_id,
        settings=_masked_settings(plugin_id, stored),
        message="Settings updated successfully",
    )
