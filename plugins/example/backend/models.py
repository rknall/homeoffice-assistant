# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Example plugin database models."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID

from src.database import Base


class ExampleNote(Base):
    """Simple note model for the example plugin.

    Demonstrates how plugins can define their own database tables.
    The table will be prefixed with the plugin ID during migration.
    """

    __tablename__ = "plugin_example_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<ExampleNote(id={self.id}, title={self.title!r})>"
