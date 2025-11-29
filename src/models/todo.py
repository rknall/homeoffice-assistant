# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Todo model."""
import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin
from src.models.enums import TodoCategory

if TYPE_CHECKING:
    from src.models.event import Event


class Todo(Base, TimestampMixin):
    """Todo model for event tasks."""

    __tablename__ = "todos"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    category: Mapped[TodoCategory] = mapped_column(
        Enum(TodoCategory),
        default=TodoCategory.OTHER,
        nullable=False,
    )

    # Relationships
    event: Mapped["Event"] = relationship("Event", back_populates="todos")
