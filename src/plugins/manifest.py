# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Plugin manifest parsing and validation."""

import json
import logging
import re
from pathlib import Path

from src.plugins.base import (
    Permission,
    PluginCapability,
    PluginManifest,
    ProvidedPermission,
)
from src.plugins.permissions import PermissionChecker

logger = logging.getLogger(__name__)

PLUGIN_MANIFEST_FILE = "plugin.manifest.json"

# Regex for validating pip requirement specifiers (PEP 508 simplified)
# Matches: package, package>=1.0, package[extra]>=1.0,<2.0, etc.
# Note: PEP 508 requires package names to start with a letter
DEPENDENCY_PATTERN = re.compile(
    r"^[a-zA-Z]([a-zA-Z0-9._-]*[a-zA-Z0-9])?"  # Package name (must start with letter)
    r"(\[[a-zA-Z0-9,._-]+\])?"  # Optional extras like [dev,test]
    r"([<>=!~]+[\d.]+(\s*,\s*[<>=!~]+[\d.]+)*)?$"  # Version specifiers
)


class PluginValidationError(Exception):
    """Error validating a plugin manifest or structure."""

    pass


def _parse_required_permissions(
    checker: PermissionChecker, codes: list[str]
) -> set[Permission]:
    """Parse the permissions a manifest requires from the host.

    Args:
        checker: Permission checker used to parse the codes.
        codes: Permission codes listed in the manifest.

    Returns:
        The parsed permissions.

    Raises:
        PluginValidationError: If a code is not a core permission code.
    """
    valid_perms, invalid_perms = checker.parse_permissions(codes)
    if invalid_perms:
        raise PluginValidationError(
            f"Unknown required permission: {', '.join(invalid_perms)}. "
            "Required permissions must be core permission codes."
        )
    return valid_perms


def parse_manifest(manifest_path: Path) -> PluginManifest:
    """Parse and validate a plugin manifest file.

    Args:
        manifest_path: Path to the manifest JSON file

    Returns:
        Parsed PluginManifest dataclass

    Raises:
        PluginValidationError: If manifest is invalid
    """
    try:
        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise PluginValidationError(f"Invalid JSON in manifest: {e}") from e
    except OSError as e:
        raise PluginValidationError(f"Could not read manifest: {e}") from e

    # Validate required fields
    required_fields = ["id", "name", "version", "description"]
    for field in required_fields:
        if field not in data:
            raise PluginValidationError(f"Missing required field: {field}")

    # Validate plugin ID format (alphanumeric, hyphens, underscores)
    plugin_id = data["id"]
    if not plugin_id:
        raise PluginValidationError("Plugin ID cannot be empty")
    if not all(c.isalnum() or c in "-_" for c in plugin_id):
        raise PluginValidationError(
            f"Invalid plugin ID: {plugin_id}. "
            "Use only alphanumeric characters, hyphens, and underscores."
        )

    # Parse capabilities
    capabilities: set[PluginCapability] = set()
    caps_data = data.get("capabilities", {})

    if isinstance(caps_data, dict):
        # Handle object format: {"backend": true, "frontend": true}
        for cap_name, enabled in caps_data.items():
            if enabled:
                try:
                    capabilities.add(PluginCapability(cap_name))
                except ValueError:
                    logger.warning(f"Unknown capability: {cap_name}")
    elif isinstance(caps_data, list):
        # Handle array format: ["backend", "frontend"]
        for cap_name in caps_data:
            try:
                capabilities.add(PluginCapability(cap_name))
            except ValueError:
                logger.warning(f"Unknown capability: {cap_name}")

    # Parse permissions - support both old and new formats
    required_permissions: set[Permission] = set()
    provided_permissions: list[ProvidedPermission] = []
    checker = PermissionChecker()

    perms_data = data.get("permissions", {})

    if isinstance(perms_data, list):
        # OLD FORMAT: flat array, treat as required permissions
        # Example: ["user.read", "event.read"]
        required_permissions = _parse_required_permissions(checker, perms_data)
    elif isinstance(perms_data, dict):
        # NEW FORMAT: object with required/provided sections
        # Example: {"required": ["user.read"], "provided": [...]}

        # Parse required permissions
        required_list = perms_data.get("required", [])
        if isinstance(required_list, list):
            required_permissions = _parse_required_permissions(checker, required_list)

        # Parse provided permissions
        provided_list = perms_data.get("provided", [])
        if isinstance(provided_list, list):
            for item in provided_list:
                if isinstance(item, dict):
                    code = item.get("code", "")
                    description = item.get("description", "")
                    member_default = item.get("member_default", False) is True

                    # Validate prefix requirement
                    if not code.startswith(f"{plugin_id}."):
                        raise PluginValidationError(
                            f"Provided permission '{code}' must start with "
                            f"'{plugin_id}.' prefix"
                        )

                    provided_permissions.append(
                        ProvidedPermission(
                            code=code,
                            description=description,
                            member_default=member_default,
                        )
                    )
                elif isinstance(item, str):
                    # Allow simple string format for provided permissions
                    if not item.startswith(f"{plugin_id}."):
                        raise PluginValidationError(
                            f"Provided permission '{item}' must start with "
                            f"'{plugin_id}.' prefix"
                        )
                    provided_permissions.append(
                        ProvidedPermission(code=item, description="")
                    )

    return PluginManifest(
        id=data["id"],
        name=data["name"],
        version=data["version"],
        description=data["description"],
        author=data.get("author", ""),
        homepage=data.get("homepage", ""),
        license=data.get("license", ""),
        min_host_version=data.get("min_host_version", "0.1.0"),
        max_host_version=data.get("max_host_version"),
        capabilities=capabilities,
        required_permissions=required_permissions,
        provided_permissions=provided_permissions,
        dependencies=data.get("dependencies", []),
        python_dependencies=data.get("python_dependencies", []),
        table_prefix=data.get("table_prefix"),
    )


def validate_dependency_format(dependency: str) -> bool:
    """Validate that a dependency string matches expected pip format.

    This prevents potential security issues from malformed dependency strings.

    Args:
        dependency: A pip requirement specifier (e.g., "holidays>=0.62")

    Returns:
        True if valid, False otherwise
    """
    return DEPENDENCY_PATTERN.match(dependency) is not None
