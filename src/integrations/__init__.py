"""Integrations package."""
from src.integrations.base import DocumentProvider, EmailProvider, IntegrationProvider, PhotoProvider
from src.integrations.registry import IntegrationRegistry

# Import providers to register them
from src.integrations import paperless  # noqa: F401

__all__ = [
    "IntegrationProvider",
    "DocumentProvider",
    "PhotoProvider",
    "EmailProvider",
    "IntegrationRegistry",
]
