# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Company schemas."""
import datetime

from pydantic import BaseModel, EmailStr, Field

from src.models.enums import CompanyType


class CompanyBase(BaseModel):
    """Base company schema."""

    name: str = Field(..., min_length=1, max_length=200)
    type: CompanyType


class CompanyCreate(CompanyBase):
    """Schema for creating a company."""

    paperless_storage_path_id: int | None = None
    expense_recipient_email: EmailStr | None = None
    expense_recipient_name: str | None = Field(None, max_length=200)
    report_recipients: list[dict[str, str]] | None = None


class CompanyUpdate(BaseModel):
    """Schema for updating a company."""

    name: str | None = Field(None, min_length=1, max_length=200)
    type: CompanyType | None = None
    paperless_storage_path_id: int | None = None
    expense_recipient_email: EmailStr | None = None
    expense_recipient_name: str | None = Field(None, max_length=200)
    report_recipients: list[dict[str, str]] | None = None


class CompanyResponse(BaseModel):
    """Schema for company response."""

    id: str
    name: str
    type: CompanyType
    paperless_storage_path_id: int | None
    expense_recipient_email: str | None
    expense_recipient_name: str | None
    report_recipients: list[dict[str, str]] | None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}
