# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Pydantic schemas for plugin API endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PluginCapabilitiesResponse(BaseModel):
    """Plugin capabilities in API responses."""

    backend: bool = False
    frontend: bool = False
    config: bool = False


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
    permissions: list[str]


class PluginSummary(BaseModel):
    """Summary of a plugin for list views."""

    plugin_id: str
    plugin_version: str
    is_enabled: bool
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
    is_enabled: bool
    manifest: dict[str, Any] | None = None
    config_schema: dict[str, Any]
    settings: dict[str, Any]
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
    message: str = ""


class PluginEnableResponse(BaseModel):
    """Response after enabling/disabling a plugin."""

    success: bool
    plugin_id: str
    is_enabled: bool
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
