"""Todo schemas."""
import datetime
from typing import Optional

from pydantic import BaseModel, Field

from src.models.enums import TodoCategory


class TodoBase(BaseModel):
    """Base todo schema."""

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    due_date: Optional[datetime.date] = None
    category: TodoCategory = TodoCategory.OTHER


class TodoCreate(TodoBase):
    """Schema for creating a todo."""

    pass


class TodoUpdate(BaseModel):
    """Schema for updating a todo."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    due_date: Optional[datetime.date] = None
    completed: Optional[bool] = None
    category: Optional[TodoCategory] = None


class TodoResponse(BaseModel):
    """Schema for todo response."""

    id: str
    event_id: str
    title: str
    description: Optional[str]
    due_date: Optional[datetime.date]
    completed: bool
    category: TodoCategory
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}
