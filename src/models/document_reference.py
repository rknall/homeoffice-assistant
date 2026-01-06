# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Document reference model for Paperless-ngx integration."""

from __future__ import annotations

import uuid as uuid_lib
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.event import Event


class DocumentReference(Base, TimestampMixin):
    """Document reference model linking Paperless documents to events.

    This allows linking non-expense documents (contracts, itineraries,
    confirmations, etc.) to events without creating expense records.
    """

    __tablename__ = "document_references"
    __table_args__ = (
        UniqueConstraint(
            "event_id", "paperless_doc_id", name="uq_document_reference_event_doc"
        ),
    )

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
    paperless_doc_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # contract, itinerary, confirmation, other
    include_in_report: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    event: Mapped[Event] = relationship("Event", back_populates="document_references")
