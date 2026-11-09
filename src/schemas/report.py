# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Report request and response schemas."""

import uuid

from pydantic import BaseModel, EmailStr, Field

from src.schemas.expense import SubmissionMethod


class GenerateReportRequest(BaseModel):
    """Schema for generating expense report with expense selection."""

    expense_ids: list[uuid.UUID] | None = Field(
        None,
        description=(
            "Specific expense IDs to include. If not provided, includes all "
            "expenses. Reimbursed expenses are always excluded."
        ),
    )
    mark_as_submitted: bool = Field(
        True,
        description="Mark selected expenses as SUBMITTED after generation.",
    )
    submission_method: SubmissionMethod = Field(
        SubmissionMethod.DOWNLOAD,
        description="How the report is being submitted (download, email, portal).",
    )
    notes: str | None = Field(
        None,
        description="Optional notes about this submission.",
    )
    include_private: bool = Field(
        False,
        description="Include expenses marked as private (excluded by default).",
    )


class SendReportRequest(BaseModel):
    """Schema for sending expense report via email."""

    expense_ids: list[uuid.UUID] | None = Field(
        None,
        description=(
            "Specific expense IDs to include. If not provided, includes all "
            "expenses. Reimbursed expenses are always excluded."
        ),
    )
    mark_as_submitted: bool = Field(
        True,
        description="Mark selected expenses as SUBMITTED after sending.",
    )
    notes: str | None = Field(
        None,
        description="Optional notes about this submission.",
    )
    recipient_emails: list[EmailStr] | None = Field(
        None,
        description="Email addresses to send report to. Uses contacts if not provided.",
    )
    template_id: uuid.UUID | None = Field(
        None,
        description="Email template ID to use. If not provided, uses default template.",
    )
    auto_select_contacts: bool = Field(
        True,
        description="Automatically select contacts based on template contact types.",
    )


class SendReportResponse(BaseModel):
    """Schema for send report response."""

    success: bool
    message: str
    recipients: list[str] = []


class ReportPreviewResponse(BaseModel):
    """Schema for the expense report preview."""

    event_id: uuid.UUID
    event_name: str
    company_name: str | None = None
    start_date: str
    end_date: str
    expense_count: int
    documents_available: int
    total: float
    currency: str
    by_category: dict[str, float]
    by_payment_type: dict[str, float]
    paperless_configured: bool
    conversion_rates: dict[str, float] | None = None
