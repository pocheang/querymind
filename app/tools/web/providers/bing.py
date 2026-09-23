from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.services.observability.log_safety import question_ref
from app.tools.web.base import BaseSearchProvider, WebSearchError, describe_search_error

logger = logging.getLogger(__name__)


class BingSearchProvider(BaseSearchProvider):
    """Azure / Microsoft Bing Web Search API provider."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings

    @property
    def name(self) -> str:
        return "bing"

    def _get_active_settings(self) -> Settings:
        return self._settings or get_settings()

    def search(self, query: str, max_results: int = 5, timeout: int = 15) -> list[dict]:
        settings = self._get_active_settings()
        api_key = settings.bing_search_api_key
        if not api_key:
            raise ValueError("Bing Search API key is not configured (BING_SEARCH_API_KEY is empty)")

        proxy = settings.web_proxy_url or None
        max_retries = max(0, settings.web_search_max_retries)
        endpoint = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": api_key}
        params = {"q": query, "count": max_results, "responseFilter": "Webpages"}

        last_err: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                client_kwargs: dict[str, Any] = {"timeout": timeout, "trust_env": False}
                if proxy:
                    client_kwargs["proxy"] = proxy

                with httpx.Client(**client_kwargs) as client:
                    resp = client.get(endpoint, headers=headers, params=params)
                    resp.raise_for_status()
                    data = resp.json()

                web_pages = data.get("webPages", {}).get("value", [])
                results = [
                    {
                        "title": item.get("name", ""),
                        "href": item.get("url", ""),
                        "body": item.get("snippet", ""),
                    }
                    for item in web_pages
                ]
                logger.debug(
                    "Bing search returned %d results for %s (attempt %d)",
                    len(results),
                    question_ref(query),
                    attempt + 1,
                )
                return results
            except Exception as exc:
                last_err = exc
                logger.warning(
                    "Bing search attempt %d/%d failed for %s: %s",
                    attempt + 1,
                    max_retries + 1,
                    question_ref(query),
                    describe_search_error(exc),
                )
                if attempt < max_retries:
                    time.sleep(0.5 * (attempt + 1))

        if last_err:
            logger.error(
                "Bing search completely failed for %s: %s", question_ref(query), describe_search_error(last_err)
            )
            # `from None`: the chained client exception would print its URL -- the question -- in any traceback.
            raise WebSearchError(f"{self.name} search failed: {describe_search_error(last_err)}") from None

        return []
