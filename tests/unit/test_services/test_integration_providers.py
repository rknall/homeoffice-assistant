# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Unit tests for integration providers (Paperless, Immich, SMTP)."""

from __future__ import annotations

import smtplib
from datetime import datetime, timedelta
from typing import Any, ClassVar

import httpx
import pytest

from src.integrations.immich import ImmichProvider
from src.integrations.paperless import PaperlessProvider
from src.integrations.smtp import SmtpProvider


class FakeResponse:
    """Minimal httpx-like response for testing."""

    def __init__(
        self,
        status_code: int = 200,
        json_data: dict[str, Any] | None = None,
        content: bytes | None = None,
        headers: dict[str, str] | None = None,
        method: str = "GET",
        url: str = "http://test.local",
    ) -> None:
        self.status_code = status_code
        self._json_data = json_data or {}
        self.content = content or b""
        self.headers = headers or {}
        self._request = httpx.Request(method, url)

    def json(self) -> dict[str, Any]:
        return self._json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error",
                request=self._request,
                response=httpx.Response(self.status_code, request=self._request),
            )


class FakeClient:
    """Async HTTP client stub with queued responses."""

    def __init__(
        self,
        get_responses: list[FakeResponse] | None = None,
        post_responses: list[FakeResponse] | None = None,
        put_responses: list[FakeResponse] | None = None,
        delete_responses: list[FakeResponse] | None = None,
    ) -> None:
        self.get_responses = list(get_responses or [])
        self.post_responses = list(post_responses or [])
        self.put_responses = list(put_responses or [])
        self.delete_responses = list(delete_responses or [])
        self.calls: list[dict[str, Any]] = []

    async def get(self, url: str, params: dict[str, Any] | None = None) -> FakeResponse:
        self.calls.append({"method": "get", "url": url, "params": params})
        return self.get_responses.pop(0)

    async def post(
        self,
        url: str,
        json: dict[str, Any] | None = None,
    ) -> FakeResponse:
        self.calls.append({"method": "post", "url": url, "json": json})
        return self.post_responses.pop(0)

    async def put(
        self,
        url: str,
        json: dict[str, Any] | None = None,
    ) -> FakeResponse:
        self.calls.append({"method": "put", "url": url, "json": json})
        return self.put_responses.pop(0)

    async def delete(
        self,
        url: str,
        json: dict[str, Any] | None = None,
    ) -> FakeResponse:
        self.calls.append({"method": "delete", "url": url, "json": json})
        return self.delete_responses.pop(0)

    async def aclose(self) -> None:
        self.calls.append({"method": "close"})


# ---------------------- PaperlessProvider tests ---------------------- #


@pytest.mark.asyncio
async def test_paperless_health_check_and_close(monkeypatch):
    client = FakeClient(get_responses=[FakeResponse(200)])
    monkeypatch.setattr(
        "src.integrations.paperless.httpx.AsyncClient",
        lambda **kwargs: client,
    )
    provider = PaperlessProvider({"url": "https://paperless.local", "token": "t"})

    success, message = await provider.health_check()
    assert success is True
    assert "Connected" in message

    await provider.close()
    assert client.calls[-1]["method"] == "close"


