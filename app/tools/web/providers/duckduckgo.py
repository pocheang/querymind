from __future__ import annotations

import logging
import threading
import time
from typing import Any

from ddgs import DDGS

from app.core.config import Settings, get_settings
from app.services.observability.log_safety import question_ref
from app.tools.web.base import BaseSearchProvider, WebSearchError, describe_search_error

logger = logging.getLogger(__name__)

# Held for the WHOLE search -- construction and `text()` -- so one process runs
# one DuckDuckGo search at a time. Concurrent searches wedge the process at zero
# CPU: `primp.Client` (Rust) calls back into Python logging while it is built,
# and two threads doing that at once deadlock with a third stuck in
# `Thread.start()` -- which is the event loop, so `/health` stops answering too.
#
# This lock used to cover only `DDGS(...)`, and in ddgs 9.x that builds nothing:
# the primp clients are built lazily inside `text()`, per engine, in
# `_get_engines` -> `HttpClient.__init__`. Measured on 2026-09-27 (ddgs 9.12.0):
# one question wedged the process with two threads at `ddgs.text()` -- one in
# `http_client.py:53`, one in `logging.getLogger` -- and the loop in
# `Thread.start()`. Serialising costs a second or two per extra query; the
# alternative is a process that answers nothing.
_SEARCH_LOCK = threading.Lock()


def _resolve_ddgs_eagerly() -> None:
    """Trigger the proxy metaclass resolution once at module import."""
    try:
        DDGS.text  # noqa: B018 - attribute access triggers proxy import
    except Exception:
        logger.warning("ddgs could not be resolved at import; web search may be slow on first use")


_resolve_ddgs_eagerly()


class DuckDuckGoSearchProvider(BaseSearchProvider):
    """DuckDuckGo web search provider with proxy support, concurrency protection, and retries."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings

    @property
    def name(self) -> str:
        return "duckduckgo"

    def _get_active_settings(self) -> Settings:
        return self._settings or get_settings()

    def search(self, query: str, max_results: int = 5, timeout: int = 15) -> list[dict]:
        settings = self._get_active_settings()
        proxy = settings.web_proxy_url or None
        max_retries = max(0, settings.web_search_max_retries)
        last_err: Exception | None = None
        for attempt in range(max_retries + 1):
            # Per attempt: a failed attempt's partial results used to stay in the
            # list and be appended to again by the retry.
            results: list[dict] = []
            try:
                client_kwargs: dict[str, Any] = {"timeout": timeout}
                if proxy:
                    client_kwargs["proxy"] = proxy
                with _SEARCH_LOCK, DDGS(**client_kwargs) as ddgs:
                    for item in ddgs.text(query, max_results=max_results, region="wt-wt", safesearch="moderate"):
                        results.append(
                            {
                                "title": item.get("title", ""),
                                "href": item.get("href", ""),
                                "body": item.get("body", ""),
                            }
                        )
                logger.debug(
                    "DuckDuckGo search returned %d results for %s (attempt %d)",
                    len(results),
                    question_ref(query),
                    attempt + 1,
                )
                return results
            except Exception as exc:
                last_err = exc
                logger.warning(
                    "DuckDuckGo search attempt %d/%d failed for %s: %s",
                    attempt + 1,
                    max_retries + 1,
                    question_ref(query),
                    describe_search_error(exc),
                )
                if attempt < max_retries:
                    time.sleep(0.5 * (attempt + 1))

        if last_err:
            logger.error(
                "DuckDuckGo search completely failed for %s: %s", question_ref(query), describe_search_error(last_err)
            )
            # `from None`: the chained client exception would print its URL -- the question -- in any traceback.
            raise WebSearchError(f"{self.name} search failed: {describe_search_error(last_err)}") from None

        return results
