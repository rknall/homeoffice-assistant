# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for the OpenAI-compatible LLM provider and expense scan validation."""

import base64
import json
from decimal import Decimal

import pytest
import respx
from httpx import Response

from src.integrations.llm import LlmError, OpenAiCompatibleLlmProvider
from src.models.enums import ExpenseCategory, PaymentType
from src.services.expense_scan_service import validate_extraction

CONFIG = {
    "base_url": "https://llm.example.com/v1",
    "api_key": "sk-test",
    "model": "gpt-4o-mini",
}


def chat_response(content: dict | str) -> Response:
    if isinstance(content, dict):
        content = json.dumps(content)
    return Response(200, json={"choices": [{"message": {"content": content}}]})


@pytest.mark.asyncio
@respx.mock
async def test_extract_expense_happy_path():
    respx.post("https://llm.example.com/v1/chat/completions").mock(
        return_value=chat_response(
            {
                "date": "2025-12-28",
                "amount": 134.8,
                "currency": "chf",
                "category": "travel",
                "payment_type": "debit_card",
                "description": "SBB ticket",
            }
        )
    )
    provider = OpenAiCompatibleLlmProvider(CONFIG)
    try:
        raw = await provider.extract_expense("some receipt text")
    finally:
        await provider.close()

    result = validate_extraction(raw)
    assert str(result.date) == "2025-12-28"
    assert result.amount == Decimal("134.80")
    assert result.currency == "CHF"
    assert result.category == ExpenseCategory.TRAVEL
    assert result.payment_type == PaymentType.DEBIT_CARD
    assert result.description == "SBB ticket"
    assert result.warnings == []


@pytest.mark.asyncio
@respx.mock
async def test_extract_expense_http_error():
    respx.post("https://llm.example.com/v1/chat/completions").mock(
        return_value=Response(401, json={"error": "bad key"})
    )
    provider = OpenAiCompatibleLlmProvider(CONFIG)
    try:
        with pytest.raises(LlmError, match="401"):
            await provider.extract_expense("text")
    finally:
        await provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_extract_expense_markdown_fenced_json():
    fenced = '```json\n{"date": "2025-01-01", "amount": 5, "currency": "EUR"}\n```'
    respx.post("https://llm.example.com/v1/chat/completions").mock(
        return_value=chat_response(fenced)
    )
    provider = OpenAiCompatibleLlmProvider(CONFIG)
    try:
        raw = await provider.extract_expense("text")
    finally:
        await provider.close()
    assert raw["date"] == "2025-01-01"
    assert raw["currency"] == "EUR"


@pytest.mark.asyncio
@respx.mock
async def test_extract_expense_json_wrapped_in_prose():
    wrapped = 'Here is the extracted data:\n{"amount": 12.5, "currency": "USD"}\nDone!'
    respx.post("https://llm.example.com/v1/chat/completions").mock(
        return_value=chat_response(wrapped)
    )
    provider = OpenAiCompatibleLlmProvider(CONFIG)
    try:
        raw = await provider.extract_expense("text")
    finally:
        await provider.close()
    assert raw["amount"] == 12.5
    assert raw["currency"] == "USD"


@pytest.mark.asyncio
@respx.mock
async def test_extract_expense_invalid_json():
    respx.post("https://llm.example.com/v1/chat/completions").mock(
        return_value=chat_response("not json at all")
    )
    provider = OpenAiCompatibleLlmProvider(CONFIG)
    try:
        with pytest.raises(LlmError, match="invalid JSON"):
            await provider.extract_expense("text")
    finally:
        await provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_health_check():
    respx.get("https://llm.example.com/v1/models").mock(
        return_value=Response(200, json={"data": []})
    )
    provider = OpenAiCompatibleLlmProvider(CONFIG)
    try:
        ok, message = await provider.health_check()
    finally:
        await provider.close()
    assert ok is True
    assert message == "Connected"


@pytest.mark.asyncio
@respx.mock
async def test_health_check_auth_failure():
    respx.get("https://llm.example.com/v1/models").mock(
        return_value=Response(401, json={})
    )
    provider = OpenAiCompatibleLlmProvider(CONFIG)
    try:
        ok, message = await provider.health_check()
    finally:
        await provider.close()
    assert ok is False
    assert "Authentication" in message


def test_validate_extraction_all_null():
    result = validate_extraction(
        dict.fromkeys(
            ["date", "amount", "currency", "category", "payment_type", "description"]
        )
    )
    assert result.date is None
    assert result.amount is None
    assert any("no expense data" in w for w in result.warnings)


def test_validate_extraction_drops_invalid_values():
    result = validate_extraction(
        {
            "date": "yesterday",
            "amount": "-5",
            "currency": "EURO",
            "category": "shopping",
            "payment_type": "bitcoin",
            "description": "  Taxi  ",
        }
    )
    assert result.date is None
    assert result.amount is None
    assert result.currency is None
    assert result.category is None
    assert result.payment_type is None
    assert result.description == "Taxi"
    assert len(result.warnings) == 5


@pytest.mark.asyncio
@respx.mock
async def test_basic_auth_and_api_key_are_sent_together():
    """A gateway takes Authorization, so the API key moves to x-api-key."""
    route = respx.get("https://llm.example.com/v1/models").mock(
        return_value=Response(200, json={"data": []})
    )
    provider = OpenAiCompatibleLlmProvider(
        {**CONFIG, "username": "alice", "password": "s3cret"}
    )
    try:
        ok, message = await provider.health_check()
    finally:
        await provider.close()

    assert (ok, message) == (True, "Connected")
    headers = route.calls.last.request.headers
    expected = base64.b64encode(b"alice:s3cret").decode()
    assert headers["Authorization"] == f"Basic {expected}"
    assert headers["x-api-key"] == "sk-test"


@pytest.mark.asyncio
@respx.mock
async def test_bearer_token_used_without_username():
    route = respx.get("https://llm.example.com/v1/models").mock(
        return_value=Response(200, json={"data": []})
    )
    provider = OpenAiCompatibleLlmProvider(CONFIG)
    try:
        await provider.health_check()
    finally:
        await provider.close()

    headers = route.calls.last.request.headers
    assert headers["Authorization"] == "Bearer sk-test"
    assert "x-api-key" not in headers


@pytest.mark.asyncio
@respx.mock
async def test_list_models_returns_sorted_ids():
    respx.get("https://llm.example.com/v1/models").mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {"id": "gpt-4o-mini"},
                    {"id": "claude-sonnet-5"},
                    {"object": "model"},
                ]
            },
        )
    )
    provider = OpenAiCompatibleLlmProvider(CONFIG)
    try:
        models = await provider.list_models()
    finally:
        await provider.close()

    assert models == ["claude-sonnet-5", "gpt-4o-mini"]


@pytest.mark.asyncio
@respx.mock
async def test_list_models_raises_on_error():
    respx.get("https://llm.example.com/v1/models").mock(
        return_value=Response(401, text="no key")
    )
    provider = OpenAiCompatibleLlmProvider(CONFIG)
    try:
        with pytest.raises(LlmError, match="401"):
            await provider.list_models()
    finally:
        await provider.close()
