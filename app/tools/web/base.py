from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod


class BaseSearchProvider(ABC):
    """Abstract base class for all web search providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier (e.g. duckduckgo, tavily, bing, searxng)."""
        ...

    @abstractmethod
    def search(self, query: str, max_results: int = 5, timeout: int = 15) -> list[dict]:
        """Synchronously execute web search and return a list of dicts with title, href, body."""
        ...

    async def search_async(self, query: str, max_results: int = 5, **kwargs: object) -> list[dict]:
        """Asynchronously execute web search. Default implementation delegates to search via asyncio.to_thread."""
        return await asyncio.to_thread(self.search, query, max_results=max_results, **kwargs)
