# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Integrations package."""

# Import providers to register them
from src.integrations import (
    immich,
    llm,
    paperless,
    smtp,
    unsplash,
)
from src.integrations.base import (
    DocumentProvider,
    EmailProvider,
    ImageSearchProvider,
    IntegrationProvider,
    LlmProvider,
    PhotoProvider,
)
from src.integrations.registry import IntegrationRegistry

__all__ = [
    "DocumentProvider",
    "EmailProvider",
    "ImageSearchProvider",
    "IntegrationProvider",
    "IntegrationRegistry",
    "LlmProvider",
    "PhotoProvider",
    "immich",
    "llm",
    "paperless",
    "smtp",
    "unsplash",
]
