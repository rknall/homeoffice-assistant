# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for application settings validation."""

import pytest
from pydantic import ValidationError

from src.config import Settings


def test_secret_key_shorter_than_32_characters_is_rejected():
    with pytest.raises(ValidationError):
        Settings(secret_key="x" * 31, _env_file=None)


def test_secret_key_with_32_characters_is_accepted():
    settings = Settings(secret_key="x" * 32, _env_file=None)
    assert settings.secret_key == "x" * 32