@pytest.mark.asyncio
async def test_paperless_pagination_and_documents(monkeypatch):
    storage_responses = [
        FakeResponse(
            json_data={
                "results": [{"id": 1, "name": "First", "path": "a"}],
                "next": "https://paperless.local/api/storage_paths/?page=2",
            }
        ),
        FakeResponse(
            json_data={
                "results": [{"id": 2, "name": "Second", "path": "b"}],
                "next": None,
            }
        ),
        FakeResponse(
            json_data={"results": [{"id": 10, "name": "Travel"}], "next": None}
        ),
        FakeResponse(
            json_data={"results": [{"id": 10, "name": "Travel"}], "next": None}
        ),
        FakeResponse(
            json_data={
                "results": [
                    {
                        "id": 99,
                        "title": "Itinerary",
                        "added": "2024-01-01",
                        "tags": [10],
                        "storage_path": 2,
                        "original_file_name": "trip.pdf",
                    }
                ],
                "next": None,
            }
        ),
        FakeResponse(json_data={"original_file_name": "trip.pdf"}),
        FakeResponse(
            content=b"%PDF-1.4",
            headers={"content-type": "application/pdf"},
        ),
    ]
    post_responses = [
        FakeResponse(status_code=201, json_data={"id": 11, "name": "New"})
    ]

    client = FakeClient(get_responses=storage_responses, post_responses=post_responses)
    monkeypatch.setattr(
        "src.integrations.paperless.httpx.AsyncClient",
        lambda **kwargs: client,
    )

    provider = PaperlessProvider({"url": "https://paperless.local", "token": "t"})

    storage_paths = await provider.list_storage_paths()
    assert storage_paths == [
        {"id": 1, "name": "First", "path": "a"},
        {"id": 2, "name": "Second", "path": "b"},
    ]

    tags = await provider.list_tags()
    assert tags == [{"id": 10, "name": "Travel"}]

    created_tag = await provider.create_tag("New")
    assert created_tag == {"id": 11, "name": "New"}

    tag = await provider.get_tag_by_name("Travel")
    assert tag == {"id": 10, "name": "Travel"}

    documents = await provider.get_documents(
        tag_id=10, storage_path_id=2, custom_field_value="Trip"
    )
    assert documents[0]["id"] == 99
    doc_calls = [
        call for call in client.calls if call["url"].startswith("/api/documents/")
    ]
    assert doc_calls[0]["params"] == {
        "tags__id__in": 10,
        "storage_path__id": 2,
        "custom_fields__icontains": "Trip",
    }

    content, filename, content_type = await provider.download_document(99)
    assert filename == "trip.pdf"
    assert content_type == "application/pdf"
    assert content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_paperless_health_check_errors():
    provider = PaperlessProvider({"url": "https://paperless.local", "token": "t"})

    class FailingClient:
        async def get(self, *_args, **_kwargs):
            raise httpx.ConnectError(
                "boom",
                request=httpx.Request("GET", "https://paperless.local"),
            )

    provider._client = FailingClient()
    success, message = await provider.health_check()
    assert success is False
    assert "Connection failed" in message


# ---------------------- ImmichProvider tests ---------------------- #


@pytest.mark.asyncio
async def test_immich_health_and_metadata(monkeypatch):
    get_responses = [
        FakeResponse(status_code=200),  # ping
        FakeResponse(
            status_code=200,
            json_data={"major": 1, "minor": 2, "patch": 3},
        ),
        FakeResponse(json_data=[{"id": "album-asset"}]),  # list_albums
        FakeResponse(
            headers={"content-type": "image/png"}, content=b"\x89PNG"
        ),  # thumb
        FakeResponse(json_data={"id": "info-asset"}),  # info
        FakeResponse(
            headers={"content-disposition": 'attachment; filename="photo.jpg"'},
            content=b"\x00\x01",
        ),  # download
    ]
    post_responses = [
        FakeResponse(
            json_data={
                "assets": {
                    "items": [
                        {
                            "id": "asset-1",
                            "exifInfo": {"latitude": 48.2, "longitude": 16.37},
                        },
                        {
                            "id": "asset-2",
                            "exifInfo": {"latitude": 0.0, "longitude": 0.0},
                        },
                    ]
                }
            }
        ),
        FakeResponse(
            json_data={
                "assets": {
                    "items": [
                        {
                            "id": "asset-1",
                            "exifInfo": {"latitude": 48.2, "longitude": 16.37},
                        }
                    ]
                }
            }
        ),
        FakeResponse(json_data={"assets": {"items": [{"id": "date-only"}]}}),
    ]
    put_responses = [FakeResponse()]
    delete_responses = [FakeResponse()]

    client = FakeClient(
        get_responses=get_responses,
        post_responses=post_responses,
        put_responses=put_responses,
        delete_responses=delete_responses,
    )
    monkeypatch.setattr(
        "src.integrations.immich.httpx.AsyncClient",
        lambda **kwargs: client,
    )

    provider = ImmichProvider(
        {"url": "https://immich.local", "api_key": "k", "search_radius_km": 100}
    )

    success, message = await provider.health_check()
    assert success is True
    assert "Immich v1.2.3" in message

    albums = await provider.list_albums()
    assert albums[0]["id"] == "album-asset"

    all_assets = await provider.get_assets()
    assert {asset["id"] for asset in all_assets} == {"asset-1", "asset-2"}

    filtered = await provider.search_by_location_and_date(
        latitude=48.2,
        longitude=16.37,
        start_date=datetime.utcnow() - timedelta(days=1),
        end_date=datetime.utcnow(),
    )
    assert [asset["id"] for asset in filtered] == ["asset-1"]
    assert filtered[0]["_thumbnail_url"].endswith("/thumbnail?size=preview")
    assert filtered[0]["_distance_km"] == 0

    date_only = await provider.search_by_date_only(
        datetime.utcnow() - timedelta(days=2),
        datetime.utcnow(),
    )
    assert date_only == [
        {
            "id": "date-only",
            "_thumbnail_url": (
                "https://immich.local/api/assets/date-only/thumbnail?size=preview"
            ),
        }
    ]

    thumb_content, thumb_type = await provider.get_asset_thumbnail("asset-1")
    assert thumb_type == "image/png"
    assert thumb_content == b"\x89PNG"

    info = await provider.get_asset_info("asset-1")
    assert info["id"] == "info-asset"

    await provider.add_assets_to_album("album", ["asset-1"])
    await provider.remove_assets_from_album("album", ["asset-1"])

    download_content, filename, content_type = await provider.download_asset("asset-1")
    assert filename == "photo.jpg"
    assert content_type == "image/jpeg"
    assert download_content == b"\x00\x01"


