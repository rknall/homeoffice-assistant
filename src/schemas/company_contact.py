# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Company contact schemas."""

import datetime
import uuid

from pydantic import BaseModel, EmailStr, Field

from src.models.enums import ContactType


class CompanyContactBase(BaseModel):
    """Base company contact schema."""

    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    phone: str | None = Field(None, max_length=50)
    title: str | None = Field(None, max_length=200)
    department: str | None = Field(None, max_length=200)
    notes: str | None = None
    contact_types: list[ContactType] = Field(default_factory=list)
    is_main_contact: bool = False


class CompanyContactCreate(CompanyContactBase):
    """Schema for creating a company contact."""

    pass


class CompanyContactUpdate(BaseModel):
    """Schema for updating a company contact."""

    name: str | None = Field(None, min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    title: str | None = Field(None, max_length=200)
    department: str | None = Field(None, max_length=200)
    notes: str | None = None
    contact_types: list[ContactType] | None = None
    is_main_contact: bool | None = None


class CompanyContactResponse(BaseModel):
    """Schema for company contact response."""

    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    email: str
    phone: str | None
    title: str | None
    department: str | None
    notes: str | None
    contact_types: list[ContactType]
    is_main_contact: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class TemplateContactValidation(BaseModel):
    """Validation result for template contacts."""

    is_valid: bool
    missing_types: list[ContactType]
    available_contacts: list[CompanyContactResponse]
    message: str
