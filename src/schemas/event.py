# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Event schemas."""
import datetime

from pydantic import BaseModel, Field, model_validator

from src.models.enums import EventStatus


class EventBase(BaseModel):
    """Base event schema."""

    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    start_date: datetime.date
    end_date: datetime.date

    @model_validator(mode="after")
    def validate_dates(self) -> EventBase:
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class EventCreate(EventBase):
    """Schema for creating an event."""

    company_id: str
    status: EventStatus = EventStatus.PLANNING
    paperless_custom_field_value: str | None = None
    # Location fields
    city: str | None = None
    country: str | None = None
    country_code: str | None = Field(None, max_length=3)
    latitude: float | None = None
    longitude: float | None = None


class EventUpdate(BaseModel):
    """Schema for updating an event."""

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    company_id: str | None = None
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None
    status: EventStatus | None = None
    paperless_custom_field_value: str | None = None
    # Location fields
    city: str | None = None
    country: str | None = None
    country_code: str | None = Field(None, max_length=3)
    latitude: float | None = None
    longitude: float | None = None


class EventResponse(BaseModel):
    """Schema for event response."""

    id: str
    user_id: str
    company_id: str
    name: str
    description: str | None
    start_date: datetime.date
    end_date: datetime.date
    status: EventStatus
    external_tag: str | None
    paperless_custom_field_value: str | None = None
    # Location fields
    city: str | None = None
    country: str | None = None
    country_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class EventDetailResponse(EventResponse):
    """Schema for detailed event response with company info."""

    company_name: str | None = None