@pytest.mark.asyncio
async def test_immich_error_handling(monkeypatch):
    class ErrorClient:
        async def get(self, *_args, **_kwargs):
            raise httpx.HTTPError("unreachable")

    monkeypatch.setattr(
        "src.integrations.immich.httpx.AsyncClient",
        lambda **kwargs: ErrorClient(),
    )
    provider = ImmichProvider({"url": "https://immich.local", "api_key": "k"})
    success, message = await provider.health_check()
    assert success is False
    assert "Connection error" in message


# ---------------------- SmtpProvider tests ---------------------- #


class FakeSMTP:
    """SMTP stub capturing actions."""

    instances: ClassVar[list[FakeSMTP]] = []

    def __init__(self, host: str, port: int, timeout: int | None = None) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.logged_in: tuple[str, str] | None = None
        self.sent: list[tuple[str, list[str], str]] = []
        self.closed = False
        FakeSMTP.instances.append(self)

    def starttls(self) -> None:
        self.started_tls = True

    def login(self, username: str, password: str) -> None:
        self.logged_in = (username, password)

    def sendmail(self, from_addr: str, to_addrs: list[str], msg: str) -> None:
        self.sent.append((from_addr, to_addrs, msg))

    def quit(self) -> None:
        self.closed = True


class AuthFailSMTP(FakeSMTP):
    def login(self, username: str, password: str) -> None:
        raise smtplib.SMTPAuthenticationError(535, b"auth failed")


@pytest.mark.asyncio
async def test_smtp_health_and_send_email(monkeypatch):
    FakeSMTP.instances.clear()
    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)
    monkeypatch.setattr("smtplib.SMTP_SSL", FakeSMTP)

    provider = SmtpProvider(
        {
            "host": "smtp.example.com",
            "port": 587,
            "username": "user",
            "password": "secret",
            "from_email": "noreply@example.com",
            "from_name": "Home Office",
            "use_tls": True,
        }
    )

    success, message = await provider.health_check()
    assert success is True
    assert message == "Connected"
    assert FakeSMTP.instances[-1].started_tls is True
    assert FakeSMTP.instances[-1].logged_in == ("user", "secret")

    result = await provider.send_email(
        to=["dest@example.com"],
        subject="Report",
        body="Plain text",
        body_html="<p>HTML</p>",
        attachments=[("report.txt", b"data", "text/plain")],
    )
    assert result is True
    sent = FakeSMTP.instances[-1].sent[0]
    assert sent[0] == "noreply@example.com"
    assert "Report" in sent[2]
    assert "multipart/alternative" in sent[2]
    assert "report.txt" in sent[2]


@pytest.mark.asyncio
async def test_smtp_health_auth_failure(monkeypatch):
    monkeypatch.setattr("smtplib.SMTP", AuthFailSMTP)
    provider = SmtpProvider(
        {
            "host": "smtp.example.com",
            "port": 587,
            "username": "bad",
            "password": "secret",
            "from_email": "noreply@example.com",
            "use_tls": True,
        }
    )
    success, message = await provider.health_check()
    assert success is False
    assert message == "Authentication failed"
