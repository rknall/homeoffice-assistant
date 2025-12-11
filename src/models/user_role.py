# src/models/user_role.py
import uuid as uuid_lib
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.company import Company
    from src.models.role import Role
    from src.models.user import User


class UserRole(Base, TimestampMixin):
    """Association between a user, role, and company including assignment metadata."""

    __tablename__ = "user_roles"

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
    role_id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    company_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
    )
    assigned_by_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "role_id", "company_id", name="_user_role_company_uc"
        ),
    )

    user: Mapped[User] = relationship(
        "User", back_populates="user_roles", foreign_keys=[user_id]
    )
    role: Mapped[Role] = relationship("Role", back_populates="user_roles")
    company: Mapped[Company | None] = relationship(
        "Company", back_populates="user_roles"
    )
    assigned_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[assigned_by_id]
    )
