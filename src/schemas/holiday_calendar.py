# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Holiday calendar configuration schemas."""

import datetime
import uuid

from pydantic import BaseModel, Field, field_validator


class HolidayCalendarBase(BaseModel):
    """Base holiday calendar schema."""

    country_code: str = Field(..., min_length=2, max_length=2)
    subdivision: str | None = Field(None, max_length=10)
    display_label: str = Field(..., min_length=1, max_length=20)

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        """Validate and uppercase country code."""
        return v.upper()

    @field_validator("subdivision")
    @classmethod
    def validate_subdivision(cls, v: str | None) -> str | None:
        """Uppercase subdivision code if present."""
        if v is None:
            return v
        return v.upper()


class HolidayCalendarCreate(HolidayCalendarBase):
    """Schema for creating a holiday calendar configuration."""

    pass


class HolidayCalendarUpdate(BaseModel):
    """Schema for updating a holiday calendar configuration."""

    display_label: str | None = Field(None, min_length=1, max_length=20)


class HolidayCalendarResponse(BaseModel):
    """Schema for holiday calendar response."""

    id: uuid.UUID
    user_id: uuid.UUID
    country_code: str
    subdivision: str | None
    display_label: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class HolidayEntry(BaseModel):
    """A single holiday entry."""

    date: datetime.date
    name: str
    country_code: str
    subdivision: str | None
    display_label: str


class HolidaysResponse(BaseModel):
    """Response containing holidays for a date range."""

    holidays: list[HolidayEntry]


class CountryInfo(BaseModel):
    """Information about a supported country."""

    code: str
    name: str
    subdivisions: list[str]


class SupportedCountriesResponse(BaseModel):
    """Response containing all supported countries."""

    countries: list[CountryInfo]
