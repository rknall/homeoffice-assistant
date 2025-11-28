"""Base classes for integration providers."""
from abc import ABC, abstractmethod
from typing import Any


class IntegrationProvider(ABC):
    """Base class for all integrations."""

    @classmethod
    @abstractmethod
    def get_type(cls) -> str:
        """Unique identifier for this integration type."""
        ...

    @classmethod
    @abstractmethod
    def get_display_name(cls) -> str:
        """Human-readable name for this integration."""
        ...

    @classmethod
    @abstractmethod
    def get_config_schema(cls) -> dict[str, Any]:
        """JSON Schema for configuration form generation."""
        ...

    @abstractmethod
    def __init__(self, config: dict[str, Any]):
        """Initialize with decrypted config."""
        ...

    @abstractmethod
    async def health_check(self) -> tuple[bool, str]:
        """Check connectivity. Returns (success, message)."""
        ...

    async def close(self) -> None:
        """Clean up resources."""
        pass


class DocumentProvider(IntegrationProvider):
    """Interface for document management systems (Paperless, etc.)"""

    @abstractmethod
    async def list_storage_paths(self) -> list[dict[str, Any]]:
        """List available storage paths."""
        ...

    @abstractmethod
    async def list_tags(self) -> list[dict[str, Any]]:
        """List all tags."""
        ...

    @abstractmethod
    async def create_tag(self, name: str) -> dict[str, Any]:
        """Create a new tag."""
        ...

    @abstractmethod
    async def get_tag_by_name(self, name: str) -> dict[str, Any] | None:
        """Get a tag by name."""
        ...

    @abstractmethod
    async def get_documents(
        self,
        tag_id: int | None = None,
        storage_path_id: int | None = None,
        custom_field_value: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query documents with filters."""
        ...

    @abstractmethod
    async def download_document(self, doc_id: int) -> tuple[bytes, str, str]:
        """Download document. Returns (content, filename, mime_type)."""
        ...


class PhotoProvider(IntegrationProvider):
    """Interface for photo management systems (Immich, etc.)"""

    @abstractmethod
    async def list_albums(self) -> list[dict[str, Any]]:
        """List available albums."""
        ...

    @abstractmethod
    async def create_album(self, name: str) -> dict[str, Any]:
        """Create a new album."""
        ...

    @abstractmethod
    async def get_assets(
        self,
        album_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query assets with filters."""
        ...

    @abstractmethod
    async def download_asset(self, asset_id: str) -> tuple[bytes, str, str]:
        """Download asset. Returns (content, filename, mime_type)."""
        ...


class EmailProvider(IntegrationProvider):
    """Interface for email sending (SMTP, etc.)"""

    @abstractmethod
    async def send_email(
        self,
        to: list[str],
        subject: str,
        body: str,
        attachments: list[tuple[str, bytes, str]] | None = None,
    ) -> bool:
        """Send email with optional attachments. Returns success."""
        ...
