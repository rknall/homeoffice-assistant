# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Expense schemas."""

import datetime
import uuid
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from src.models.enums import ExpenseCategory, ExpenseStatus, PaymentType


class ExpenseBase(BaseModel):
    """Base expense schema."""

    date: datetime.date
    amount: Decimal = Field(..., ge=0, decimal_places=2)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    payment_type: PaymentType
    category: ExpenseCategory
    description: str | None = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Validate that amount is positive and round to 2 decimal places."""
        if v <= 0:
            raise ValueError("Amount must be positive")
        return round(v, 2)


class ExpenseCreate(ExpenseBase):
    """Schema for creating an expense."""

    paperless_doc_id: int | None = None
    original_filename: str | None = Field(None, max_length=255)


class ExpenseUpdate(BaseModel):
    """Schema for updating an expense."""

    date: datetime.date | None = None
    amount: Decimal | None = Field(None, ge=0, decimal_places=2)
    currency: str | None = Field(None, min_length=3, max_length=3)
    payment_type: PaymentType | None = None
    category: ExpenseCategory | None = None
    description: str | None = None
    status: ExpenseStatus | None = None
    paperless_doc_id: int | None = None
    original_filename: str | None = Field(None, max_length=255)

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal | None) -> Decimal | None:
        """Validate that amount is positive and round to 2 decimal places."""
        if v is not None:
            if v <= 0:
                raise ValueError("Amount must be positive")
            return round(v, 2)
        return v


class ExpenseResponse(BaseModel):
    """Schema for expense response."""

    id: uuid.UUID
    event_id: uuid.UUID
    paperless_doc_id: int | None
    date: datetime.date
    amount: Decimal
    currency: str
    payment_type: PaymentType
    category: ExpenseCategory
    description: str | None
    status: ExpenseStatus
    original_filename: str | None
    # Currency conversion fields
    converted_amount: Decimal | None
    exchange_rate: Decimal | None
    rate_date: datetime.date | None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class ExpenseBulkUpdate(BaseModel):
    """Schema for bulk updating expense payment types."""

    expense_ids: list[uuid.UUID]
    payment_type: PaymentType
