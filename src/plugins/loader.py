# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Plugin discovery, loading, and management."""

import importlib.util
import json
import logging
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from src.plugins.base import BasePlugin, PluginConfig, PluginManifest
from src.plugins.dependencies import unsatisfied_requirements
from src.plugins.manifest import (
    PLUGIN_MANIFEST_FILE,
    PluginValidationError,
    parse_manifest,
    validate_dependency_format,
)
from src.plugins.permissions import PermissionChecker

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Default plugins directory relative to project root
PLUGINS_DIR = Path("./plugins")


class PluginLoadError(Exception):
    """Error loading a plugin module."""

    pass


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

        result = subprocess.run(
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
        upgrade: bool = False,
    ) -> tuple[PluginManifest, str | None]:
        """Install a plugin from a ZIP file.

        Args:
            zip_path: Path to the ZIP file
            db: Optional database session (not used here, but available)
            upgrade: If True, allow replacing an existing plugin

        Returns:
            Tuple of (parsed plugin manifest, old version if upgraded else None)

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
            old_version: str | None = None

            if target_dir.exists():
                if not upgrade:
                    raise PluginValidationError(
                        f"Plugin {manifest.id} is already installed. "
                        "Use the upgrade option to replace it with a new version."
                    )

                # Get old version before replacing
                old_manifest_path = target_dir / PLUGIN_MANIFEST_FILE
                if old_manifest_path.exists():
                    try:
                        old_manifest = parse_manifest(old_manifest_path)
                        old_version = old_manifest.version
                    except (
                        PluginValidationError,
                        OSError,
                        json.JSONDecodeError,
                    ) as exc:
                        logger.warning(
                            "Failed to parse existing manifest for plugin %s at %s: %s",
                            manifest.id,
                            old_manifest_path,
                            exc,
                        )
                        old_version = "unknown"

                # Remove old plugin directory
                logger.info(
                    f"Upgrading plugin {manifest.id}: "
                    f"{old_version} -> {manifest.version}"
                )
                shutil.rmtree(target_dir)

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

            if old_version:
                logger.info(
                    f"Upgraded plugin {manifest.id}: "
                    f"{old_version} -> {manifest.version}"
                )
            else:
                logger.info(f"Installed plugin {manifest.id} v{manifest.version}")

        return manifest, old_version

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
        self._ensure_python_dependencies(manifest)
        plugin_class = load_plugin_class(plugin_path, manifest)
        return plugin_class(manifest, config, str(plugin_path))

    def _ensure_python_dependencies(self, manifest: PluginManifest) -> None:
        """Make sure the plugin's Python requirements are importable.

        Requirements the environment already satisfies are not installed. The
        application image has no pip (its venv is exactly the lockfile), so a
        missing requirement there must be added to the image instead.

        Args:
            manifest: Parsed plugin manifest.

        Raises:
            PluginLoadError: If a requirement is malformed, missing without pip,
                or fails to install.
        """
        requirements = manifest.python_dependencies
        if not requirements:
            return
        invalid = [d for d in requirements if not validate_dependency_format(d)]
        if invalid:
            raise PluginLoadError(
                f"Invalid dependency format for {manifest.id}: {', '.join(invalid)}"
            )
        missing = unsatisfied_requirements(requirements)
        if not missing:
            return
        if importlib.util.find_spec("pip") is None:
            raise PluginLoadError(
                f"Plugin {manifest.id} requires {', '.join(missing)}, which are not "
                "installed; add them to the application image"
            )
        success, msg = install_plugin_dependencies(manifest.id, missing)
        if not success:
            raise PluginLoadError(
                f"Failed to install dependencies for {manifest.id}: {msg}"
            )

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
