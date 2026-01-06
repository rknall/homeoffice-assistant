# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Note model."""

from __future__ import annotations

import uuid as uuid_lib
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin
from src.models.enums import NoteType

if TYPE_CHECKING:
    from src.models.event import Event


class Note(Base, TimestampMixin):
    """Note model for event observations and report sections."""

    __tablename__ = "notes"

    id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid_lib.uuid4,
    )
    event_id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    note_type: Mapped[NoteType] = mapped_column(
        Enum(NoteType),
        default=NoteType.OBSERVATION,
        nullable=False,
    )

    # Relationships
    event: Mapped[Event] = relationship("Event", back_populates="notes")
