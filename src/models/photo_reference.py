# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Photo reference model for Immich integration."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.event import Event


class PhotoReference(Base, TimestampMixin):
    """Photo reference model linking Immich assets to events."""

    __tablename__ = "photo_references"

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
    immich_asset_id: Mapped[str] = mapped_column(String(100), nullable=False)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    include_in_report: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Photo metadata from Immich
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    event: Mapped[Event] = relationship("Event", back_populates="photo_references")
