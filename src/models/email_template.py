# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Email template model for customizable email content."""

import uuid as uuid_lib
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.company import Company


class EmailTemplate(Base, TimestampMixin):
    """Email template with variable substitution support.

    Templates can be global (company_id=NULL) or company-specific.
    Company-specific templates override global ones for that company.
    """

    __tablename__ = "email_templates"

    id: Mapped[uuid_lib.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid_lib.uuid4,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    reason: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    company_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Contact types this template applies to (JSON array: ["billing", "hr"])
    contact_types: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
    )

    # Relationships
    company: Mapped[Company | None] = relationship(
        "Company",
        back_populates="email_templates",
    )
