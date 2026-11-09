# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for the plugin dependency check."""

import pytest
from packaging.requirements import InvalidRequirement

from scripts.plugin_deps import main
from src.plugins.dependencies import unsatisfied_requirements


def test_installed_requirement_is_satisfied() -> None:
    """An installed package inside the specifier is not reported."""
    assert unsatisfied_requirements(["holidays>=0.62"]) == []


def test_unsatisfied_requirements_keep_input_order() -> None:
    """Too-new and missing packages are returned in input order."""
    requirements = ["holidays>=999", "holidays>=0.62", "hoa-nonexistent-pkg>=1"]
    assert unsatisfied_requirements(requirements) == [
        "holidays>=999",
        "hoa-nonexistent-pkg>=1",
    ]


def test_marker_that_does_not_apply_is_skipped() -> None:
    """A requirement whose marker is false counts as satisfied."""
    assert unsatisfied_requirements(['foo>=1; python_version < "3"']) == []


def test_invalid_requirement_raises() -> None:
    """A string that is not PEP 508 raises InvalidRequirement."""
    with pytest.raises(InvalidRequirement):
        unsatisfied_requirements(["not a requirement!!"])


def test_bundled_plugins_are_satisfied() -> None:
    """The script exits 0 for the plugins shipped in the repository."""
    assert main() == 0
