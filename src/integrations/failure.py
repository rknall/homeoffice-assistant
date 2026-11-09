# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Client-safe categories for provider failures."""

import smtplib
import socket

import httpx

UNREACHABLE = "server unreachable"
AUTH_FAILED = "authentication failed"
UNEXPECTED = "unexpected response"


def failure_category(exc: BaseException) -> str:
    """Name what went wrong with a provider call without exposing its text.

    The category comes from the exception class (and, for wrapped errors, the
    class of the exception that caused it), never from the message, so no
    host names, paths or secrets leak to the client.

    Args:
        exc: The exception raised by the provider call.

    Returns:
        One of "server unreachable", "authentication failed" or
        "unexpected response".
    """
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, smtplib.SMTPAuthenticationError):
            return AUTH_FAILED
        if isinstance(current, httpx.HTTPStatusError):
            if current.response.status_code in (401, 403):
                return AUTH_FAILED
            return UNEXPECTED
        if isinstance(
            current,
            httpx.TransportError
            | smtplib.SMTPConnectError
            | smtplib.SMTPServerDisconnected
            | ConnectionError
            | TimeoutError
            | socket.gaierror,
        ):
            return UNREACHABLE
        current = current.__cause__
    return UNEXPECTED
