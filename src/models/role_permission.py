# src/models/role_permission.py
from __future__ import annotations

import uuid as uuid_lib
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, PrimaryKeyConstraint, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.permission import Permission
    from src.models.role import Role


class RolePermission(Base):
    """Association table mapping roles to their granted permissions."""

    __tablename__ = "role_permissions"

    role_id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_code: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("permissions.code", ondelete="CASCADE"),
        primary_key=True,
    )

    __table_args__ = (PrimaryKeyConstraint("role_id", "permission_code"),)

    role: Mapped[Role] = relationship("Role", back_populates="permissions")
    permission: Mapped[Permission] = relationship("Permission")
