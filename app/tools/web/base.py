from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from app.services.observability.log_safety import install_http_url_redaction

# Installed where the questions leave as URLs, so it is in place before any
# provider sends one -- in the app, a script or a test alike.
install_http_url_redaction()


class WebSearchError(RuntimeError):
    """A web search failed. Its message never carries the request URL.

    Providers used to log `str(exc)` and re-raise the client's own exception,
    and an httpx error's message is the full request URL -- which, for every
    provider that sends the query as a GET parameter, is the user's question.
    The log line beside it carefully printed `question_ref(query)`, and the
    question went out anyway, twice per failure, then a third time from the
    caller's `logger.exception`. The AST guard on question text in logs could
    not see it: it checks what is passed to the logger, not what an exception
    says.
    """


def describe_search_error(exc: BaseException) -> str:
    """What failed, without anything the request carried: the type and any HTTP status."""

    status = getattr(getattr(exc, "response", None), "status_code", None)
    return f"{type(exc).__name__} (HTTP {status})" if status else type(exc).__name__


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
