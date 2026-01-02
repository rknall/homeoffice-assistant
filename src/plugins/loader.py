# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Plugin discovery, loading, and management."""

import importlib.util
import json
import logging
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from src.plugins.base import (
    BasePlugin,
    Permission,
    PluginCapability,
    PluginConfig,
    PluginManifest,
    ProvidedPermission,
)
from src.plugins.permissions import PermissionChecker

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Default plugins directory relative to project root
PLUGINS_DIR = Path("./plugins")
PLUGIN_MANIFEST_FILE = "plugin.manifest.json"

# Regex for validating pip requirement specifiers (PEP 508 simplified)
# Matches: package, package>=1.0, package[extra]>=1.0,<2.0, etc.
DEPENDENCY_PATTERN = re.compile(
    r"^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?"  # Package name
    r"(\[[a-zA-Z0-9,._-]+\])?"  # Optional extras like [dev,test]
    r"([<>=!~]+[\d.]+(\s*,\s*[<>=!~]+[\d.]+)*)?$"  # Version specifiers
)


class PluginLoadError(Exception):
    """Error loading a plugin module."""

    pass


class PluginValidationError(Exception):
    """Error validating a plugin manifest or structure."""

    pass


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
        valid_perms, invalid_perms = checker.parse_permissions(perms_data)
        required_permissions = valid_perms
        for invalid in invalid_perms:
            logger.warning(f"Unknown permission: {invalid}")
    elif isinstance(perms_data, dict):
        # NEW FORMAT: object with required/provided sections
        # Example: {"required": ["user.read"], "provided": [...]}

        # Parse required permissions
        required_list = perms_data.get("required", [])
        if isinstance(required_list, list):
            valid_perms, invalid_perms = checker.parse_permissions(required_list)
            required_permissions = valid_perms
            for invalid in invalid_perms:
                logger.warning(f"Unknown required permission: {invalid}")

        # Parse provided permissions
        provided_list = perms_data.get("provided", [])
        if isinstance(provided_list, list):
            for item in provided_list:
                if isinstance(item, dict):
                    code = item.get("code", "")
                    description = item.get("description", "")

                    # Validate prefix requirement
                    if not code.startswith(f"{plugin_id}."):
                        raise PluginValidationError(
                            f"Provided permission '{code}' must start with "
                            f"'{plugin_id}.' prefix"
                        )

                    provided_permissions.append(
                        ProvidedPermission(code=code, description=description)
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


def install_plugin_dependencies(
    plugin_id: str,
    dependencies: list[str],
    verbose: bool = False,
) -> tuple[bool, str]:
    """Install Python dependencies for a plugin.

    Uses pip to install the specified packages. This is called before
    the plugin module is loaded to ensure all imports succeed.

    Args:
        plugin_id: Plugin ID for logging
        dependencies: List of pip requirement specifiers (e.g., ["holidays>=0.62"])
        verbose: If True, use --verbose flag for pip (default False)

    Returns:
        Tuple of (success, message)
    """
    if not dependencies:
        return True, "No dependencies to install"

    # Validate dependency formats for security
    invalid_deps = [d for d in dependencies if not validate_dependency_format(d)]
    if invalid_deps:
        error_msg = f"Invalid dependency format: {', '.join(invalid_deps)}"
        logger.error(f"Plugin {plugin_id}: {error_msg}")
        return False, error_msg

    logger.debug(f"Installing dependencies for plugin {plugin_id}: {dependencies}")
    logger.debug(f"Using Python executable: {sys.executable}")

    try:
        cmd = [sys.executable, "-m", "pip", "install"]
        if verbose or logger.isEnabledFor(logging.DEBUG):
            cmd.append("--verbose")
        else:
            cmd.append("--quiet")
        cmd.extend(dependencies)

        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        if verbose or logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"pip stdout: {result.stdout}")
            if result.stderr:
                logger.debug(f"pip stderr: {result.stderr}")
        installed = ", ".join(dependencies)
        logger.info(f"Successfully installed dependencies for {plugin_id}: {installed}")
        return True, f"Installed: {installed}"
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else str(e)
        logger.error(f"Failed to install dependencies for {plugin_id}: {error_msg}")
        return False, f"Failed to install dependencies: {error_msg}"
    except Exception as e:
        logger.error(f"Unexpected error installing dependencies for {plugin_id}: {e}")
        return False, f"Unexpected error: {e}"


