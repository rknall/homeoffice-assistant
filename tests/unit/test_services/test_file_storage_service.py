# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for file_storage_service."""

import uuid
from pathlib import Path

import pytest

from src.services import file_storage_service as fss

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 8
GIF = b"GIF89a" + b"0" * 8
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 "


@pytest.mark.parametrize(
    ("name", "content"),
    [("a.png", PNG), ("a.GIF", GIF), ("a.webp", WEBP), ("a.jpeg", b"\xff\xd8\xff")],
)
def test_validate_image_accepts_matching_content(name: str, content: bytes) -> None:
    assert (
        fss.validate_image(name, content, fss.AVATAR_TYPES) == Path(name).suffix.lower()
    )


@pytest.mark.parametrize(
    ("name", "content", "message"),
    [
        (None, PNG, "No file"),
        ("a.exe", PNG, "not allowed"),
        ("a.svg", b"<svg/>", "not allowed"),
        ("a.png", GIF, "does not match"),
    ],
)
def test_validate_image_rejects(name: str | None, content: bytes, message: str) -> None:
    with pytest.raises(fss.FileValidationError, match=message):
        fss.validate_image(name, content, fss.AVATAR_TYPES)


def test_validate_svg_allows_fragment_href() -> None:
    fss.validate_svg(
        b'<svg xmlns="http://www.w3.org/2000/svg"><use href="#shape"/></svg>'
    )


def test_avatar_url_maps_legacy_and_current_values() -> None:
    assert fss.avatar_url(None) is None
    assert fss.avatar_url("/static/avatars/a.png") == "/avatars/a.png"
    assert fss.avatar_url("/avatars/a.png") == "/avatars/a.png"


def test_save_avatar_replaces_old_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(fss, "AVATAR_DIR", tmp_path)
    owner = uuid.uuid4()

    first = fss.save_avatar(owner, "a.png", PNG, None)
    second = fss.save_avatar(owner, "b.png", PNG, first)

    assert [p.name for p in tmp_path.iterdir()] == [Path(second).name]


def test_remove_only_touches_the_storage_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stored value with a path never deletes a file outside the directory."""
    storage = tmp_path / "logos"
    storage.mkdir()
    outside = tmp_path / "keep.txt"
    outside.write_text("x")
    monkeypatch.setattr(fss, "LOGO_DIR", storage)

    fss.remove_logo("../keep.txt")

    assert outside.exists()
