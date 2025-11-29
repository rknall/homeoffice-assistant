# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Note schemas."""
import datetime

from pydantic import BaseModel, Field

from src.models.enums import NoteType


class NoteBase(BaseModel):
    """Base note schema."""

    content: str = Field(..., min_length=1)
    note_type: NoteType = NoteType.OBSERVATION


class NoteCreate(NoteBase):
    """Schema for creating a note."""

    pass


class NoteUpdate(BaseModel):
    """Schema for updating a note."""

    content: str | None = Field(None, min_length=1)
    note_type: NoteType | None = None


class NoteResponse(BaseModel):
    """Schema for note response."""

    id: str
    event_id: str
    content: str
    note_type: NoteType
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}
