# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Shared translation of provider failures into HTTP errors."""

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import HTTPException

from src.services.integration_service import ProviderError


@contextmanager
def provider_errors() -> Iterator[None]:
    """Report a provider that cannot be opened as an HTTP error."""
    try:
        yield
    except ProviderError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
