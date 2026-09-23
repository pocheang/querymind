from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.services.observability.log_safety import question_ref
from app.tools.web.base import BaseSearchProvider, WebSearchError, describe_search_error

logger = logging.getLogger(__name__)


class SearXNGSearchProvider(BaseSearchProvider):
    """SearXNG self-hosted open-source meta search engine provider."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings

    @property
    def name(self) -> str:
        return "searxng"

    def _get_active_settings(self) -> Settings:
        return self._settings or get_settings()

    def search(self, query: str, max_results: int = 5, timeout: int = 15) -> list[dict]:
        settings = self._get_active_settings()
        base_url = settings.searxng_base_url
        if not base_url:
            raise ValueError("SearXNG base URL is not configured (SEARXNG_BASE_URL is empty)")

        proxy = settings.web_proxy_url or None
        max_retries = max(0, settings.web_search_max_retries)
        endpoint = f"{base_url.rstrip('/')}/search"
        params = {"q": query, "format": "json"}

        last_err: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                client_kwargs: dict[str, Any] = {"timeout": timeout, "trust_env": False}
                if proxy:
                    client_kwargs["proxy"] = proxy

                with httpx.Client(**client_kwargs) as client:
                    resp = client.get(endpoint, params=params)
                    resp.raise_for_status()
                    data = resp.json()

                raw_results = data.get("results", [])[:max_results]
                results = [
                    {
                        "title": item.get("title", ""),
                        "href": item.get("url", ""),
                        "body": item.get("content", ""),
                    }
                    for item in raw_results
                ]
                logger.debug(
                    "SearXNG search returned %d results for %s (attempt %d)",
                    len(results),
                    question_ref(query),
                    attempt + 1,
                )
                return results
            except Exception as exc:
                last_err = exc
                logger.warning(
                    "SearXNG search attempt %d/%d failed for %s: %s",
                    attempt + 1,
                    max_retries + 1,
                    question_ref(query),
                    describe_search_error(exc),
                )
                if attempt < max_retries:
                    time.sleep(0.5 * (attempt + 1))

        if last_err:
            logger.error(
                "SearXNG search completely failed for %s: %s", question_ref(query), describe_search_error(last_err)
            )
            # `from None`: the chained client exception would print its URL -- the question -- in any traceback.
            raise WebSearchError(f"{self.name} search failed: {describe_search_error(last_err)}") from None

        return []
