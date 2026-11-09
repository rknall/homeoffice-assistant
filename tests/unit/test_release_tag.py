# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for the release tag check script."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_release_tag.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_release_tag", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_release_tag = _load()

EXISTING_TAGS = {
    "v0.2.3": "0.2.3",
    "v0.3.0": "0.3.0",
    "v0.3.0-alpha": "0.3.0-alpha",
    "v0.3.0-beta1": "0.3.0-beta",
    "v0.3.0-beta2": "0.3.0-beta",
    "v0.3.0-beta3": "0.3.0-beta",
    "v0.3.0-rc2": "0.3.0-rc",
    "v0.3.0-rc3": "0.3.0-rc",
    "v0.3.0-rc4": "0.3.0-rc",
    "v0.3.0-rc5": "0.3.0-rc",
    "v0.4.0-dev": "0.4.0-dev",
    "v0.5.0-dev1": "0.5.0-dev",
    "v0.5.0-dev2": "0.5.0-dev",
    "v0.5.0-dev3": "0.5.0-dev",
    "v0.5.0-dev4": "0.5.0-dev",
    "v0.5.0-dev5": "0.5.0-dev",
    "v0.5.0-dev6": "0.5.0-dev",
}


@pytest.mark.parametrize(("tag", "expected"), EXISTING_TAGS.items())
def test_expected_version_for_existing_tags(tag: str, expected: str) -> None:
    """Every tag in the repository history maps to its file version."""
    assert check_release_tag.expected_version(tag) == expected


@pytest.mark.parametrize("tag", ["0.5.0-dev6", "v0.5", "v0.5.0-Dev1", "v0.5.0-"])
def test_malformed_tags_are_rejected(tag: str) -> None:
    """Tags outside the release format raise and fail the CLI."""
    with pytest.raises(ValueError, match="Invalid release tag"):
        check_release_tag.expected_version(tag)
    assert check_release_tag.main([tag]) == 1


def test_matching_tag_passes_against_current_files() -> None:
    """A new pre-release number of the current version is consistent."""
    assert check_release_tag.check_tag("v0.5.0-dev7") == []
    assert check_release_tag.main(["v0.5.0-dev7"]) == 0


def test_mismatching_tag_fails_against_current_files() -> None:
    """A tag for another version reports both version files."""
    problems = check_release_tag.check_tag("v0.6.0")
    assert len(problems) == 2
    assert check_release_tag.main(["v0.6.0"]) == 1
