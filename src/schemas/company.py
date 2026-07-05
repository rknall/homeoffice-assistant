# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Company schemas."""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from pydantic import BaseModel, Field

from src.models.enums import CompanyType


class CompanyBase(BaseModel):
    """Base company schema."""

    name: str = Field(..., min_length=1, max_length=200)
    type: CompanyType


class CompanyCreate(CompanyBase):
    """Schema for creating a company."""

    paperless_storage_path_id: int | None = None
    report_recipients: list[dict[str, str]] | None = None
    webpage: str | None = Field(None, max_length=500)
    address: str | None = None
    country: str | None = Field(None, max_length=100)


class CompanyUpdate(BaseModel):
    """Schema for updating a company."""

    name: str | None = Field(None, min_length=1, max_length=200)
    type: CompanyType | None = None
    paperless_storage_path_id: int | None = None
    report_recipients: list[dict[str, str]] | None = None
    webpage: str | None = Field(None, max_length=500)
    address: str | None = None
    country: str | None = Field(None, max_length=100)


class CompanyResponse(BaseModel):
    """Schema for company response."""

    id: uuid.UUID
    name: str
    type: CompanyType
    paperless_storage_path_id: int | None
    report_recipients: list[dict[str, str]] | None
    webpage: str | None = None
    address: str | None = None
    country: str | None = None
    logo_path: str | None = None
    contacts: list[Any] = []  # CompanyContactResponse, forward reference
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}
