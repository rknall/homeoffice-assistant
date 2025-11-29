# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Company schemas."""
import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from src.models.enums import CompanyType


class CompanyBase(BaseModel):
    """Base company schema."""

    name: str = Field(..., min_length=1, max_length=200)
    type: CompanyType


class CompanyCreate(CompanyBase):
    """Schema for creating a company."""

    paperless_storage_path_id: Optional[int] = None
    expense_recipient_email: Optional[EmailStr] = None
    expense_recipient_name: Optional[str] = Field(None, max_length=200)
    report_recipients: Optional[list[dict[str, str]]] = None


class CompanyUpdate(BaseModel):
    """Schema for updating a company."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    type: Optional[CompanyType] = None
    paperless_storage_path_id: Optional[int] = None
    expense_recipient_email: Optional[EmailStr] = None
    expense_recipient_name: Optional[str] = Field(None, max_length=200)
    report_recipients: Optional[list[dict[str, str]]] = None


class CompanyResponse(BaseModel):
    """Schema for company response."""

    id: str
    name: str
    type: CompanyType
    paperless_storage_path_id: Optional[int]
    expense_recipient_email: Optional[str]
    expense_recipient_name: Optional[str]
    report_recipients: Optional[list[dict[str, str]]]
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}
