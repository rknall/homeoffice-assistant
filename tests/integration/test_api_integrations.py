# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Characterization of the integration CRUD, test and provider routes.

Secret masking and the LLM model scoping live in test_integration_secrets.py.
"""

import smtplib
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.integrations.base import DocumentProvider, EmailProvider, ImageSearchProvider
from src.models import User
from tests.conftest import LoginHelper

BASE = "/api/v1/integrations"
SERVICE = "src.api.v1.integrations.integration_service"


def _create(client: TestClient, integration_type: str, **config: Any) -> dict[str, Any]:
    response = client.post(
        BASE,
        json={
            "integration_type": integration_type,
            "name": f"{integration_type} config",
            "config": config or {"token": "secret-token"},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_admin_crud_roundtrip(admin_client: TestClient) -> None:
    """Global Admin creates, reads, updates, lists and deletes an integration."""
    created = _create(admin_client, "unsplash", access_key="key-1")
    url = f"{BASE}/{created['id']}"

    assert created["is_active"] is True
    assert "config" not in created
    assert admin_client.get(url).json()["name"] == "unsplash config"
    updated = admin_client.put(url, json={"name": "Renamed", "is_active": False})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Renamed"
    assert updated.json()["is_active"] is False
    listed = admin_client.get(BASE, params={"integration_type": "unsplash"})
    assert [i["id"] for i in listed.json()] == [created["id"]]
    assert admin_client.get(BASE, params={"integration_type": "smtp"}).json() == []
    assert admin_client.delete(url).status_code == 204
    assert admin_client.get(url).status_code == 404


def test_unknown_id_is_not_found(admin_client: TestClient) -> None:
    """Unknown integration ids are 404 on every id route."""
    url = f"{BASE}/{uuid.uuid4()}"

    assert admin_client.get(url).status_code == 404
    assert admin_client.get(f"{url}/config").status_code == 404
    assert admin_client.put(url, json={"name": "x"}).status_code == 404
    assert admin_client.delete(url).status_code == 404
    assert admin_client.post(f"{url}/test").status_code == 404
    assert (
        admin_client.post(f"{url}/test-email", json={"to_email": "a@b.co"}).status_code
        == 404
    )
    assert admin_client.get(f"{url}/storage-paths").status_code == 404


def test_create_rejects_unknown_type(admin_client: TestClient) -> None:
    """An integration type outside the enum is a 422."""
    response = admin_client.post(
        BASE, json={"integration_type": "ftp", "name": "x", "config": {}}
    )

    assert response.status_code == 422


def test_member_may_use_but_not_configure(
    admin_client: TestClient,
    client: TestClient,
    login: LoginHelper,
    second_user: User,
) -> None:
    """Member holds integration.use: it reads, but cannot create or edit."""
    created = _create(admin_client, "unsplash", access_key="key-1")
    member = login(client, second_user)
    url = f"{BASE}/{created['id']}"

    assert member.get(BASE).status_code == 200
    assert member.get(url).status_code == 200
    assert member.get(f"{BASE}/types").status_code == 200
    assert member.get(f"{url}/config").status_code == 403
    assert (
        member.post(
            BASE, json={"integration_type": "unsplash", "name": "x", "config": {}}
        ).status_code
        == 403
    )
    assert member.put(url, json={"name": "x"}).status_code == 403
    assert member.delete(url).status_code == 403
    assert (
        member.post(f"{BASE}/llm/models", json={"base_url": "https://x"}).status_code
        == 403
    )


def test_config_detail_masks_secret(admin_client: TestClient) -> None:
    """The edit view returns the config with the secret masked."""
    created = _create(admin_client, "unsplash", access_key="plain-secret-value")
    response = admin_client.get(f"{BASE}/{created['id']}/config")

    assert response.status_code == 200
    assert "plain-secret-value" not in response.text
    assert "access_key" in response.json()["config"]


def test_config_detail_reports_secrets_set(admin_client: TestClient) -> None:
    """A stored key is blank in the config but listed in secrets_set."""
    with_key = _create(admin_client, "llm", api_key="stored-llm-key")
    body = admin_client.get(f"{BASE}/{with_key['id']}/config")
    assert body.status_code == 200
    assert "stored-llm-key" not in body.text
    assert body.json()["config"]["api_key"] == ""
    assert body.json()["secrets_set"] == ["api_key"]

    without_key = _create(admin_client, "llm", api_key="")
    empty = admin_client.get(f"{BASE}/{without_key['id']}/config")
    assert empty.json()["secrets_set"] == []


def test_types_lists_every_integration(admin_client: TestClient) -> None:
    """The types endpoint lists each integration type with its schema."""
    response = admin_client.get(f"{BASE}/types")

    assert response.status_code == 200
    types = {t["type"] for t in response.json()}
    assert {"paperless", "immich", "smtp", "unsplash", "llm"} <= types
    assert all(t["config_schema"] for t in response.json())


def test_test_endpoint_reports_connection_result(admin_client: TestClient) -> None:
    """The test route returns the provider's health check result."""
    created = _create(admin_client, "unsplash", access_key="key-1")
    check = AsyncMock(return_value=(False, "no route to host"))
    with patch(f"{SERVICE}.test_integration_connection", new=check):
        response = admin_client.post(f"{BASE}/{created['id']}/test")

    assert response.status_code == 200
    assert response.json() == {"success": False, "message": "no route to host"}


