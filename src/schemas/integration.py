# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Integration schemas."""
import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.models.enums import IntegrationType


class IntegrationConfigBase(BaseModel):
    """Base integration config schema."""

    integration_type: IntegrationType
    name: str = Field(..., min_length=1, max_length=100)


class IntegrationConfigCreate(IntegrationConfigBase):
    """Schema for creating an integration config."""

    config: dict[str, Any]


class IntegrationConfigUpdate(BaseModel):
    """Schema for updating an integration config."""

    name: str | None = Field(None, min_length=1, max_length=100)
    config: dict[str, Any] | None = None
    is_active: bool | None = None


class IntegrationConfigResponse(BaseModel):
    """Schema for integration config response (without secrets)."""

    id: str
    integration_type: IntegrationType
    name: str
    is_active: bool
    created_by: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class IntegrationConfigDetailResponse(IntegrationConfigResponse):
    """Schema for integration config detail response (with masked secrets)."""

    config: dict[str, Any]


class IntegrationTypeInfo(BaseModel):
    """Schema for integration type information."""

    type: str
    name: str
    config_schema: dict[str, Any]


class IntegrationTestResult(BaseModel):
    """Schema for integration connection test result."""

    success: bool
    message: str


class StoragePathResponse(BaseModel):
    """Schema for Paperless storage path."""

    id: int
    name: str
    path: str


class TagResponse(BaseModel):
    """Schema for Paperless tag."""

    id: int
    name: str


class CustomFieldResponse(BaseModel):
    """Schema for Paperless custom field."""

    id: int
    name: str
    data_type: str
    extra_data: dict[str, Any] | None = None


class CustomFieldChoicesResponse(BaseModel):
    """Schema for custom field choices."""

    choices: list[str]


class CustomFieldChoice(BaseModel):
    """Schema for a single custom field choice with label and value."""

    label: str
    value: str


class EventCustomFieldChoicesResponse(BaseModel):
    """Schema for event custom field choices from Paperless."""

    available: bool
    custom_field_name: str
    choices: list[CustomFieldChoice]


class AddChoiceRequest(BaseModel):
    """Schema for adding a choice to a custom field."""

    choice: str = Field(..., min_length=1, max_length=200)


class TestEmailRequest(BaseModel):
    """Schema for sending a test email."""

    to_email: str = Field(..., min_length=1, max_length=200)


class TestEmailResponse(BaseModel):
    """Schema for test email response."""

    success: bool
    message: str


class DocumentResponse(BaseModel):
    """Schema for a Paperless document."""

    id: int
    title: str
    created: str | None = None
    added: str | None = None
    original_file_name: str
    correspondent: int | None = None
    document_type: int | None = None
    archive_serial_number: int | None = None


class DeleteDocumentRequest(BaseModel):
    """Schema for deleting a document."""

    document_id: int
