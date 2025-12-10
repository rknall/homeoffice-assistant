# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for settings_service."""

from src.models import SystemSettings
from src.services import settings_service


def test_get_and_set_setting(db_session):
    assert settings_service.get_setting(db_session, "missing") is None
    settings_service.set_setting(db_session, "key", "value", is_encrypted=True)
    assert settings_service.get_setting(db_session, "key") == "value"
    setting = db_session.query(SystemSettings).filter_by(key="key").first()
    assert setting.is_encrypted is True


def test_locale_settings_defaults(db_session):
    settings = settings_service.get_locale_settings(db_session)
    assert settings["date_format"] == settings_service.DEFAULT_DATE_FORMAT


def test_update_locale_settings(db_session):
    updated = settings_service.update_locale_settings(
        db_session, date_format="DD.MM.YYYY", timezone="Europe/Vienna"
    )
    assert updated["date_format"] == "DD.MM.YYYY"
    assert updated["timezone"] == "Europe/Vienna"
