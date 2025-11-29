"""Company model for organizing events."""
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin
from src.models.enums import CompanyType

if TYPE_CHECKING:
    from src.models.email_template import EmailTemplate
    from src.models.event import Event


class Company(Base, TimestampMixin):
    """Company model for organizing events and expenses."""

    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[CompanyType] = mapped_column(
        Enum(CompanyType),
        nullable=False,
    )
    paperless_storage_path_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    expense_recipient_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    expense_recipient_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    report_recipients: Mapped[str | None] = mapped_column(
        Text,  # JSON array stored as text
        nullable=True,
    )

    # Relationships
    events: Mapped[list["Event"]] = relationship(
        "Event",
        back_populates="company",
        cascade="all, delete-orphan",
    )
    email_templates: Mapped[list["EmailTemplate"]] = relationship(
        "EmailTemplate",
        back_populates="company",
        cascade="all, delete-orphan",
    )
