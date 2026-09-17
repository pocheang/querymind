from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

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


def test_an_unknown_provider_cannot_be_configured():
    """`WEB_SEARCH_PROVIDER` used to accept any string and fall back silently.

    A typo searched DuckDuckGo while the admin page reported `tavly`, so the
    deployment's chosen provider was quietly not the one in use. The set is on the
    field now, so this is a refused write and a loud startup instead.
    """

    with pytest.raises(ValidationError, match="WEB_SEARCH_PROVIDER"):
        Settings(WEB_SEARCH_PROVIDER="unknown_engine")


def test_the_factory_still_falls_back_if_it_is_handed_one_anyway():
    """Defence in depth, and the reason the branch is kept rather than deleted.

    `get_search_provider` takes any object with the attribute -- a `model_construct`
    skips validation, and so would a future provider named in configuration before
    its class exists. Answering with DuckDuckGo beats raising inside retrieval.
    """

    settings = Settings.model_construct(web_search_provider="unknown_engine", web_proxy_url=None)

    assert isinstance(get_search_provider(settings), DuckDuckGoSearchProvider)


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
