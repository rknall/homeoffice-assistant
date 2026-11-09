# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Unsplash search bounds and the report submission method values."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.schemas.expense import ExpenseSubmissionCreate, SubmissionMethod
from src.schemas.report import GenerateReportRequest

BASE = "/api/v1/integrations"


@pytest.fixture
def unsplash_id(admin_client: TestClient) -> str:
    """Create an Unsplash integration and return its id."""
    response = admin_client.post(
        BASE,
        json={
            "integration_type": "unsplash",
            "name": "Unsplash",
            "config": {"access_key": "key-1"},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page": -1},
        {"per_page": 0},
        {"per_page": 31},
        {"per_page": 10000},
    ],
)
def test_unsplash_search_rejects_out_of_range(
    admin_client: TestClient, unsplash_id: str, params: dict[str, int]
) -> None:
    """Page and per_page are bounded before any provider call."""
    response = admin_client.get(
        f"{BASE}/{unsplash_id}/unsplash/search", params={"query": "sea", **params}
    )

    assert response.status_code == 422


def test_search_on_unknown_integration_is_404(admin_client: TestClient) -> None:
    """A missing integration keeps its 404."""
    response = admin_client.get(
        f"{BASE}/00000000-0000-0000-0000-000000000000/unsplash/search",
        params={"query": "sea"},
    )

    assert response.status_code == 404


@pytest.mark.parametrize("schema", [GenerateReportRequest, ExpenseSubmissionCreate])
def test_submission_method_is_an_enum(schema: type) -> None:
    """Only download, email and portal are accepted; download is the default."""
    fields = {"expense_ids": []}
    assert schema(**fields).submission_method is SubmissionMethod.DOWNLOAD
    assert schema(**fields, submission_method="email").submission_method == "email"
    with pytest.raises(ValidationError):
        schema(**fields, submission_method="carrier-pigeon")
