# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Company calendar connection schemas."""

import datetime
import re
import uuid

from pydantic import BaseModel, Field, field_validator

from src.models.enums import CalendarType


class CompanyCalendarBase(BaseModel):
    """Base company calendar schema."""

    name: str = Field(..., min_length=1, max_length=200)
    calendar_type: CalendarType
    external_id: str = Field(..., min_length=1, max_length=500)
    color: str = Field(default="#3B82F6", max_length=7)
    is_active: bool = True
    sync_interval_minutes: int = Field(default=30, ge=5, le=1440)

    @field_validator("color")
    @classmethod
    def validate_hex_color(cls, v: str) -> str:
        """Validate hex color format."""
        if not re.match(r"^#[0-9A-Fa-f]{6}$", v):
            raise ValueError("Color must be a valid hex color (e.g., #3B82F6)")
        return v.upper()


class CompanyCalendarCreate(CompanyCalendarBase):
    """Schema for creating a company calendar connection."""

    pass


class CompanyCalendarUpdate(BaseModel):
    """Schema for updating a company calendar connection."""

    name: str | None = Field(None, min_length=1, max_length=200)
    external_id: str | None = Field(None, min_length=1, max_length=500)
    color: str | None = Field(None, max_length=7)
    is_active: bool | None = None
    sync_interval_minutes: int | None = Field(None, ge=5, le=1440)

    @field_validator("color")
    @classmethod
    def validate_hex_color(cls, v: str | None) -> str | None:
        """Validate hex color format."""
        if v is None:
            return v
        if not re.match(r"^#[0-9A-Fa-f]{6}$", v):
            raise ValueError("Color must be a valid hex color (e.g., #3B82F6)")
        return v.upper()


class CompanyCalendarResponse(BaseModel):
    """Schema for company calendar response."""

    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    calendar_type: CalendarType
    external_id: str
    color: str
    is_active: bool
    sync_interval_minutes: int
    last_synced_at: datetime.datetime | None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class CalendarSyncResult(BaseModel):
    """Result of a calendar sync operation."""

    calendar_id: uuid.UUID
    success: bool
    events_synced: int = 0
    error_message: str | None = None
