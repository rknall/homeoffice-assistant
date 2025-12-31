# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Document reference schemas for Paperless-ngx integration."""

import datetime
import uuid
from typing import Literal

from pydantic import BaseModel

DocumentType = Literal["contract", "itinerary", "confirmation", "other"]


class DocumentReferenceCreate(BaseModel):
    """Schema for linking a document to an event."""

    paperless_doc_id: int
    title: str
    original_filename: str | None = None
    notes: str | None = None
    document_type: DocumentType | None = None
    include_in_report: bool = False


class DocumentReferenceUpdate(BaseModel):
    """Schema for updating a document reference."""

    notes: str | None = None
    document_type: DocumentType | None = None
    include_in_report: bool | None = None


class DocumentReferenceResponse(BaseModel):
    """Document reference response schema."""

    id: uuid.UUID
    event_id: uuid.UUID
    paperless_doc_id: int
    title: str
    original_filename: str | None
    notes: str | None
    document_type: str | None
    include_in_report: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}
