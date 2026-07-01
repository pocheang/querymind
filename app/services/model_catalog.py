"""
Immutable model provider catalog.

This module defines the canonical source of truth for provider capabilities,
default models, and constraints. All backend configuration derives from this catalog.
"""

from typing import Any, TypedDict


class ProviderInfo(TypedDict):
    """Provider capability and default model information."""

    supports_chat: bool
    supports_embeddings: bool
    default_chat_model: str | None
    default_embedding_model: str | None
    display_name: str
    requires_api_key: bool


# Immutable provider catalog - the single source of truth for provider capabilities
PROVIDER_CATALOG: dict[str, ProviderInfo] = {
    "local": {
        "supports_chat": True,
        "supports_embeddings": True,
        "default_chat_model": "local-evidence",
        "default_embedding_model": "local-hash-384",
        "display_name": "Local (Ollama)",
        "requires_api_key": False,
    },
    "openai": {
        "supports_chat": True,
        "supports_embeddings": True,
        "default_chat_model": "gpt-4o",
        "default_embedding_model": "text-embedding-3-small",
        "display_name": "OpenAI",
        "requires_api_key": True,
    },
    "anthropic": {
        "supports_chat": True,
        "supports_embeddings": False,  # Anthropic does not provide embeddings
        "default_chat_model": "claude-sonnet-4-20250514",
        "default_embedding_model": None,
        "display_name": "Anthropic",
        "requires_api_key": True,
    },
    "deepseek": {
        "supports_chat": True,
        "supports_embeddings": False,  # DeepSeek does not provide embeddings
        "default_chat_model": "deepseek-chat",
        "default_embedding_model": None,
        "display_name": "DeepSeek",
        "requires_api_key": True,
    },
    "custom": {
        "supports_chat": True,
        "supports_embeddings": True,
        "default_chat_model": None,  # User must specify
        "default_embedding_model": None,  # User must specify
        "display_name": "Custom",
        "requires_api_key": True,
    },
}


def get_provider_defaults(provider: str) -> dict[str, Any]:
    """
    Get default model configuration for a provider.

    Args:
        provider: Provider name (e.g., "local", "openai", "anthropic")

    Returns:
        Dictionary with chat_model and embedding_model defaults
    """
    provider = provider.lower().strip() if provider else "local"

    if provider not in PROVIDER_CATALOG:
        provider = "local"

    info = PROVIDER_CATALOG[provider]

    return {
        "chat_model": info["default_chat_model"],
        "embedding_model": info["default_embedding_model"],
    }


def get_provider_info(provider: str) -> ProviderInfo:
    """
    Get full provider information from the catalog.

    Args:
        provider: Provider name

    Returns:
        ProviderInfo dictionary
    """
    provider = provider.lower().strip() if provider else "local"
    return PROVIDER_CATALOG.get(provider, PROVIDER_CATALOG["local"])


def list_providers() -> list[dict[str, Any]]:
    """
    List all available providers with their capabilities.

    Returns:
        List of provider information dictionaries
    """
    return [
        {
            "name": name,
            **info,
        }
        for name, info in PROVIDER_CATALOG.items()
    ]
