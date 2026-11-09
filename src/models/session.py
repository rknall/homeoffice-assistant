# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Session model for authentication."""

import uuid as uuid_lib
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.utils.time import utc_now

if TYPE_CHECKING:
    from src.models.user import User


class Session(Base):
    """Session model for user authentication."""

    __tablename__ = "sessions"

    id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid_lib.uuid4,
    )
    user_id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False,
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="sessions")
