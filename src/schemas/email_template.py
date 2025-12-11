# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Email template schemas."""

import datetime
import uuid

from pydantic import BaseModel, Field

from src.models.enums import ContactType


class EmailTemplateBase(BaseModel):
    """Base email template schema."""

    name: str = Field(..., min_length=1, max_length=200)
    reason: str = Field(..., min_length=1, max_length=50)
    subject: str = Field(..., min_length=1, max_length=500)
    body_html: str = Field(..., min_length=1)
    body_text: str = Field(..., min_length=1)
    is_default: bool = False
    contact_types: list[ContactType] = Field(default_factory=list)


class EmailTemplateCreate(EmailTemplateBase):
    """Schema for creating an email template."""

    company_id: uuid.UUID | None = None


class EmailTemplateUpdate(BaseModel):
    """Schema for updating an email template."""

    name: str | None = Field(None, min_length=1, max_length=200)
    reason: str | None = Field(None, min_length=1, max_length=50)
    subject: str | None = Field(None, min_length=1, max_length=500)
    body_html: str | None = Field(None, min_length=1)
    body_text: str | None = Field(None, min_length=1)
    is_default: bool | None = None
    contact_types: list[ContactType] | None = None


class EmailTemplateResponse(BaseModel):
    """Schema for email template response."""

    id: uuid.UUID
    name: str
    reason: str
    company_id: uuid.UUID | None
    subject: str
    body_html: str
    body_text: str
    is_default: bool
    contact_types: list[ContactType]
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class TemplateVariableInfo(BaseModel):
    """Information about a template variable."""

    variable: str
    description: str
    example: str


class TemplateReason(BaseModel):
    """Information about a template reason."""

    reason: str
    description: str
    variables: list[TemplateVariableInfo]


class TemplatePreviewRequest(BaseModel):
    """Request for template preview."""

    subject: str
    body_html: str
    body_text: str
    reason: str
    event_id: uuid.UUID | None = None  # If provided, use real event data


class TemplatePreviewResponse(BaseModel):
    """Response for template preview."""

    subject: str
    body_html: str
    body_text: str
