# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Settings service for system-wide configuration."""

from sqlalchemy.orm import Session

from src.models import SystemSettings

# Default locale settings
DEFAULT_DATE_FORMAT = "YYYY-MM-DD"
DEFAULT_TIME_FORMAT = "24h"
DEFAULT_TIMEZONE = "UTC"

# Setting keys
SETTING_DATE_FORMAT = "locale_date_format"
SETTING_TIME_FORMAT = "locale_time_format"
SETTING_TIMEZONE = "locale_timezone"


def get_setting(db: Session, key: str) -> str | None:
    """Get a system setting by key."""
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    return setting.value if setting else None


def set_setting(db: Session, key: str, value: str, is_encrypted: bool = False) -> SystemSettings:
    """Set a system setting."""
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    if setting:
        setting.value = value
        setting.is_encrypted = is_encrypted
    else:
        setting = SystemSettings(key=key, value=value, is_encrypted=is_encrypted)
        db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


def get_locale_settings(db: Session) -> dict:
    """Get all locale settings."""
    return {
        "date_format": get_setting(db, SETTING_DATE_FORMAT) or DEFAULT_DATE_FORMAT,
        "time_format": get_setting(db, SETTING_TIME_FORMAT) or DEFAULT_TIME_FORMAT,
        "timezone": get_setting(db, SETTING_TIMEZONE) or DEFAULT_TIMEZONE,
    }


def update_locale_settings(
    db: Session,
    date_format: str | None = None,
    time_format: str | None = None,
    timezone: str | None = None,
) -> dict:
    """Update locale settings."""
    if date_format is not None:
        set_setting(db, SETTING_DATE_FORMAT, date_format)
    if time_format is not None:
        set_setting(db, SETTING_TIME_FORMAT, time_format)
    if timezone is not None:
        set_setting(db, SETTING_TIMEZONE, timezone)
    return get_locale_settings(db)
