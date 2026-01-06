# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for plugin migration management."""

from pathlib import Path

import pytest

from src.plugins.base import PluginCapability, PluginManifest
from src.plugins.migrations import PluginMigrationRunner


class TestGetTablePrefix:
    """Tests for _get_table_prefix method."""

    @pytest.fixture
    def plugin_path(self, tmp_path: Path) -> Path:
        """Create a temporary plugin directory."""
        return tmp_path / "test-plugin"

    def test_uses_manifest_table_prefix_when_available(self, plugin_path: Path):
        """Test that manifest table_prefix takes priority over derivation."""
        manifest = PluginManifest(
            id="time-tracking",
            name="Time Tracking",
            version="1.0.0",
            description="Test",
            capabilities={PluginCapability.BACKEND},
            table_prefix="tt_",
        )

        runner = PluginMigrationRunner(plugin_path, "time-tracking", manifest)

        # Should use manifest value, not derived "tt_" (which happens to match)
        assert runner._get_table_prefix() == "tt_"

    def test_uses_manifest_prefix_over_derived(self, plugin_path: Path):
        """Test manifest prefix is used even when different from derived."""
        # For "example" plugin, derivation would produce "example_"
        # but manifest specifies "plugin_example_"
        manifest = PluginManifest(
            id="example",
            name="Example Plugin",
            version="1.0.0",
            description="Test",
            capabilities={PluginCapability.BACKEND},
            table_prefix="plugin_example_",
        )

        runner = PluginMigrationRunner(plugin_path, "example", manifest)

        # Should use manifest value, not derived "example_"
        assert runner._get_table_prefix() == "plugin_example_"

    def test_derives_prefix_when_manifest_missing(self, plugin_path: Path):
        """Test fallback to derivation when no manifest provided."""
        runner = PluginMigrationRunner(plugin_path, "time-tracking", manifest=None)

        # "time-tracking" -> "tt_" (initials of hyphenated words)
        assert runner._get_table_prefix() == "tt_"

    def test_derives_prefix_when_table_prefix_not_set(self, plugin_path: Path):
        """Test fallback to derivation when manifest has no table_prefix."""
        manifest = PluginManifest(
            id="my-cool-plugin",
            name="My Cool Plugin",
            version="1.0.0",
            description="Test",
            capabilities={PluginCapability.BACKEND},
            # table_prefix not set, defaults to None
        )

        runner = PluginMigrationRunner(plugin_path, "my-cool-plugin", manifest)

        # "my-cool-plugin" -> "mcp_" (initials)
        assert runner._get_table_prefix() == "mcp_"

    def test_derives_single_word_prefix(self, plugin_path: Path):
        """Test derivation for single-word plugin IDs."""
        runner = PluginMigrationRunner(plugin_path, "analytics", manifest=None)

        # Single word uses full name as prefix
        assert runner._get_table_prefix() == "analytics_"

    def test_derives_underscore_separated_prefix(self, plugin_path: Path):
        """Test derivation treats underscores like hyphens."""
        runner = PluginMigrationRunner(plugin_path, "data_export", manifest=None)

        # "data_export" -> "de_" (underscores converted to hyphens, then initials)
        assert runner._get_table_prefix() == "de_"
