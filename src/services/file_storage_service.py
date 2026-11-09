# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Validation and storage of uploaded user avatars and company logos."""

import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

AVATAR_DIR = Path("static/avatars")
# The SPA catch-all serves files below static/ from the site root, so a file
# in static/avatars is reachable at /avatars/<name>.
AVATAR_URL_PREFIX = "/avatars/"
LOGO_DIR = Path("data/logos")
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

RASTER_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
SVG_TYPE = "image/svg+xml"
AVATAR_TYPES = RASTER_TYPES
LOGO_TYPES: dict[str, str] = {**RASTER_TYPES, ".svg": SVG_TYPE}

# A logo is shown as an image only: no scripts, no external loads, and the
# document is sandboxed should a browser open the URL directly.
LOGO_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'none'; style-src 'unsafe-inline'; sandbox"
    ),
    "X-Content-Type-Options": "nosniff",
}

_FORBIDDEN_SVG_TAGS = {"script", "foreignobject"}


class FileValidationError(ValueError):
    """An uploaded file is rejected; the message is safe to show the user."""


def _sniff_raster(content: bytes) -> str | None:
    """Return the media type the magic bytes of a raster image announce."""
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


def _local_name(name: str) -> str:
    """Strip an ElementTree ``{namespace}`` prefix and lower-case the name."""
    return name.rsplit("}", 1)[-1].lower()


def validate_svg(content: bytes) -> None:
    """Reject an SVG that could run code or load external content.

    Args:
        content: The raw SVG document.

    Raises:
        FileValidationError: When the document is not well-formed SVG, has a
            DOCTYPE or entity declaration, or contains ``script``,
            ``foreignObject``, ``on*`` event attributes, ``javascript:``
            values or a non-fragment ``href``.
    """
    # Rejecting every DOCTYPE first rules out entity expansion and external
    # entities, the XML attacks a plain stdlib parser is open to.
    lowered = content.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise FileValidationError("SVG must not contain DOCTYPE or entities")
    parser = ET.XMLPullParser(events=("end",))
    try:
        parser.feed(content)
        parser.close()
        elements = [element for _, element in parser.read_events()]
    except ET.ParseError as e:
        raise FileValidationError("File is not a valid SVG image") from e
    root = elements[-1] if elements else None
    if root is None or _local_name(root.tag) != "svg":
        raise FileValidationError("File is not a valid SVG image")
    for element in root.iter():
        if _local_name(element.tag) in _FORBIDDEN_SVG_TAGS:
            raise FileValidationError("SVG must not contain scripts or HTML")
        for raw_name, value in element.attrib.items():
            name = _local_name(raw_name)
            compact = "".join(value.split()).lower()
            if name.startswith("on") or "javascript:" in compact:
                raise FileValidationError("SVG must not contain scripts")
            if name == "href" and not value.strip().startswith("#"):
                raise FileValidationError("SVG must not reference external content")


def validate_image(
    filename: str | None, content: bytes, allowed: dict[str, str]
) -> str:
    """Check an upload's extension, size and content.

    Args:
        filename: The client's file name; only its extension is used.
        content: The uploaded bytes.
        allowed: Allowed extensions mapped to their media type.

    Returns:
        The lower-case extension of the accepted file.

    Raises:
        FileValidationError: When the name is missing, the extension is not
            allowed, the file is too large or its content does not match the
            extension.
    """
    if not filename:
        raise FileValidationError("No file provided")
    ext = Path(filename).suffix.lower()
    if ext not in allowed:
        raise FileValidationError(
            f"File type not allowed. Allowed: {', '.join(sorted(allowed))}"
        )
    if len(content) > MAX_FILE_SIZE:
        raise FileValidationError(
            f"File too large. Max size: {MAX_FILE_SIZE // (1024 * 1024)}MB"
        )
    if allowed[ext] == SVG_TYPE:
        validate_svg(content)
    elif _sniff_raster(content) != allowed[ext]:
        raise FileValidationError("File content does not match its type")
    return ext


def _write(directory: Path, prefix: str, ext: str, content: bytes) -> str:
    """Write ``content`` under a new unique name and return that name."""
    directory.mkdir(parents=True, exist_ok=True)
    name = f"{prefix}_{uuid.uuid4().hex[:8]}{ext}"
    (directory / name).write_bytes(content)
    return name


def _remove(directory: Path, name: str | None) -> None:
    """Delete a stored file; only its base name is used, so no path escapes."""
    if not name:
        return
    path = directory / Path(name).name
    if path.is_file():
        path.unlink()


def avatar_url(stored: str | None) -> str | None:
    """Return the public URL of a stored avatar.

    Older rows hold ``/static/avatars/<name>``, which the site does not serve;
    every value is mapped to ``/avatars/<name>``.

    Args:
        stored: The value of ``User.avatar_url``.

    Returns:
        The URL the browser can load, or None without an avatar.
    """
    if not stored:
        return None
    return AVATAR_URL_PREFIX + Path(stored).name


def save_avatar(
    owner_id: uuid.UUID, filename: str | None, content: bytes, old: str | None
) -> str:
    """Validate and store an avatar, removing the previous one.

    Args:
        owner_id: The user the avatar belongs to; prefixes the file name.
        filename: The client's file name.
        content: The uploaded bytes.
        old: The user's current ``avatar_url``, removed after the new file is
            written.

    Returns:
        The URL to store in ``User.avatar_url``.

    Raises:
        FileValidationError: When the upload is rejected.
    """
    ext = validate_image(filename, content, AVATAR_TYPES)
    name = _write(AVATAR_DIR, str(owner_id), ext, content)
    _remove(AVATAR_DIR, old)
    return AVATAR_URL_PREFIX + name


def remove_avatar(stored: str | None) -> None:
    """Delete the file behind a stored ``avatar_url``, if any."""
    _remove(AVATAR_DIR, stored)


def save_logo(
    company_id: uuid.UUID, filename: str | None, content: bytes, old: str | None
) -> str:
    """Validate and store a company logo, removing the previous one.

    Args:
        company_id: The company; prefixes the file name.
        filename: The client's file name.
        content: The uploaded bytes.
        old: The company's current ``logo_path``.

    Returns:
        The file name to store in ``Company.logo_path``.

    Raises:
        FileValidationError: When the upload is rejected.
    """
    ext = validate_image(filename, content, LOGO_TYPES)
    name = _write(LOGO_DIR, str(company_id), ext, content)
    _remove(LOGO_DIR, old)
    return name


def remove_logo(logo_path: str | None) -> None:
    """Delete a stored logo file, if any."""
    _remove(LOGO_DIR, logo_path)


def logo_file(logo_path: str) -> tuple[Path, str] | None:
    """Locate a stored logo and its media type.

    Args:
        logo_path: The company's ``logo_path``.

    Returns:
        The file path and media type, or None when the file is missing.
    """
    path = LOGO_DIR / Path(logo_path).name
    if not path.is_file():
        return None
    media_type = LOGO_TYPES.get(path.suffix.lower(), "application/octet-stream")
    return path, media_type
