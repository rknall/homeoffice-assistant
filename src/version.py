# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Application version, read from pyproject.toml (single backend source)."""

import tomllib
from pathlib import Path

_PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"

with _PYPROJECT.open("rb") as _fh:
    APP_VERSION: str = tomllib.load(_fh)["project"]["version"]
