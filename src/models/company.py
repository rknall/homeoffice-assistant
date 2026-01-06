# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Company model for organizing events."""

import uuid as uuid_lib
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin
from src.models.enums import CompanyType

if TYPE_CHECKING:
    from src.models.company_contact import CompanyContact
    from src.models.email_template import EmailTemplate
    from src.models.event import Event
    from src.models.user_role import UserRole


class Company(Base, TimestampMixin):
    """Company model for organizing events and expenses."""

    __tablename__ = "companies"

    id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid_lib.uuid4,
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
    report_recipients: Mapped[str | None] = mapped_column(
        Text,  # JSON array stored as text
        nullable=True,
    )

    # New general information fields
    webpage: Mapped[str | None] = mapped_column(String(500), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    logo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Currency for expense reports
    base_currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)

    # Relationships
    events: Mapped[list[Event]] = relationship(
        "Event",
        back_populates="company",
        cascade="all, delete-orphan",
    )
    email_templates: Mapped[list[EmailTemplate]] = relationship(
        "EmailTemplate",
        back_populates="company",
        cascade="all, delete-orphan",
    )
    contacts: Mapped[list[CompanyContact]] = relationship(
        "CompanyContact",
        back_populates="company",
        cascade="all, delete-orphan",
    )

    user_roles: Mapped[list[UserRole]] = relationship(
        "UserRole",
        back_populates="company",
        cascade="all, delete-orphan",
    )
