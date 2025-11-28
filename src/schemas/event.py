"""Event schemas."""
import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from src.models.enums import EventStatus


class EventBase(BaseModel):
    """Base event schema."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    start_date: datetime.date
    end_date: datetime.date

    @model_validator(mode="after")
    def validate_dates(self) -> "EventBase":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class EventCreate(EventBase):
    """Schema for creating an event."""

    company_id: str
    status: EventStatus = EventStatus.PLANNING
    paperless_custom_field_value: Optional[str] = None


class EventUpdate(BaseModel):
    """Schema for updating an event."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    company_id: Optional[str] = None
    start_date: Optional[datetime.date] = None
    end_date: Optional[datetime.date] = None
    status: Optional[EventStatus] = None
    paperless_custom_field_value: Optional[str] = None


class EventResponse(BaseModel):
    """Schema for event response."""

    id: str
    user_id: str
    company_id: str
    name: str
    description: Optional[str]
    start_date: datetime.date
    end_date: datetime.date
    status: EventStatus
    external_tag: Optional[str]
    paperless_custom_field_value: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class EventDetailResponse(EventResponse):
    """Schema for detailed event response with company info."""

    company_name: Optional[str] = None
