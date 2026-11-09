# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Fail when a plugin requires a package the locked environment lacks.

Run from the repository root: ``uv run python -m scripts.plugin_deps``.
"""

import sys
from pathlib import Path

from src.plugins.dependencies import unsatisfied_requirements
from src.plugins.loader import PluginLoader


def main() -> int:
    """Print every unsatisfied plugin requirement.

    Returns:
        1 when at least one requirement is unsatisfied, otherwise 0.
    """
    loader = PluginLoader(Path("plugins"))
    failed = False
    for _, manifest in loader.discover_plugins():
        for requirement in unsatisfied_requirements(manifest.python_dependencies):
            print(f"{manifest.id}: {requirement}")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
