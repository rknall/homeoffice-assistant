# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Event schemas."""

import datetime
import uuid
from typing import Self

from pydantic import BaseModel, Field, computed_field, model_validator

from src.models.enums import EventStatus


def compute_event_status(start_date: datetime.date, end_date: datetime.date) -> EventStatus:
    """Compute event status from dates.

    - UPCOMING: start_date > today
    - ACTIVE: start_date <= today <= end_date
    - PAST: end_date < today
    """
    today = datetime.date.today()
    if start_date > today:
        return EventStatus.UPCOMING
    elif end_date < today:
        return EventStatus.PAST
    else:
        return EventStatus.ACTIVE


class EventBase(BaseModel):
    """Base event schema."""

    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    start_date: datetime.date
    end_date: datetime.date

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        """Ensure end_date is on or after start_date."""
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class EventCreate(EventBase):
    """Schema for creating an event.

    Note: status is computed from dates, not set manually.
    """

    company_id: uuid.UUID
    paperless_custom_field_value: str | None = None
    # Location fields
    city: str | None = None
    country: str | None = None
    country_code: str | None = Field(None, max_length=3)
    latitude: float | None = None
    longitude: float | None = None
    # Cover image fields
    cover_image_url: str | None = None
    cover_thumbnail_url: str | None = None
    cover_photographer_name: str | None = None
    cover_photographer_url: str | None = None
    cover_image_position_y: int | None = Field(None, ge=0, le=100)


class EventUpdate(BaseModel):
    """Schema for updating an event.

    Note: status is computed from dates, not set manually.
    """

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    company_id: uuid.UUID | None = None
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None
    paperless_custom_field_value: str | None = None
    # Location fields
    city: str | None = None
    country: str | None = None
    country_code: str | None = Field(None, max_length=3)
    latitude: float | None = None
    longitude: float | None = None
    # Cover image fields
    cover_image_url: str | None = None
    cover_thumbnail_url: str | None = None
    cover_photographer_name: str | None = None
    cover_photographer_url: str | None = None
    cover_image_position_y: int | None = Field(None, ge=0, le=100)


class EventResponse(BaseModel):
    """Schema for event response.

    Note: status is computed from dates, not stored.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    company_id: uuid.UUID
    name: str
    description: str | None
    start_date: datetime.date
    end_date: datetime.date
    external_tag: str | None
    paperless_custom_field_value: str | None = None
    # Location fields
    city: str | None = None
    country: str | None = None
    country_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    # Cover image fields
    cover_image_url: str | None = None
    cover_thumbnail_url: str | None = None
    cover_photographer_name: str | None = None
    cover_photographer_url: str | None = None
    cover_image_position_y: int | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def status(self) -> EventStatus:
        """Compute status from event dates."""
        return compute_event_status(self.start_date, self.end_date)


class EventDetailResponse(EventResponse):
    """Schema for detailed event response with company info."""

    company_name: str | None = None


class EventWithSummary(EventDetailResponse):
    """Event response with expense and todo summaries for list views."""

    expense_count: int = 0
    expense_total: float = 0.0
    todo_count: int = 0
    todo_incomplete_count: int = 0
