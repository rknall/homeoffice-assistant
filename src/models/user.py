# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""User model for authentication."""

from __future__ import annotations

import uuid as uuid_lib
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.event import Event
    from src.models.integration_config import IntegrationConfig
    from src.models.session import Session
    from src.models.todo_template import TodoTemplate
    from src.models.user_role import UserRole


class User(Base, TimestampMixin):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid_lib.uuid4,
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    use_gravatar: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    sessions: Mapped[list[Session]] = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    events: Mapped[list[Event]] = relationship(
        "Event",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    integration_configs: Mapped[list[IntegrationConfig]] = relationship(
        "IntegrationConfig",
        back_populates="created_by_user",
        cascade="all, delete-orphan",
    )
    user_roles: Mapped[list[UserRole]] = relationship(
        "UserRole",
        foreign_keys="[UserRole.user_id]",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    todo_templates: Mapped[list[TodoTemplate]] = relationship(
        "TodoTemplate",
        back_populates="user",
        cascade="all, delete-orphan",
    )
