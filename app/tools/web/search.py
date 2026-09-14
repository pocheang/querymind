from __future__ import annotations

import logging

from app.core.config import get_settings
from app.tools.web.factory import get_search_provider

logger = logging.getLogger(__name__)

__all__ = ["search_web"]


def search_web(query: str, max_results: int = 5, timeout: int | None = None) -> list[dict]:
    """Execute web search using the configured search provider.

    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 5)
        timeout: Timeout in seconds (default: from settings or 15)

    Returns:
        List of search results with title, href, and body

    Raises:
        Exception: If search fails or times out
    """
    settings = get_settings()
    effective_timeout = timeout if timeout is not None else settings.web_search_timeout_seconds
    provider = get_search_provider(settings)
    return provider.search(query=query, max_results=max_results, timeout=effective_timeout)
