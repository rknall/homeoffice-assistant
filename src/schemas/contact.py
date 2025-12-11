# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Contact schemas."""

import datetime
import uuid

from pydantic import BaseModel, EmailStr, Field


class ContactBase(BaseModel):
    """Base contact schema."""

    name: str = Field(..., min_length=1, max_length=200)
    company: str | None = Field(None, max_length=200)
    role: str | None = Field(None, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    notes: str | None = None
    met_on: datetime.date | None = None


class ContactCreate(ContactBase):
    """Schema for creating a contact."""

    pass


class ContactUpdate(BaseModel):
    """Schema for updating a contact."""

    name: str | None = Field(None, min_length=1, max_length=200)
    company: str | None = Field(None, max_length=200)
    role: str | None = Field(None, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    notes: str | None = None
    met_on: datetime.date | None = None


class ContactResponse(BaseModel):
    """Schema for contact response."""

    id: uuid.UUID
    event_id: uuid.UUID
    name: str
    company: str | None
    role: str | None
    email: str | None
    phone: str | None
    notes: str | None
    met_on: datetime.date | None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}
