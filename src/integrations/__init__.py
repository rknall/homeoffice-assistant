# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Integrations package."""
from src.integrations.base import DocumentProvider, EmailProvider, IntegrationProvider, PhotoProvider
from src.integrations.registry import IntegrationRegistry

# Import providers to register them
from src.integrations import paperless  # noqa: F401
from src.integrations import smtp  # noqa: F401

__all__ = [
    "IntegrationProvider",
    "DocumentProvider",
    "PhotoProvider",
    "EmailProvider",
    "IntegrationRegistry",
]
