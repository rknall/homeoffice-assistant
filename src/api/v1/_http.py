# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Small HTTP helpers shared by the API routers."""

from urllib.parse import quote

_UNSAFE_FALLBACK_CHARS = frozenset('";' + chr(92))


def content_disposition(filename: str, disposition: str = "attachment") -> str:
    """Build a Content-Disposition header value for a download.

    Emits an ASCII fallback ``filename`` plus an RFC 5987 ``filename*`` so
    names with quotes, newlines or non-ASCII characters stay valid.

    Args:
        filename: The file name offered to the client.
        disposition: ``attachment`` or ``inline``.

    Returns:
        The header value.
    """
    fallback = "".join(
        c
        if c.isascii() and c.isprintable() and c not in _UNSAFE_FALLBACK_CHARS
        else "_"
        for c in filename
    )
    encoded = quote(filename)
    return f"{disposition}; filename=\"{fallback}\"; filename*=UTF-8''{encoded}"
