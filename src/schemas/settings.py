"""Settings schemas."""
from typing import Literal, Optional

from pydantic import BaseModel, Field


# Date format options
DateFormatType = Literal["YYYY-MM-DD", "DD.MM.YYYY", "DD/MM/YYYY", "MM/DD/YYYY"]

# Time format options
TimeFormatType = Literal["24h", "12h"]


class LocaleSettingsResponse(BaseModel):
    """Response schema for locale settings."""

    date_format: DateFormatType = Field(default="YYYY-MM-DD")
    time_format: TimeFormatType = Field(default="24h")
    timezone: str = Field(default="UTC")


class LocaleSettingsUpdate(BaseModel):
    """Schema for updating locale settings."""

    date_format: Optional[DateFormatType] = None
    time_format: Optional[TimeFormatType] = None
    timezone: Optional[str] = Field(None, max_length=50)
