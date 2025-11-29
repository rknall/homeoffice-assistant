# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Contact schemas."""
import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class ContactBase(BaseModel):
    """Base contact schema."""

    name: str = Field(..., min_length=1, max_length=200)
    company: Optional[str] = Field(None, max_length=200)
    role: Optional[str] = Field(None, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    met_on: Optional[datetime.date] = None


class ContactCreate(ContactBase):
    """Schema for creating a contact."""

    pass


class ContactUpdate(BaseModel):
    """Schema for updating a contact."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    company: Optional[str] = Field(None, max_length=200)
    role: Optional[str] = Field(None, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    met_on: Optional[datetime.date] = None


class ContactResponse(BaseModel):
    """Schema for contact response."""

    id: str
    event_id: str
    name: str
    company: Optional[str]
    role: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    notes: Optional[str]
    met_on: Optional[datetime.date]
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}
