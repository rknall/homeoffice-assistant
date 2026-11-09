# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Company time settings service."""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from ..models import (
    CompanyTimeSettings,
)


class CompanySettingsService:
    """Service for managing company time settings."""

    def __init__(self, db: Session) -> None:
        """Initialize the service.

        Args:
            db: Database session.
        """
        self.db = db

    def get_settings(self, company_id: UUID) -> CompanyTimeSettings | None:
        """Get time settings for a company.

        Args:
            company_id: The company ID.

        Returns:
            The company settings, or None if not found.
        """
        return (
            self.db.query(CompanyTimeSettings)
            .filter(CompanyTimeSettings.company_id == company_id)
            .first()
        )

    def get_or_create_settings(self, company_id: UUID) -> CompanyTimeSettings:
        """Get or create time settings for a company.

        Args:
            company_id: The company ID.

        Returns:
            The company settings.
        """
        settings = self.get_settings(company_id)
        if not settings:
            settings = CompanyTimeSettings(company_id=company_id)
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)
        return settings

    def update_settings(
        self,
        company_id: UUID,
        **kwargs: Any,
    ) -> CompanyTimeSettings:
        """Update company time settings.

        Args:
            company_id: The company ID.
            **kwargs: Fields to update.

        Returns:
            The updated settings.
        """
        settings = self.get_or_create_settings(company_id)

        for key, value in kwargs.items():
            if value is not None and hasattr(settings, key):
                setattr(settings, key, value)

        self.db.commit()
        self.db.refresh(settings)
        return settings


# --- Holiday Service ---
