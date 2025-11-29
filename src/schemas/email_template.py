"""Email template schemas."""
import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EmailTemplateBase(BaseModel):
    """Base email template schema."""

    name: str = Field(..., min_length=1, max_length=200)
    reason: str = Field(..., min_length=1, max_length=50)
    subject: str = Field(..., min_length=1, max_length=500)
    body_html: str = Field(..., min_length=1)
    body_text: str = Field(..., min_length=1)
    is_default: bool = False


class EmailTemplateCreate(EmailTemplateBase):
    """Schema for creating an email template."""

    company_id: Optional[str] = None


class EmailTemplateUpdate(BaseModel):
    """Schema for updating an email template."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    reason: Optional[str] = Field(None, min_length=1, max_length=50)
    subject: Optional[str] = Field(None, min_length=1, max_length=500)
    body_html: Optional[str] = Field(None, min_length=1)
    body_text: Optional[str] = Field(None, min_length=1)
    is_default: Optional[bool] = None


class EmailTemplateResponse(BaseModel):
    """Schema for email template response."""

    id: str
    name: str
    reason: str
    company_id: Optional[str]
    subject: str
    body_html: str
    body_text: str
    is_default: bool
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
    event_id: Optional[str] = None  # If provided, use real event data


class TemplatePreviewResponse(BaseModel):
    """Response for template preview."""

    subject: str
    body_html: str
    body_text: str
