# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Time-tracking plugin settings and manifest metadata."""

import logging
from dataclasses import dataclass
from datetime import date
from functools import cache
from pathlib import Path
from typing import Any

from src.plugins.manifest import parse_manifest

from ..validators import ComplianceValidator, get_validator

logger = logging.getLogger(__name__)

MANIFEST_PATH = Path(__file__).resolve().parents[2] / "plugin.manifest.json"

DEFAULT_WORK_HOURS = 8.0
DEFAULT_BREAK_MINUTES = 30
DEFAULT_COUNTRY = "AT"


@cache
def plugin_version() -> str:
    """Return the plugin version declared in the manifest."""
    return parse_manifest(MANIFEST_PATH).version


@cache
def plugin_name() -> str:
    """Return the plugin display name declared in the manifest."""
    return parse_manifest(MANIFEST_PATH).name


@dataclass(frozen=True)
class TimeTrackingConfig:
    """Plugin settings the services use, with the built-in defaults."""

    default_work_hours: float = DEFAULT_WORK_HOURS
    default_break_minutes: int = DEFAULT_BREAK_MINUTES
    default_country: str = DEFAULT_COUNTRY

    @classmethod
    def from_settings(cls, settings: dict[str, Any]) -> TimeTrackingConfig:
        """Build the config from stored plugin settings.

        An unsupported country falls back to the default with a warning, so a
        mistyped setting cannot break every holiday lookup.

        Args:
            settings: Plugin settings as stored; missing keys use defaults.

        Returns:
            The service configuration.
        """
        country = str(settings.get("default_country", DEFAULT_COUNTRY))
        try:
            get_validator(country)
        except ValueError:
            logger.warning("Unsupported default_country %r, using AT", country)
            country = DEFAULT_COUNTRY
        return cls(
            default_work_hours=float(
                settings.get("default_work_hours", DEFAULT_WORK_HOURS)
            ),
            default_break_minutes=int(
                settings.get("default_break_minutes", DEFAULT_BREAK_MINUTES)
            ),
            default_country=country,
        )

    def validator(self) -> ComplianceValidator:
        """Return the compliance validator of the configured country."""
        return get_validator(self.default_country)

    def holiday_dates(self, year: int) -> set[date]:
        """Return the public holiday dates of the configured country."""
        return set(self.validator().get_public_holidays(year))
