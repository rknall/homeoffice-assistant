# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Integration secrets: LLM model listing scope and schema-driven masking."""

import base64
import uuid
from collections.abc import Callable

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models import User
from src.services import integration_service

STORED_LLM_KEY = "stored-llm-key"
STORED_BASIC = "stored-basic-value"
STORED_ACCESS = "stored-access-value"
STORED_SIGNING = "stored-signing-value"
STORED_BASE_URL = "https://llm.example.com/v1"


@pytest.fixture
def outgoing(monkeypatch: pytest.MonkeyPatch) -> list[httpx.Request]:
    """Record every request the LLM provider sends, answering with one model."""
    sent: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, json={"data": [{"id": "model-a"}]})

    real_client = httpx.AsyncClient

    class RecordingClient(real_client):
        def __init__(self, *args: object, **kwargs: object) -> None:
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", RecordingClient)
    return sent


def _create(client: TestClient, integration_type: str, config: dict) -> str:
    response = client.post(
        "/api/v1/integrations",
        json={"integration_type": integration_type, "name": "x", "config": config},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.fixture
def llm_config_id(admin_client: TestClient) -> str:
    """Create an LLM integration with an API key behind basic auth."""
    return _create(
        admin_client,
        "llm",
        {
            "base_url": STORED_BASE_URL,
            "api_key": STORED_LLM_KEY,
            "username": "gateway",
            "password": STORED_BASIC,
            "model": "model-a",
        },
    )


def _models_request(base_url: str, config_id: str) -> dict[str, str]:
    # The edit form sends saved secrets back blank.
    return {
        "base_url": base_url,
        "api_key": "",
        "username": "gateway",
        "password": "",
        "config_id": config_id,
    }


def _sent_secrets(request: httpx.Request) -> str:
    """Return every credential-bearing header value of a request, decoded."""
    values = [request.headers.get("x-api-key", "")]
    authorization = request.headers.get("authorization", "")
    values.append(authorization)
    if authorization.lower().startswith("basic "):
        values.append(base64.b64decode(authorization[6:]).decode())
    return " ".join(values)


def test_llm_models_requires_admin(
    client: TestClient,
    user_factory: Callable[..., User],
    login: Callable[[TestClient, User], TestClient],
    llm_config_id: str,
    outgoing: list[httpx.Request],
) -> None:
    member = login(client, user_factory("member"))
    response = member.post(
        "/api/v1/integrations/llm/models",
        json=_models_request("https://attacker.example.com/v1", llm_config_id),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied: integration.config"
    assert outgoing == []


def test_llm_models_foreign_base_url_gets_no_stored_secret(
    admin_client: TestClient, llm_config_id: str, outgoing: list[httpx.Request]
) -> None:
    response = admin_client.post(
        "/api/v1/integrations/llm/models",
        json=_models_request("https://attacker.example.com/v1", llm_config_id),
    )
    assert response.status_code == 200, response.text
    assert len(outgoing) == 1
    assert outgoing[0].url.host == "attacker.example.com"
    sent = _sent_secrets(outgoing[0])
    assert STORED_LLM_KEY not in sent
    assert STORED_BASIC not in sent
    assert STORED_LLM_KEY not in response.text


def test_llm_models_stored_base_url_uses_stored_secrets(
    admin_client: TestClient, llm_config_id: str, outgoing: list[httpx.Request]
) -> None:
    response = admin_client.post(
        "/api/v1/integrations/llm/models",
        json=_models_request(STORED_BASE_URL, llm_config_id),
    )
    assert response.status_code == 200, response.text
    assert response.json() == ["model-a"]
    sent = _sent_secrets(outgoing[0])
    assert STORED_LLM_KEY in sent
    assert STORED_BASIC in sent


def test_unsplash_keys_masked_and_preserved(
    admin_client: TestClient, db_session: Session
) -> None:
    config_id = _create(
        admin_client,
        "unsplash",
        {"access_key": STORED_ACCESS, "secret_key": STORED_SIGNING},
    )

    detail = admin_client.get(f"/api/v1/integrations/{config_id}/config")
    assert detail.status_code == 200
    assert detail.json()["config"] == {"access_key": "", "secret_key": ""}
    assert STORED_ACCESS not in detail.text
    assert STORED_SIGNING not in detail.text

    # Saving the form with the masked values keeps the stored keys.
    update = admin_client.put(
        f"/api/v1/integrations/{config_id}",
        json={"config": detail.json()["config"]},
    )
    assert update.status_code == 200, update.text
    stored = integration_service.get_integration_config(
        db_session, uuid.UUID(config_id)
    )
    assert stored is not None
    db_session.refresh(stored)
    decrypted = integration_service.get_decrypted_config(stored)
    assert decrypted == {"access_key": STORED_ACCESS, "secret_key": STORED_SIGNING}
