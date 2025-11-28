"""Integration configuration model."""
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin
from src.models.enums import IntegrationType

if TYPE_CHECKING:
    from src.models.user import User


class IntegrationConfig(Base, TimestampMixin):
    """Integration configuration model with encrypted credentials."""

    __tablename__ = "integration_configs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    integration_type: Mapped[IntegrationType] = mapped_column(
        Enum(IntegrationType),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    config_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationships
    created_by_user: Mapped["User"] = relationship(
        "User",
        back_populates="integration_configs",
    )
