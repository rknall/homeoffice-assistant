# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Todo schemas."""

import datetime
import uuid

from pydantic import BaseModel, Field

from src.models.enums import TodoCategory


class TodoBase(BaseModel):
    """Base todo schema."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    due_date: datetime.date | None = None
    category: TodoCategory = TodoCategory.OTHER


class TodoCreate(TodoBase):
    """Schema for creating a todo."""

    pass


class TodoUpdate(BaseModel):
    """Schema for updating a todo."""

    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    due_date: datetime.date | None = None
    completed: bool | None = None
    category: TodoCategory | None = None


class TodoResponse(BaseModel):
    """Schema for todo response."""

    id: uuid.UUID
    event_id: uuid.UUID
    title: str
    description: str | None
    due_date: datetime.date | None
    completed: bool
    category: TodoCategory
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}
