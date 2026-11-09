# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Unsplash integration for image search."""

from typing import Any

import httpx

from src.integrations.base import ImageSearchProvider
from src.integrations.failure import failure_category
from src.integrations.registry import IntegrationRegistry
from src.models.enums import IntegrationType


@IntegrationRegistry.register
class UnsplashProvider(ImageSearchProvider):
    """Unsplash API client for image search."""

    BASE_URL = "https://api.unsplash.com"

    @classmethod
    def get_type(cls) -> str:
        """Return the unique identifier for this integration type."""
        return IntegrationType.UNSPLASH.value

    @classmethod
    def get_display_name(cls) -> str:
        """Return the human-readable name for this integration."""
        return "Unsplash"

    @classmethod
    def get_config_schema(cls) -> dict[str, Any]:
        """Return JSON Schema for the configuration form."""
        return {
            "type": "object",
            "required": ["access_key"],
            "properties": {
                "access_key": {
                    "type": "string",
                    "title": "Access Key",
                    "description": "Unsplash API Access Key (unsplash.com/developers)",
                    "format": "password",
                },
                "secret_key": {
                    "type": "string",
                    "title": "Secret Key",
                    "description": "Unsplash API Secret Key (optional, OAuth)",
                    "format": "password",
                },
            },
        }

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the Unsplash provider with configuration.

        Args:
            config: Decrypted configuration dict with access_key, etc.
        """
        self.access_key = config["access_key"]
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Client-ID {self.access_key}",
                "Accept-Version": "v1",
            },
            timeout=30.0,
        )

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        await self._client.aclose()

    async def health_check(self) -> tuple[bool, str]:
        """Check connectivity by fetching current user (rate limit info)."""
        try:
            # Use a simple search to verify the API key works
            resp = await self._client.get("/photos/random", params={"count": 1})
            if resp.status_code == 200:
                # Check rate limit headers
                remaining = resp.headers.get("X-Ratelimit-Remaining", "unknown")
                return True, f"Connected (API calls remaining: {remaining})"
            if resp.status_code == 401:
                return False, "Invalid Access Key"
            return False, f"HTTP {resp.status_code}"
        except Exception as e:
            return False, failure_category(e)

    async def search_images(
        self,
        query: str,
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]:
        """Search for images on Unsplash."""
        resp = await self._client.get(
            "/search/photos",
            params={
                "query": query,
                "page": page,
                "per_page": per_page,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        # Transform to a simpler format
        return {
            "total": data.get("total", 0),
            "total_pages": data.get("total_pages", 0),
            "results": [
                {
                    "id": photo["id"],
                    "description": photo.get("description")
                    or photo.get("alt_description"),
                    "width": photo["width"],
                    "height": photo["height"],
                    "color": photo.get("color"),
                    "urls": {
                        "raw": photo["urls"]["raw"],
                        "full": photo["urls"]["full"],
                        "regular": photo["urls"]["regular"],
                        "small": photo["urls"]["small"],
                        "thumb": photo["urls"]["thumb"],
                    },
                    "user": {
                        "name": photo["user"]["name"],
                        "username": photo["user"]["username"],
                        "portfolio_url": photo["user"].get("portfolio_url"),
                    },
                    "links": {
                        "html": photo["links"]["html"],
                        "download_location": photo["links"]["download_location"],
                    },
                }
                for photo in data.get("results", [])
            ],
        }

    async def get_image(self, image_id: str) -> dict[str, Any]:
        """Get image details by ID."""
        resp = await self._client.get(f"/photos/{image_id}")
        resp.raise_for_status()
        photo = resp.json()

        return {
            "id": photo["id"],
            "description": photo.get("description") or photo.get("alt_description"),
            "width": photo["width"],
            "height": photo["height"],
            "color": photo.get("color"),
            "urls": {
                "raw": photo["urls"]["raw"],
                "full": photo["urls"]["full"],
                "regular": photo["urls"]["regular"],
                "small": photo["urls"]["small"],
                "thumb": photo["urls"]["thumb"],
            },
            "user": {
                "name": photo["user"]["name"],
                "username": photo["user"]["username"],
                "portfolio_url": photo["user"].get("portfolio_url"),
            },
            "links": {
                "html": photo["links"]["html"],
                "download_location": photo["links"]["download_location"],
            },
        }

    async def trigger_download(self, image_id: str) -> str:
        """Trigger download tracking (required by Unsplash API guidelines).

        This must be called when an image is actually downloaded/used.
        Returns the download URL.
        """
        # First get the download location
        photo = await self.get_image(image_id)
        download_location = photo["links"]["download_location"]

        # Trigger the download endpoint
        resp = await self._client.get(download_location)
        resp.raise_for_status()
        data = resp.json()

        return data.get("url", photo["urls"]["full"])
