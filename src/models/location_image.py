# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Location image cache model for Unsplash images."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class LocationImage(Base):
    """Cached location images from Unsplash."""

    __tablename__ = "location_images"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    city: Mapped[str | None] = mapped_column(String(200), nullable=True)
    country: Mapped[str] = mapped_column(String(200), nullable=False)
    unsplash_id: Mapped[str] = mapped_column(String(50), nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_url: Mapped[str] = mapped_column(String(500), nullable=False)
    photographer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    photographer_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_location_images_city_country", "city", "country"),
    )
