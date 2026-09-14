from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.services.observability.log_safety import question_ref
from app.tools.web.base import BaseSearchProvider

logger = logging.getLogger(__name__)


class TavilySearchProvider(BaseSearchProvider):
    """Tavily search provider tailored for LLM and RAG workloads."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings

    @property
    def name(self) -> str:
        return "tavily"

    def _get_active_settings(self) -> Settings:
        return self._settings or get_settings()

    def search(self, query: str, max_results: int = 5, timeout: int = 15) -> list[dict]:
        settings = self._get_active_settings()
        api_key = settings.tavily_api_key
        if not api_key:
            raise ValueError("Tavily API key is not configured (TAVILY_API_KEY is empty)")

        proxy = settings.web_proxy_url or None
        max_retries = max(0, settings.web_search_max_retries)
        url = "https://api.tavily.com/search"
        payload: dict[str, Any] = {
            "api_key": api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
            "include_raw_content": False,
        }

        last_err: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                client_kwargs: dict[str, Any] = {"timeout": timeout, "trust_env": False}
                if proxy:
                    client_kwargs["proxy"] = proxy

                with httpx.Client(**client_kwargs) as client:
                    resp = client.post(url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()

                raw_items = data.get("results", [])
                results = [
                    {
                        "title": item.get("title", ""),
                        "href": item.get("url", ""),
                        "body": item.get("content", ""),
                        "raw_content": item.get("raw_content"),
                    }
                    for item in raw_items
                ]
                logger.debug(
                    "Tavily search returned %d results for %s (attempt %d)",
                    len(results),
                    question_ref(query),
                    attempt + 1,
                )
                return results
            except Exception as exc:
                last_err = exc
                logger.warning(
                    "Tavily search attempt %d/%d failed for %s: %s",
                    attempt + 1,
                    max_retries + 1,
                    question_ref(query),
                    str(exc),
                )
                if attempt < max_retries:
                    time.sleep(0.5 * (attempt + 1))

        if last_err:
            logger.error("Tavily search completely failed for %s: %s", question_ref(query), str(last_err))
            raise last_err

        return []
