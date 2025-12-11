# src/models/role.py
import uuid as uuid_lib
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.role_permission import RolePermission
    from src.models.user_role import UserRole


class Role(Base, TimestampMixin):
    """Model representing a role with its metadata and relationships."""

    __tablename__ = "roles"

    id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid_lib.uuid4,
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    permissions: Mapped[list[RolePermission]] = relationship(
        "RolePermission", back_populates="role", cascade="all, delete-orphan"
    )
    user_roles: Mapped[list[UserRole]] = relationship(
        "UserRole", back_populates="role", cascade="all, delete-orphan"
    )
