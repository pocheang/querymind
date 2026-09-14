from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.tools.web.base import BaseSearchProvider
from app.tools.web.factory import clear_provider_cache, get_search_provider
from app.tools.web.providers.bing import BingSearchProvider
from app.tools.web.providers.duckduckgo import DuckDuckGoSearchProvider
from app.tools.web.providers.searxng import SearXNGSearchProvider
from app.tools.web.providers.tavily import TavilySearchProvider
from app.tools.web.search import search_web


@pytest.fixture(autouse=True)
def _reset_provider_cache():
    clear_provider_cache()
    yield
    clear_provider_cache()


def test_factory_returns_duckduckgo_by_default():
    settings = Settings(WEB_SEARCH_PROVIDER="duckduckgo")
    provider = get_search_provider(settings)
    assert isinstance(provider, DuckDuckGoSearchProvider)
    assert provider.name == "duckduckgo"


def test_factory_returns_tavily():
    settings = Settings(WEB_SEARCH_PROVIDER="tavily", TAVILY_API_KEY="tvly-mock-key")
    provider = get_search_provider(settings)
    assert isinstance(provider, TavilySearchProvider)
    assert provider.name == "tavily"


def test_factory_returns_bing():
    settings = Settings(WEB_SEARCH_PROVIDER="bing", BING_SEARCH_API_KEY="bing-mock-key")
    provider = get_search_provider(settings)
    assert isinstance(provider, BingSearchProvider)
    assert provider.name == "bing"


def test_factory_returns_searxng():
    settings = Settings(WEB_SEARCH_PROVIDER="searxng", SEARXNG_BASE_URL="http://localhost:8888")
    provider = get_search_provider(settings)
    assert isinstance(provider, SearXNGSearchProvider)
    assert provider.name == "searxng"


def test_factory_unknown_provider_falls_back_to_duckduckgo():
    settings = Settings(WEB_SEARCH_PROVIDER="unknown_engine")
    provider = get_search_provider(settings)
    assert isinstance(provider, DuckDuckGoSearchProvider)


def test_tavily_provider_search_success():
    settings = Settings(WEB_SEARCH_PROVIDER="tavily", TAVILY_API_KEY="tvly-test-123")
    provider = TavilySearchProvider(settings)

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "results": [
            {
                "title": "Tavily Title",
                "url": "https://example.com/tavily",
                "content": "Tavily content snippet",
                "score": 0.9,
            }
        ]
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        results = provider.search("test query", max_results=2)

    assert len(results) == 1
    assert results[0]["title"] == "Tavily Title"
    assert results[0]["href"] == "https://example.com/tavily"
    assert results[0]["body"] == "Tavily content snippet"


def test_bing_provider_search_success():
    settings = Settings(WEB_SEARCH_PROVIDER="bing", BING_SEARCH_API_KEY="bing-key-xyz")
    provider = BingSearchProvider(settings)

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "webPages": {
            "value": [
                {
                    "name": "Bing Page",
                    "url": "https://example.com/bing",
                    "snippet": "Bing result snippet",
                }
            ]
        }
    }

    with patch("httpx.Client.get", return_value=mock_resp):
        results = provider.search("bing query", max_results=3)

    assert len(results) == 1
    assert results[0]["title"] == "Bing Page"
    assert results[0]["href"] == "https://example.com/bing"
    assert results[0]["body"] == "Bing result snippet"


def test_searxng_provider_search_success():
    settings = Settings(WEB_SEARCH_PROVIDER="searxng", SEARXNG_BASE_URL="https://search.local")
    provider = SearXNGSearchProvider(settings)

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "results": [
            {
                "title": "SearXNG Page",
                "url": "https://example.com/searxng",
                "content": "SearXNG result content",
            }
        ]
    }

    with patch("httpx.Client.get", return_value=mock_resp):
        results = provider.search("searxng query", max_results=5)

    assert len(results) == 1
    assert results[0]["title"] == "SearXNG Page"
    assert results[0]["href"] == "https://example.com/searxng"
    assert results[0]["body"] == "SearXNG result content"


def test_search_web_delegates_to_factory(monkeypatch: pytest.MonkeyPatch):
    mock_provider = MagicMock(spec=BaseSearchProvider)
    mock_provider.search.return_value = [{"title": "Delegated", "href": "https://test.com", "body": "Snippet"}]

    monkeypatch.setattr("app.tools.web.search.get_search_provider", lambda settings=None: mock_provider)

    results = search_web("my query", max_results=3, timeout=10)
    assert len(results) == 1
    assert results[0]["title"] == "Delegated"
    mock_provider.search.assert_called_once_with(query="my query", max_results=3, timeout=10)
