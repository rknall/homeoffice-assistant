# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""OpenAI-compatible LLM integration provider (OpenAI, LiteLLM, etc.)."""

import json
import logging
import re
from typing import Any

import httpx

from src.integrations.base import LlmProvider
from src.integrations.registry import IntegrationRegistry
from src.models.enums import ExpenseCategory, PaymentType

logger = logging.getLogger(__name__)

EXTRACTION_FIELDS = (
    "date",
    "amount",
    "currency",
    "category",
    "payment_type",
    "description",
)


def _extraction_prompt() -> str:
    categories = ", ".join(c.value for c in ExpenseCategory)
    payment_types = ", ".join(p.value for p in PaymentType)
    return (
        "You extract expense data from receipt or invoice text (often OCR "
        "output, possibly in any language). Reply with a single JSON object "
        "with exactly these keys:\n"
        '- "date": the purchase/invoice date as ISO 8601 (YYYY-MM-DD)\n'
        '- "amount": the total amount paid as a decimal number\n'
        '- "currency": the 3-letter ISO 4217 currency code\n'
        f'- "category": one of: {categories}\n'
        f'- "payment_type": one of: {payment_types}\n'
        '- "description": a short English description of the purchase '
        "(merchant and what was bought, max 100 characters)\n"
        "Use null for any value that cannot be determined from the text. "
        "Do not guess. Reply with JSON only."
    )


class LlmError(Exception):
    """LLM request or response error."""


def _parse_json_object(content: str | None) -> dict[str, Any] | None:
    """Parse a JSON object from LLM output, tolerating common wrapping.

    Models that ignore response_format often wrap the JSON in markdown code
    fences or surrounding prose; extract the first {...} block in that case.
    """
    if not content:
        return None
    candidate = content.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```[a-zA-Z]*\s*", "", candidate)
        candidate = re.sub(r"\s*```$", "", candidate)
    try:
        data = json.loads(candidate)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", candidate, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None
    return None


@IntegrationRegistry.register
class OpenAiCompatibleLlmProvider(LlmProvider):
    """LLM provider for OpenAI-compatible chat-completions APIs."""

    @classmethod
    def get_type(cls) -> str:
        """Return the unique identifier for this integration type."""
        return "llm"

    @classmethod
    def get_display_name(cls) -> str:
        """Return the human-readable name for this integration."""
        return "LLM (OpenAI-compatible)"

    @classmethod
    def get_config_schema(cls) -> dict[str, Any]:
        """Return JSON Schema for the configuration form."""
        return {
            "type": "object",
            "required": ["base_url", "model"],
            "properties": {
                "base_url": {
                    "type": "string",
                    "title": "Base URL",
                    "description": (
                        "OpenAI-compatible API base URL, e.g. a LiteLLM proxy "
                        "or https://api.openai.com/v1"
                    ),
                    "default": "https://api.openai.com/v1",
                },
                "api_key": {
                    "type": "string",
                    "title": "API Key",
                    "description": (
                        "API key for the LLM service. Sent as a Bearer token, "
                        "or as an x-api-key header when basic auth is used."
                    ),
                    "format": "password",
                },
                "username": {
                    "type": "string",
                    "title": "Basic Auth Username",
                    "description": (
                        "Optional. Set when the API sits behind a gateway "
                        "that requires HTTP basic authentication."
                    ),
                },
                "password": {
                    "type": "string",
                    "title": "Basic Auth Password",
                    "description": "Password for HTTP basic authentication",
                    "format": "password",
                },
                "model": {
                    "type": "string",
                    "title": "Model",
                    "description": "Model name, e.g. gpt-4o-mini",
                    "default": "gpt-4o-mini",
                },
            },
        }

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the provider with decrypted configuration."""
        self.base_url = config["base_url"].rstrip("/")
        self.api_key = config.get("api_key") or ""
        self.model = config.get("model", "gpt-4o-mini")
        username = config.get("username") or ""
        # A gateway in front of the API (Pangolin, nginx, ...) takes the
        # Authorization header for basic auth, so the API key has to move to
        # x-api-key, which OpenAI-compatible servers such as LiteLLM accept.
        # ponytail: x-api-key hardcoded, make the header name configurable if
        # a backend shows up that wants something else.
        auth = (
            httpx.BasicAuth(username, config.get("password") or "")
            if username
            else None
        )
        headers: dict[str, str] = {}
        if self.api_key:
            key_header = "x-api-key" if auth else "Authorization"
            key_value = self.api_key if auth else f"Bearer {self.api_key}"
            headers[key_header] = key_value
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            auth=auth,
            timeout=60.0,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def health_check(self) -> tuple[bool, str]:
        """Check connectivity and authentication against the models endpoint."""
        try:
            resp = await self._client.get("/models")
            if resp.status_code == 401:
                return False, "Authentication failed (invalid credentials)"
            resp.raise_for_status()
            return True, "Connected"
        except httpx.ConnectError:
            return False, "Connection failed"
        except httpx.TimeoutException:
            return False, "Connection timeout"
        except Exception as e:
            return False, str(e)

    async def extract_expense(self, text: str) -> dict[str, Any]:
        """Extract expense fields from document text via chat completions.

        Returns a dict with the EXTRACTION_FIELDS keys, values nullable.

        Raises:
            LlmError: If the request fails or the reply is not usable JSON.
        """
        payload = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": _extraction_prompt()},
                {"role": "user", "content": text},
            ],
        }
        try:
            resp = await self._client.post("/chat/completions", json=payload)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM request failed: {e}")
            detail = e.response.text[:200]
            raise LlmError(
                f"LLM request failed ({e.response.status_code}): {detail}"
            ) from e
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
            logger.error(f"LLM request failed: {e}")
            raise LlmError(f"LLM request failed: {e}") from e

        data = _parse_json_object(content)
        if data is None:
            logger.warning(f"LLM returned unparseable content: {content[:500]!r}")
            snippet = (content or "").strip()[:120]
            raise LlmError(f"LLM returned invalid JSON: {snippet!r}")

        return {field: data.get(field) for field in EXTRACTION_FIELDS}
