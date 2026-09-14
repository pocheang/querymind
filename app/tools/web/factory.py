from __future__ import annotations

import logging
import threading

from app.core.config import Settings, get_settings
from app.tools.web.base import BaseSearchProvider
from app.tools.web.providers.bing import BingSearchProvider
from app.tools.web.providers.duckduckgo import DuckDuckGoSearchProvider
from app.tools.web.providers.searxng import SearXNGSearchProvider
from app.tools.web.providers.tavily import TavilySearchProvider

logger = logging.getLogger(__name__)

_PROVIDER_CACHE: dict[str, BaseSearchProvider] = {}
_PROVIDER_LOCK = threading.Lock()


def get_search_provider(settings: Settings | None = None) -> BaseSearchProvider:
    """Resolve and return the configured BaseSearchProvider instance."""
    active_settings = settings or get_settings()
    provider_name = (active_settings.web_search_provider or "duckduckgo").strip().lower()

    # Cache key includes provider name and proxy configuration
    cache_key = f"{provider_name}:{active_settings.web_proxy_url or ''}"

    with _PROVIDER_LOCK:
        if cache_key in _PROVIDER_CACHE:
            return _PROVIDER_CACHE[cache_key]

        provider: BaseSearchProvider
        if provider_name == "tavily":
            provider = TavilySearchProvider(active_settings)
        elif provider_name == "bing":
            provider = BingSearchProvider(active_settings)
        elif provider_name == "searxng":
            provider = SearXNGSearchProvider(active_settings)
        else:
            if provider_name != "duckduckgo":
                logger.warning(
                    "Unknown search provider %r configured; defaulting to 'duckduckgo'",
                    provider_name,
                )
            provider = DuckDuckGoSearchProvider(active_settings)

        _PROVIDER_CACHE[cache_key] = provider
        return provider


def clear_provider_cache() -> None:
    """Clear cached provider instances, useful in testing or after config reload."""
    with _PROVIDER_LOCK:
        _PROVIDER_CACHE.clear()
