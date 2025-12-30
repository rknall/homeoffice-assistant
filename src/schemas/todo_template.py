# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Todo template schemas."""

import datetime
import uuid

from pydantic import BaseModel, Field

from src.models.enums import OffsetReference, TodoCategory


class TodoTemplateBase(BaseModel):
    """Base todo template schema."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    category: TodoCategory = TodoCategory.OTHER
    days_offset: int = Field(default=0, description="Days offset from reference date")
    offset_reference: OffsetReference = OffsetReference.START_DATE
    template_set_name: str = Field(..., min_length=1, max_length=100)
    display_order: int = 0


class TodoTemplateCreate(TodoTemplateBase):
    """Schema for creating a user todo template."""

    pass


class TodoTemplateUpdate(BaseModel):
    """Schema for updating a todo template."""

    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    category: TodoCategory | None = None
    days_offset: int | None = None
    offset_reference: OffsetReference | None = None
    template_set_name: str | None = Field(None, min_length=1, max_length=100)
    display_order: int | None = None


class TodoTemplateResponse(BaseModel):
    """Schema for todo template response."""

    id: uuid.UUID
    title: str
    description: str | None
    category: TodoCategory
    days_offset: int
    offset_reference: OffsetReference
    template_set_name: str
    is_global: bool
    user_id: uuid.UUID | None
    display_order: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class TodoTemplateWithComputedDate(TodoTemplateResponse):
    """Template response with computed due date for a specific event."""

    computed_due_date: datetime.date | None = None


class TemplateSetResponse(BaseModel):
    """Schema for a template set with all its templates."""

    name: str
    templates: list[TodoTemplateResponse]
    is_global: bool


class TemplateSetWithComputedDates(BaseModel):
    """Template set with computed dates for a specific event."""

    name: str
    templates: list[TodoTemplateWithComputedDate]
    is_global: bool


class ApplyTemplatesRequest(BaseModel):
    """Request schema for applying templates to an event."""

    template_ids: list[uuid.UUID] = Field(
        ...,
        min_length=1,
        description="List of template IDs to apply",
    )


class ApplyTemplatesResponse(BaseModel):
    """Response schema after applying templates."""

    created_count: int
    todos_created: list[uuid.UUID]
