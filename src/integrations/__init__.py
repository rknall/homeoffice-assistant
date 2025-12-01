# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Integrations package."""
# Import providers to register them
from src.integrations import (
    immich,  # noqa: F401
    paperless,  # noqa: F401
    smtp,  # noqa: F401
)
from src.integrations.base import (
    DocumentProvider,
    EmailProvider,
    IntegrationProvider,
    PhotoProvider,
)
from src.integrations.registry import IntegrationRegistry

__all__ = [
    "IntegrationProvider",
    "DocumentProvider",
    "PhotoProvider",
    "EmailProvider",
    "IntegrationRegistry",
]