def test_test_email_requires_smtp_integration(admin_client: TestClient) -> None:
    """test-email on a non-SMTP integration is a 400."""
    created = _create(admin_client, "unsplash", access_key="key-1")
    response = admin_client.post(
        f"{BASE}/{created['id']}/test-email", json={"to_email": "a@example.com"}
    )

    assert response.status_code == 400
    assert "SMTP" in response.json()["detail"]


@pytest.mark.parametrize(
    ("sent", "expected"),
    [(True, True), (False, False)],
)
def test_test_email_sends_through_provider(
    admin_client: TestClient, sent: bool, expected: bool
) -> None:
    """A provider send result becomes the response success flag."""
    created = _create(admin_client, "smtp", host="smtp.example.com")
    provider = MagicMock(spec=EmailProvider)
    provider.send_email = AsyncMock(return_value=sent)
    provider.close = AsyncMock()
    with patch(f"{SERVICE}.create_provider_instance", return_value=provider):
        response = admin_client.post(
            f"{BASE}/{created['id']}/test-email", json={"to_email": "a@example.com"}
        )

    assert response.status_code == 200
    assert response.json()["success"] is expected
    provider.close.assert_awaited_once()


def test_test_email_provider_error_is_reported_not_raised(
    admin_client: TestClient,
) -> None:
    """A provider exception is returned as success=false with a generic message."""
    created = _create(admin_client, "smtp", host="smtp.example.com")
    provider = MagicMock(spec=EmailProvider)
    provider.send_email = AsyncMock(side_effect=smtplib.SMTPException("relay denied"))
    provider.close = AsyncMock()
    with patch(f"{SERVICE}.create_provider_instance", return_value=provider):
        response = admin_client.post(
            f"{BASE}/{created['id']}/test-email", json={"to_email": "a@example.com"}
        )

    assert response.status_code == 200
    assert response.json() == {
        "success": False,
        "message": "Failed to send test email: unexpected response",
    }
    assert "relay denied" not in response.text


def test_test_email_provider_creation_failure_is_500(
    admin_client: TestClient,
) -> None:
    """A provider that cannot be built is a 500."""
    created = _create(admin_client, "smtp", host="smtp.example.com")
    with patch(f"{SERVICE}.create_provider_instance", return_value=None):
        response = admin_client.post(
            f"{BASE}/{created['id']}/test-email", json={"to_email": "a@example.com"}
        )

    assert response.status_code == 500


