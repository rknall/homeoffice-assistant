# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for the provider failure categories and their use in the API."""

import smtplib
import socket
from collections.abc import Callable
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from src.integrations.base import EmailProvider
from src.integrations.failure import failure_category
from src.integrations.llm import LlmError

INTEGRATIONS = "/api/v1/integrations"


def _status_error(code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://llm.example.com/models")
    response = httpx.Response(code, request=request, text="secret body")
    return httpx.HTTPStatusError("secret message", request=request, response=response)


def _wrapped(cause: BaseException) -> LlmError:
    error = LlmError("secret wrapper text")
    error.__cause__ = cause
    return error


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (httpx.ConnectError("boom"), "server unreachable"),
        (httpx.ReadTimeout("slow"), "server unreachable"),
        (ConnectionRefusedError("refused"), "server unreachable"),
        (socket.gaierror("no such host"), "server unreachable"),
        (smtplib.SMTPConnectError(421, b"busy"), "server unreachable"),
        (smtplib.SMTPServerDisconnected("gone"), "server unreachable"),
        (smtplib.SMTPAuthenticationError(535, b"bad"), "authentication failed"),
        (_status_error(401), "authentication failed"),
        (_status_error(403), "authentication failed"),
        (_status_error(500), "unexpected response"),
        (smtplib.SMTPRecipientsRefused({}), "unexpected response"),
        (ValueError("odd"), "unexpected response"),
        (_wrapped(httpx.ConnectError("boom")), "server unreachable"),
        (_wrapped(_status_error(401)), "authentication failed"),
        (LlmError("no cause"), "unexpected response"),
    ],
)
def test_failure_category_from_exception_class(
    exc: BaseException, expected: str
) -> None:
    """The category follows the exception class, wrapped causes included."""
    assert failure_category(exc) == expected


def _smtp_id(admin_client: TestClient) -> str:
    created = admin_client.post(
        INTEGRATIONS,
        json={
            "integration_type": "smtp",
            "name": "smtp",
            "config": {"host": "smtp.example.com"},
        },
    )
    return str(created.json()["id"])


@pytest.mark.parametrize(
    ("error", "category"),
    [
        (ConnectionRefusedError("10.0.0.5 refused"), "server unreachable"),
        (smtplib.SMTPAuthenticationError(535, b"user bob"), "authentication failed"),
    ],
)
def test_test_email_reports_category_without_exception_text(
    admin_client: TestClient, error: Exception, category: str
) -> None:
    """The test-email message names the category and no raw exception text."""
    config_id = _smtp_id(admin_client)
    provider = MagicMock(spec=EmailProvider)
    provider.send_email = AsyncMock(side_effect=error)
    provider.close = AsyncMock()
    target = "src.services.integration_service.create_provider_instance"
    with patch(target, return_value=provider):
        response = admin_client.post(
            f"{INTEGRATIONS}/{config_id}/test-email",
            json={"to_email": "a@example.com"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "success": False,
        "message": f"Failed to send test email: {category}",
    }
    assert "10.0.0.5" not in response.text
    assert "bob" not in response.text


def _stub_llm(
    monkeypatch: pytest.MonkeyPatch,
    handler: Callable[[httpx.Request], httpx.Response],
) -> None:
    real_client = httpx.AsyncClient

    class StubClient(real_client):
        def __init__(self, *args: object, **kwargs: object) -> None:
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", StubClient)


def test_llm_model_list_reports_category_without_exception_text(
    admin_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unreachable LLM endpoint gives the category, not the httpx text."""

    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("secret-host.internal refused", request=request)

    _stub_llm(monkeypatch, refuse)
    response = admin_client.post(
        f"{INTEGRATIONS}/llm/models",
        json={"base_url": "http://secret-host.internal:9/v1"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Could not list models: server unreachable"
    assert "secret-host" not in response.text


def test_llm_model_list_auth_failure_category(
    admin_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A 401 from the endpoint is reported as an authentication failure."""

    def deny(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="invalid key sk-123", request=request)

    _stub_llm(monkeypatch, deny)
    response = admin_client.post(
        f"{INTEGRATIONS}/llm/models", json={"base_url": "https://llm.example.com/v1"}
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Could not list models: authentication failed"
    assert "sk-123" not in response.text
