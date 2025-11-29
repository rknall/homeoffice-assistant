# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Common schema types."""
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    total: int
    page: int
    per_page: int
    pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    data: list[T]
    meta: PaginationMeta


class HealthResponse(BaseModel):
    """Health check response."""

    status: str


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str
