# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Fail when a release tag disagrees with the version files.

Run from the repository root:
``uv run python scripts/check_release_tag.py v0.5.0-dev7``.
The tag may carry a trailing pre-release number (``-dev7``); the files hold the
version without it (``0.5.0-dev``).
"""

import json
import re
import sys
import tomllib
from pathlib import Path

TAG_PATTERN = re.compile(r"^v(\d+\.\d+\.\d+)(?:-([a-z]+)(\d*))?$")
ROOT = Path(__file__).resolve().parents[1]


def expected_version(tag: str) -> str:
    """Map a release tag to the version the version files must hold.

    Args:
        tag: Git tag such as ``v0.3.0-beta1`` or ``v0.2.3``.

    Returns:
        The version without the leading ``v`` and without the pre-release
        number, e.g. ``0.3.0-beta``.

    Raises:
        ValueError: If the tag does not match the release tag format.
    """
    match = TAG_PATTERN.fullmatch(tag)
    if match is None:
        raise ValueError(f"Invalid release tag: {tag!r}")
    base, suffix, _number = match.groups()
    return f"{base}-{suffix}" if suffix else base


def file_versions(root: Path = ROOT) -> dict[str, str]:
    """Read the versions as written in pyproject.toml and package.json.

    Args:
        root: Repository root.

    Returns:
        Mapping of file name to its version string.
    """
    with (root / "pyproject.toml").open("rb") as fh:
        pyproject = tomllib.load(fh)["project"]["version"]
    package = json.loads((root / "frontend" / "package.json").read_text())["version"]
    return {"pyproject.toml": pyproject, "frontend/package.json": package}


def check_tag(tag: str, root: Path = ROOT) -> list[str]:
    """Compare a tag with the version files.

    Args:
        tag: Git tag to check.
        root: Repository root.

    Returns:
        One message per mismatch; empty when the tag is consistent.

    Raises:
        ValueError: If the tag does not match the release tag format.
    """
    expected = expected_version(tag)
    return [
        f"{name} has version {version}, tag {tag} expects {expected}"
        for name, version in file_versions(root).items()
        if version != expected
    ]


def main(argv: list[str]) -> int:
    """Check the tag given on the command line.

    Args:
        argv: Command line arguments without the program name.

    Returns:
        0 when the tag matches both version files, otherwise 1 (or 2 on misuse).
    """
    if len(argv) != 1:
        print("usage: check_release_tag.py <tag>", file=sys.stderr)
        return 2
    try:
        problems = check_tag(argv[0])
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
