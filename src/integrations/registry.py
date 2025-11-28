"""Registry for integration providers."""
from typing import Any, Type

from src.integrations.base import IntegrationProvider


class IntegrationRegistry:
    """Central registry for integration providers."""

    _providers: dict[str, Type[IntegrationProvider]] = {}

    @classmethod
    def register(cls, provider_class: Type[IntegrationProvider]) -> Type[IntegrationProvider]:
        """Register a provider class. Can be used as a decorator."""
        cls._providers[provider_class.get_type()] = provider_class
        return provider_class

    @classmethod
    def get_provider(cls, integration_type: str) -> Type[IntegrationProvider] | None:
        """Get a provider class by type."""
        return cls._providers.get(integration_type)

    @classmethod
    def list_types(cls) -> list[str]:
        """List all registered integration types."""
        return list(cls._providers.keys())

    @classmethod
    def get_all_type_info(cls) -> list[dict[str, Any]]:
        """Get information about all registered types."""
        return [
            {
                "type": provider_class.get_type(),
                "name": provider_class.get_display_name(),
                "config_schema": provider_class.get_config_schema(),
            }
            for provider_class in cls._providers.values()
        ]

    @classmethod
    def create_provider(
        cls,
        integration_type: str,
        config: dict[str, Any],
    ) -> IntegrationProvider | None:
        """Create a provider instance with the given config."""
        provider_class = cls.get_provider(integration_type)
        if provider_class is None:
            return None
        return provider_class(config)