def load_plugin_class(
    plugin_path: Path,
    manifest: PluginManifest,
) -> type[BasePlugin]:
    """Load the plugin class from the plugin directory.

    Args:
        plugin_path: Path to the plugin directory
        manifest: Parsed plugin manifest

    Returns:
        Plugin class (not instantiated)

    Raises:
        PluginLoadError: If plugin module cannot be loaded
    """
    # Look for plugin.py in backend/
    plugin_module_path = plugin_path / "backend" / "plugin.py"
    if not plugin_module_path.exists():
        raise PluginLoadError(f"Plugin module not found: {plugin_module_path}")

    # Dynamic import
    module_name = f"plugins.{manifest.id}.backend.plugin"
    spec = importlib.util.spec_from_file_location(module_name, plugin_module_path)

    if spec is None or spec.loader is None:
        raise PluginLoadError(f"Could not load plugin spec: {plugin_module_path}")

    module = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(module)
    except Exception as e:
        raise PluginLoadError(f"Error executing plugin module: {e}") from e

    # Find the plugin class (must inherit from BasePlugin)
    plugin_class: type[BasePlugin] | None = None
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (
            isinstance(attr, type)
            and issubclass(attr, BasePlugin)
            and attr is not BasePlugin
        ):
            plugin_class = attr
            break

    if plugin_class is None:
        raise PluginLoadError(
            f"No BasePlugin subclass found in {plugin_module_path}. "
            "Plugin must define a class that extends BasePlugin."
        )

    return plugin_class


