# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Company contact model for organizational contacts."""

from __future__ import annotations

import uuid as uuid_lib
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.company import Company


class CompanyContact(Base, TimestampMixin):
    """Contact associated with a company.

    Different from event contacts - these are organizational contacts
    that can receive reports, invoices, etc. Each contact can have
    multiple contact types (tags) and one contact per company can be
    marked as the main contact.
    """

    __tablename__ = "company_contacts"

    id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid_lib.uuid4,
    )
    company_id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Contact information
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    department: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Contact types as JSON array of strings (e.g., ["billing", "hr"])
    contact_types: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
    )

    # Main contact flag - only one per company should be True
    is_main_contact: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    company: Mapped[Company] = relationship(
        "Company",
        back_populates="contacts",
    )
