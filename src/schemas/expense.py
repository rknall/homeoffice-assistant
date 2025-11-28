"""Expense schemas."""
import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from src.models.enums import ExpenseCategory, ExpenseStatus, PaymentType


class ExpenseBase(BaseModel):
    """Base expense schema."""

    date: datetime.date
    amount: Decimal = Field(..., ge=0, decimal_places=2)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    payment_type: PaymentType
    category: ExpenseCategory
    description: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be positive")
        return round(v, 2)


class ExpenseCreate(ExpenseBase):
    """Schema for creating an expense."""

    paperless_doc_id: Optional[int] = None
    original_filename: Optional[str] = Field(None, max_length=255)


class ExpenseUpdate(BaseModel):
    """Schema for updating an expense."""

    date: Optional[datetime.date] = None
    amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    payment_type: Optional[PaymentType] = None
    category: Optional[ExpenseCategory] = None
    description: Optional[str] = None
    status: Optional[ExpenseStatus] = None
    paperless_doc_id: Optional[int] = None
    original_filename: Optional[str] = Field(None, max_length=255)

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            if v <= 0:
                raise ValueError("Amount must be positive")
            return round(v, 2)
        return v


class ExpenseResponse(BaseModel):
    """Schema for expense response."""

    id: str
    event_id: str
    paperless_doc_id: Optional[int]
    date: datetime.date
    amount: Decimal
    currency: str
    payment_type: PaymentType
    category: ExpenseCategory
    description: Optional[str]
    status: ExpenseStatus
    original_filename: Optional[str]
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class ExpenseBulkUpdate(BaseModel):
    """Schema for bulk updating expense payment types."""

    expense_ids: list[str]
    payment_type: PaymentType