class PluginLoader:
    """Handles plugin discovery, loading, and installation."""

    def __init__(self, plugins_dir: Path | None = None) -> None:
        """Initialize the plugin loader.

        Args:
            plugins_dir: Directory containing plugins. Defaults to ./plugins
        """
        self.plugins_dir = plugins_dir or PLUGINS_DIR
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

    def discover_plugins(self) -> list[tuple[Path, PluginManifest]]:
        """Discover all plugins in the plugins directory.

        Returns:
            List of tuples (plugin_path, manifest) for each valid plugin
        """
        discovered: list[tuple[Path, PluginManifest]] = []
        logger.debug(f"Discovering plugins in {self.plugins_dir}")

        if not self.plugins_dir.exists():
            return discovered

        for entry in self.plugins_dir.iterdir():
            if not entry.is_dir():
                continue

            # Skip hidden directories and __pycache__
            if entry.name.startswith(".") or entry.name == "__pycache__":
                continue

            manifest_path = entry / PLUGIN_MANIFEST_FILE
            if not manifest_path.exists():
                logger.warning(f"No manifest found in {entry}")
                continue

            try:
                manifest = parse_manifest(manifest_path)
                discovered.append((entry, manifest))
                logger.debug(f"Discovered plugin: {manifest.id} v{manifest.version}")
            except PluginValidationError as e:
                logger.error(f"Invalid manifest in {entry}: {e}")

        return discovered

    def install_from_zip(
        self,
        zip_path: Path,
        db: Session | None = None,
    ) -> PluginManifest:
        """Install a plugin from a ZIP file.

        Args:
            zip_path: Path to the ZIP file
            db: Optional database session (not used here, but available)

        Returns:
            Parsed plugin manifest

        Raises:
            PluginValidationError: If ZIP contents are invalid
        """
        if not zip_path.exists():
            raise PluginValidationError(f"ZIP file not found: {zip_path}")

        if not zipfile.is_zipfile(zip_path):
            raise PluginValidationError(f"Not a valid ZIP file: {zip_path}")

        logger.debug(f"Installing plugin from ZIP: {zip_path}")

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Extract ZIP
            try:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(temp_path)
            except zipfile.BadZipFile as e:
                raise PluginValidationError(f"Corrupted ZIP file: {e}") from e

            # Find manifest (might be in root or in a subdirectory)
            manifest_path = temp_path / PLUGIN_MANIFEST_FILE
            source_path = temp_path

            if not manifest_path.exists():
                # Check for single subdirectory containing manifest
                subdirs = [
                    d
                    for d in temp_path.iterdir()
                    if d.is_dir() and not d.name.startswith(".")
                ]
                if len(subdirs) == 1:
                    manifest_path = subdirs[0] / PLUGIN_MANIFEST_FILE
                    source_path = subdirs[0]

            if not manifest_path.exists():
                raise PluginValidationError(f"No {PLUGIN_MANIFEST_FILE} found in ZIP")

            manifest = parse_manifest(manifest_path)

            # Check if plugin already exists
            target_dir = self.plugins_dir / manifest.id
            if target_dir.exists():
                raise PluginValidationError(
                    f"Plugin {manifest.id} is already installed. "
                    "Uninstall it first or use upgrade."
                )

            # Validate required permissions
            checker = PermissionChecker()
            dangerous = checker.get_dangerous_permissions(manifest.required_permissions)
            if dangerous:
                logger.warning(
                    f"Plugin {manifest.id} requests dangerous permissions: "
                    f"{[p.value for p in dangerous]}"
                )

            # Copy to plugins directory
            shutil.copytree(source_path, target_dir)
            logger.info(f"Installed plugin {manifest.id} v{manifest.version}")

        return manifest

    def uninstall(self, plugin_id: str) -> None:
        """Uninstall a plugin by removing its directory.

        Args:
            plugin_id: ID of the plugin to uninstall
        """
        plugin_dir = self.plugins_dir / plugin_id
        if plugin_dir.exists():
            shutil.rmtree(plugin_dir)
            logger.info(f"Uninstalled plugin {plugin_id}")
        else:
            logger.warning(f"Plugin directory not found: {plugin_dir}")

    def get_plugin_path(self, plugin_id: str) -> Path | None:
        """Get the path to a plugin's directory.

        Args:
            plugin_id: Plugin ID

        Returns:
            Path to plugin directory or None if not found
        """
        plugin_path = self.plugins_dir / plugin_id
        if plugin_path.exists() and plugin_path.is_dir():
            return plugin_path
        return None

    def load_plugin(
        self,
        plugin_path: Path,
        manifest: PluginManifest,
        config: PluginConfig,
    ) -> BasePlugin:
        """Load and instantiate a plugin.

        Args:
            plugin_path: Path to the plugin directory
            manifest: Parsed plugin manifest
            config: Runtime configuration

        Returns:
            Instantiated plugin instance

        Raises:
            PluginLoadError: If dependencies cannot be installed or plugin fails to load
        """
        # Install Python dependencies before loading the module
        if manifest.python_dependencies:
            success, msg = install_plugin_dependencies(
                manifest.id, manifest.python_dependencies
            )
            if not success:
                raise PluginLoadError(
                    f"Failed to install dependencies for {manifest.id}: {msg}"
                )

        plugin_class = load_plugin_class(plugin_path, manifest)
        return plugin_class(manifest, config, str(plugin_path))

    def has_frontend(self, plugin_id: str) -> bool:
        """Check if a plugin has frontend assets.

        Args:
            plugin_id: Plugin ID

        Returns:
            True if plugin has frontend/index.js
        """
        plugin_path = self.plugins_dir / plugin_id
        frontend_index = plugin_path / "frontend" / "index.js"
        return frontend_index.exists()

    def has_backend(self, plugin_id: str) -> bool:
        """Check if a plugin has backend code.

        Args:
            plugin_id: Plugin ID

        Returns:
            True if plugin has backend/plugin.py
        """
        plugin_path = self.plugins_dir / plugin_id
        backend_plugin = plugin_path / "backend" / "plugin.py"
        return backend_plugin.exists()
