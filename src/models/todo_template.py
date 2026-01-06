# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Todo template model for predefined event tasks."""

import uuid as uuid_lib
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin
from src.models.enums import OffsetReference, TodoCategory

if TYPE_CHECKING:
    from src.models.user import User


class TodoTemplate(Base, TimestampMixin):
    """Todo template model for predefined event tasks.

    Templates can be global (system-shipped) or user-defined.
    Each template belongs to a template set (e.g., "Business Trip").
    Due dates are calculated relative to event start_date or end_date.
    """

    __tablename__ = "todo_templates"

    id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid_lib.uuid4,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[TodoCategory] = mapped_column(
        Enum(TodoCategory),
        default=TodoCategory.OTHER,
        nullable=False,
    )
    days_offset: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    offset_reference: Mapped[OffsetReference] = mapped_column(
        Enum(OffsetReference),
        default=OffsetReference.START_DATE,
        nullable=False,
    )
    template_set_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_global: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    user: Mapped[User | None] = relationship("User", back_populates="todo_templates")
