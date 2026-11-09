# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Check plugin Python requirements against the installed environment."""

from importlib.metadata import PackageNotFoundError, version

from packaging.requirements import Requirement


def unsatisfied_requirements(requirements: list[str]) -> list[str]:
    """Return the requirements the running environment does not satisfy.

    Args:
        requirements: PEP 508 requirement strings, e.g. "holidays>=0.62".

    Returns:
        The input strings, in order, whose distribution is not installed or
        whose installed version is outside the specifier. A requirement
        whose environment marker does not apply counts as satisfied.

    Raises:
        packaging.requirements.InvalidRequirement: If a string is not PEP 508.
    """
    missing: list[str] = []
    for spec in requirements:
        requirement = Requirement(spec)
        if requirement.marker is not None and not requirement.marker.evaluate():
            continue
        try:
            installed = version(requirement.name)
        except PackageNotFoundError:
            missing.append(spec)
            continue
        if not requirement.specifier.contains(installed, prereleases=True):
            missing.append(spec)
    return missing
