# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Immich integration for photo management."""
import logging
import math
from datetime import datetime
from typing import Any

import httpx

from src.integrations.base import PhotoProvider
from src.integrations.registry import IntegrationRegistry

logger = logging.getLogger(__name__)


@IntegrationRegistry.register
class ImmichProvider(PhotoProvider):
    """Immich photo management integration."""

    @classmethod
    def get_type(cls) -> str:
        return "immich"

    @classmethod
    def get_display_name(cls) -> str:
        return "Immich"

    @classmethod
    def get_config_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["url", "api_key"],
            "properties": {
                "url": {
                    "type": "string",
                    "title": "Immich URL",
                    "description": "Base URL of your Immich instance (e.g., https://immich.example.com)",
                    "format": "uri",
                },
                "api_key": {
                    "type": "string",
                    "title": "API Key",
                    "description": "API key from Immich (Account Settings > API Keys)",
                    "format": "password",
                },
                "search_radius_km": {
                    "type": "number",
                    "title": "Default Search Radius (km)",
                    "description": "Default radius for location-based photo search",
                    "default": 50,
                },
            },
        }

    def __init__(self, config: dict[str, Any]):
        self.url = config["url"].rstrip("/")
        self.api_key = config["api_key"]
        self.search_radius_km = config.get("search_radius_km", 50)
        self._client = httpx.AsyncClient(
            base_url=self.url,
            headers={
                "x-api-key": self.api_key,
                "Accept": "application/json",
            },
            timeout=30.0,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def health_check(self) -> tuple[bool, str]:
        """Check connectivity to Immich instance."""
        try:
            # Ping endpoint
            resp = await self._client.get("/api/server/ping")
            if resp.status_code != 200:
                return False, f"HTTP {resp.status_code}"

            # Get version
            version_resp = await self._client.get("/api/server/version")
            if version_resp.status_code == 200:
                version_data = version_resp.json()
                version = (
                    f"{version_data.get('major', 0)}."
                    f"{version_data.get('minor', 0)}."
                    f"{version_data.get('patch', 0)}"
                )
                return True, f"Connected to Immich v{version}"

            return True, "Connected"
        except httpx.HTTPError as e:
            return False, f"Connection error: {e}"
        except Exception as e:
            return False, str(e)

    async def list_albums(self) -> list[dict[str, Any]]:
        """List all albums."""
        resp = await self._client.get("/api/albums")
        resp.raise_for_status()
        return resp.json()

    async def create_album(self, name: str) -> dict[str, Any]:
        """Create a new album."""
        resp = await self._client.post(
            "/api/albums",
            json={"albumName": name},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_assets(
        self,
        album_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query assets, optionally from a specific album."""
        if album_id:
            resp = await self._client.get(f"/api/albums/{album_id}")
            resp.raise_for_status()
            album_data = resp.json()
            return album_data.get("assets", [])
        else:
            # Get all assets via search
            resp = await self._client.post(
                "/api/search/metadata",
                json={"size": 1000, "page": 1},
            )
            resp.raise_for_status()
            return resp.json().get("assets", {}).get("items", [])

    async def download_asset(self, asset_id: str) -> tuple[bytes, str, str]:
        """Download original asset file."""
        resp = await self._client.get(f"/api/assets/{asset_id}/original")
        resp.raise_for_status()

        # Extract filename from Content-Disposition header
        content_disposition = resp.headers.get("content-disposition", "")
        filename = "download.jpg"
        if "filename=" in content_disposition:
            filename = content_disposition.split("filename=")[1].strip('"')

        content_type = resp.headers.get("content-type", "image/jpeg")
        return resp.content, filename, content_type

    async def search_by_location_and_date(
        self,
        latitude: float,
        longitude: float,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        radius_km: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for photos by location and optionally date range.

        Since Immich doesn't support proximity search natively,
        we fetch assets and filter by distance client-side.

        If start_date/end_date are None, searches all photos by location only.
        """
        if radius_km is None:
            radius_km = self.search_radius_km

        # Build search params
        params: dict[str, Any] = {
            "size": 1000,
            "page": 1,
            "withExif": True,  # Required to get GPS coordinates in results
        }

        # Only add date filters if provided
        if start_date is not None:
            params["takenAfter"] = start_date.isoformat()
        if end_date is not None:
            params["takenBefore"] = end_date.isoformat()

        logger.info(f"Immich search params: {params}")
        resp = await self._client.post("/api/search/metadata", json=params)
        resp.raise_for_status()
        result = resp.json()

        # Handle different API response structures
        items = []
        if "assets" in result and "items" in result["assets"]:
            items = result["assets"]["items"]
        elif "items" in result:
            items = result["items"]

        logger.info(f"Immich returned {len(items)} total assets")

        # Filter by proximity
        filtered_assets = []
        geotagged_count = 0
        for asset in items:
            exif = asset.get("exifInfo", {})
            lat = exif.get("latitude")
            lon = exif.get("longitude")

            if lat is not None and lon is not None:
                geotagged_count += 1
                distance = self._haversine_distance(latitude, longitude, lat, lon)
                if distance <= radius_km:
                    # Add computed fields
                    asset["_distance_km"] = round(distance, 2)
                    asset["_thumbnail_url"] = self.get_thumbnail_url(asset["id"])
                    filtered_assets.append(asset)

        logger.info(f"Immich: {geotagged_count} geotagged, {len(filtered_assets)} within {radius_km}km radius")

        # Sort by distance
        filtered_assets.sort(key=lambda x: x["_distance_km"])

        return filtered_assets

    async def search_by_date_only(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        """
        Search for photos by date range only (no location filtering).

        Used as fallback when no geotagged photos are found for a location.
        """
        params: dict[str, Any] = {
            "size": 1000,
            "page": 1,
            "takenAfter": start_date.isoformat(),
            "takenBefore": end_date.isoformat(),
        }

        logger.info(f"Immich date-only search params: {params}")
        resp = await self._client.post("/api/search/metadata", json=params)
        resp.raise_for_status()
        result = resp.json()

        # Handle different API response structures
        items = []
        if "assets" in result and "items" in result["assets"]:
            items = result["assets"]["items"]
        elif "items" in result:
            items = result["items"]

        logger.info(f"Immich date-only search returned {len(items)} assets")

        # Add thumbnail URLs
        for asset in items:
            asset["_thumbnail_url"] = self.get_thumbnail_url(asset["id"])

        return items

    async def get_asset_thumbnail(
        self, asset_id: str, size: str = "preview"
    ) -> tuple[bytes, str]:
        """Get asset thumbnail. Returns (content, content_type)."""
        resp = await self._client.get(
            f"/api/assets/{asset_id}/thumbnail",
            params={"size": size},
        )
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "image/jpeg")
        return resp.content, content_type

    def get_thumbnail_url(self, asset_id: str) -> str:
        """Generate thumbnail URL for an asset."""
        return f"{self.url}/api/assets/{asset_id}/thumbnail?size=preview"

    async def get_asset_info(self, asset_id: str) -> dict[str, Any]:
        """Get detailed information about a specific asset."""
        resp = await self._client.get(f"/api/assets/{asset_id}")
        resp.raise_for_status()
        return resp.json()

    async def add_assets_to_album(
        self, album_id: str, asset_ids: list[str]
    ) -> None:
        """Add assets to an existing album."""
        resp = await self._client.put(
            f"/api/albums/{album_id}/assets",
            json={"ids": asset_ids},
        )
        resp.raise_for_status()

    async def remove_assets_from_album(
        self, album_id: str, asset_ids: list[str]
    ) -> None:
        """Remove assets from an album."""
        resp = await self._client.delete(
            f"/api/albums/{album_id}/assets",
            json={"ids": asset_ids},
        )
        resp.raise_for_status()

    @staticmethod
    def _haversine_distance(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two GPS points using Haversine formula."""
        R = 6371  # Earth's radius in km

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        return R * c
