"""Integration schemas."""
import datetime
from typing import Any, Optional

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

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    config: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


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
