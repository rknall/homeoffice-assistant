# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Currency response schemas."""

from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, StringConstraints


def _normalise_currency(value: Any) -> Any:
    """Strip and upper-case a currency code string; pass other types through."""
    return value.strip().upper() if isinstance(value, str) else value


CurrencyCode = Annotated[
    str,
    BeforeValidator(_normalise_currency),
    StringConstraints(pattern=r"^[A-Z]{3}$"),
]
"""Currency code: three letters, stored upper-case."""


class CurrencyResponse(BaseModel):
    """Currency information response."""

    code: str
    name: str
