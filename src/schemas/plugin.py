# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Pydantic schemas for plugin API endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.plugins.base import PluginCapability, PluginManifest


class PluginCapabilitiesResponse(BaseModel):
    """Plugin capabilities in API responses."""

    backend: bool = False
    frontend: bool = False
    config: bool = False


class ProvidedPermissionResponse(BaseModel):
    """A permission provided by a plugin."""

    code: str
    description: str


class PluginManifestResponse(BaseModel):
    """Plugin manifest in API responses."""

    id: str
    name: str
    version: str
    description: str
    author: str = ""
    homepage: str = ""
    license: str = ""
    capabilities: PluginCapabilitiesResponse
    # Legacy field - kept for backward compatibility
    permissions: list[str] = []
    # New fields for required vs provided permissions
    required_permissions: list[str] = []
    provided_permissions: list[ProvidedPermissionResponse] = []

    @classmethod
    def from_manifest(cls, manifest: PluginManifest) -> PluginManifestResponse:
        """Build the list-view response from a parsed manifest.

        Args:
            manifest: Parsed plugin manifest.

        Returns:
            The manifest in list-view response form.
        """
        required = [p.value for p in manifest.required_permissions]
        return cls(
            id=manifest.id,
            name=manifest.name,
            version=manifest.version,
            description=manifest.description,
            author=manifest.author,
            homepage=manifest.homepage,
            license=manifest.license,
            capabilities=PluginCapabilitiesResponse(
                backend=PluginCapability.BACKEND in manifest.capabilities,
                frontend=PluginCapability.FRONTEND in manifest.capabilities,
                config=PluginCapability.CONFIG in manifest.capabilities,
            ),
            permissions=required,
            required_permissions=required,
            provided_permissions=[
                ProvidedPermissionResponse(code=p.code, description=p.description)
                for p in manifest.provided_permissions
            ],
        )


def manifest_detail(manifest: PluginManifest) -> dict[str, Any]:
    """Build the detail-view manifest dict from a parsed manifest.

    Args:
        manifest: Parsed plugin manifest.

    Returns:
        The manifest fields shown on the plugin detail page.
    """
    required = [p.value for p in manifest.required_permissions]
    return {
        "id": manifest.id,
        "name": manifest.name,
        "version": manifest.version,
        "description": manifest.description,
        "author": manifest.author,
        "homepage": manifest.homepage,
        "license": manifest.license,
        "min_host_version": manifest.min_host_version,
        "max_host_version": manifest.max_host_version,
        "capabilities": [c.value for c in manifest.capabilities],
        # "permissions" is the legacy name of "required_permissions"
        "permissions": required,
        "required_permissions": required,
        "provided_permissions": [
            {"code": p.code, "description": p.description}
            for p in manifest.provided_permissions
        ],
        "dependencies": manifest.dependencies,
    }


class PluginSummary(BaseModel):
    """Summary of a plugin for list views."""

    plugin_id: str
    plugin_version: str
    manifest: PluginManifestResponse | None = None
    has_frontend: bool
    has_backend: bool
    created_at: datetime
    updated_at: datetime


class PluginListResponse(BaseModel):
    """Response for plugin list endpoint."""

    plugins: list[PluginSummary]


class PluginInfoResponse(BaseModel):
    """Detailed plugin information."""

    plugin_id: str
    plugin_version: str
    manifest: dict[str, Any] | None = None
    config_schema: dict[str, Any]
    settings: dict[str, Any]
    secrets_set: list[str] = []
    migration_version: str | None = None
    has_frontend: bool
    has_backend: bool
    created_at: datetime
    updated_at: datetime


class PluginInstallResponse(BaseModel):
    """Response after successful plugin installation."""

    success: bool
    plugin_id: str
    plugin_name: str
    version: str
    message: str = ""


class PluginUninstallResponse(BaseModel):
    """Response after plugin uninstallation."""

    success: bool
    plugin_id: str
    tables_dropped: bool
    permissions_removed: bool = False
    message: str = ""


class PluginSettingsUpdate(BaseModel):
    """Request to update plugin settings."""

    settings: dict[str, Any] = Field(
        ...,
        description="Plugin settings dictionary",
    )


class PluginSettingsResponse(BaseModel):
    """Response after updating plugin settings."""

    success: bool
    plugin_id: str
    settings: dict[str, Any]
    message: str = ""


class DiscoveredPlugin(BaseModel):
    """A plugin discovered on disk but not yet installed."""

    plugin_id: str
    name: str
    version: str
    description: str
    author: str = ""
    has_frontend: bool
    has_backend: bool


class DiscoveredPluginsResponse(BaseModel):
    """Response for discovered plugins endpoint."""

    plugins: list[DiscoveredPlugin]