def test_storage_paths_wrong_type_and_success(admin_client: TestClient) -> None:
    """Storage paths need a Paperless integration and return its paths."""
    wrong = _create(admin_client, "unsplash", access_key="key-1")
    paperless = _create(admin_client, "paperless", url="https://p.example.com")

    rejected = admin_client.get(f"{BASE}/{wrong['id']}/storage-paths")
    assert rejected.status_code == 400
    assert "Paperless" in rejected.json()["detail"]

    provider = MagicMock(spec=DocumentProvider)
    provider.list_storage_paths = AsyncMock(
        return_value=[{"id": 3, "name": "Travel", "path": "travel/{{ created }}"}]
    )
    provider.close = AsyncMock()
    with patch(f"{SERVICE}.create_provider_instance", return_value=provider):
        response = admin_client.get(f"{BASE}/{paperless['id']}/storage-paths")

    assert response.status_code == 200
    assert response.json() == [
        {"id": 3, "name": "Travel", "path": "travel/{{ created }}"}
    ]
    provider.close.assert_awaited_once()


def test_unsplash_search_wrong_type_and_success(admin_client: TestClient) -> None:
    """Unsplash search needs an Unsplash integration and returns its page."""
    wrong = _create(admin_client, "smtp", host="smtp.example.com")
    unsplash = _create(admin_client, "unsplash", access_key="key-1")

    rejected = admin_client.get(
        f"{BASE}/{wrong['id']}/unsplash/search", params={"query": "alps"}
    )
    assert rejected.status_code == 400

    provider = MagicMock(spec=ImageSearchProvider)
    provider.search_images = AsyncMock(
        return_value={"total": 0, "total_pages": 0, "results": []}
    )
    provider.close = AsyncMock()
    with patch(f"{SERVICE}.create_provider_instance", return_value=provider):
        response = admin_client.get(
            f"{BASE}/{unsplash['id']}/unsplash/search",
            params={"query": "alps", "page": 2},
        )

    assert response.status_code == 200
    provider.search_images.assert_awaited_once_with("alps", page=2, per_page=20)
    provider.close.assert_awaited_once()


def test_unsplash_download_trigger(admin_client: TestClient) -> None:
    """The download trigger returns the provider's download URL."""
    unsplash = _create(admin_client, "unsplash", access_key="key-1")
    provider = MagicMock(spec=ImageSearchProvider)
    provider.trigger_download = AsyncMock(return_value="https://img.example/d")
    provider.close = AsyncMock()
    with patch(f"{SERVICE}.create_provider_instance", return_value=provider):
        response = admin_client.post(
            f"{BASE}/{unsplash['id']}/unsplash/download/abc123"
        )

    assert response.status_code == 200
    assert response.json() == {"download_url": "https://img.example/d"}
    provider.trigger_download.assert_awaited_once_with("abc123")


def test_custom_field_choices_without_paperless(
    authenticated_client: TestClient,
) -> None:
    """Without an active Paperless integration the choices are unavailable."""
    response = authenticated_client.get(f"{BASE}/event-custom-field-choices")

    assert response.status_code == 200
    assert response.json() == {
        "available": False,
        "custom_field_name": "",
        "choices": [],
    }


def test_custom_field_choices_sorted_by_label(
    admin_client: TestClient,
) -> None:
    """Available choices come back sorted by label with the field name."""
    _create(
        admin_client, "paperless", url="https://p.example.com", custom_field_name="Trip"
    )
    provider = MagicMock(spec=DocumentProvider)
    provider.get_custom_field_by_name = AsyncMock(return_value={"id": 9})
    provider.get_custom_field_choices_with_values = AsyncMock(
        return_value=[
            {"label": "Zurich", "value": "z"},
            {"label": "Berlin", "value": "b"},
        ]
    )
    provider.close = AsyncMock()
    with patch(f"{SERVICE}.create_provider_instance", return_value=provider):
        response = admin_client.get(f"{BASE}/event-custom-field-choices")

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["custom_field_name"] == "Trip"
    assert [c["label"] for c in body["choices"]] == ["Berlin", "Zurich"]
    provider.close.assert_awaited_once()


def test_requires_login(client: TestClient) -> None:
    """An anonymous caller is rejected."""
    assert client.get(BASE).status_code == 401
    assert client.get(f"{BASE}/event-custom-field-choices").status_code == 401
