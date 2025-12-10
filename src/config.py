# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    secret_key: str
    database_url: str = "sqlite:///./data/homeoffice_assistant.db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
