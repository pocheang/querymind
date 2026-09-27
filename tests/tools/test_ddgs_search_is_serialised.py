"""One process runs one DuckDuckGo search at a time -- the whole search, not just the constructor.

Concurrent searches wedge the process at zero CPU: `primp.Client` calls back
into Python logging while it is built, and two threads doing that at once
deadlock with the event loop stuck in `Thread.start()`. The lock that existed
covered `DDGS(...)` only, and in ddgs 9.x that builds nothing -- the clients
are built lazily inside `text()`. Measured on 2026-09-27: one question hung the
process with two threads inside `ddgs.text()`.

These tests use a fake DDGS that records how many searches overlap, so they
assert the property the lock exists for rather than timing anything.
"""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace

import pytest

from app.tools.web.providers import duckduckgo


class _FakeDDGS:
    """Counts concurrent `text()` calls; optionally fails the first attempt part-way."""

    active = 0
    peak = 0
    calls = 0
    guard = threading.Lock()
    fail_first_after_one = False

    def __init__(self, **_kwargs) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_exc) -> None:
        return None

    def text(self, query, **_kwargs):
        cls = type(self)
        with cls.guard:
            cls.active += 1
            cls.peak = max(cls.peak, cls.active)
            cls.calls += 1
            attempt = cls.calls
        try:
            # The lock must be held while text() runs: this is where the clients are built.
            assert duckduckgo._SEARCH_LOCK.locked(), "text() ran outside the search lock"
            time.sleep(0.02)
            yield {"title": f"{query}-1", "href": "https://example.com/1", "body": "one"}
            if cls.fail_first_after_one and attempt == 1:
                raise RuntimeError("rate limited")
            yield {"title": f"{query}-2", "href": "https://example.com/2", "body": "two"}
        finally:
            with cls.guard:
                cls.active -= 1


@pytest.fixture
def fake_ddgs(monkeypatch: pytest.MonkeyPatch):
    _FakeDDGS.active = _FakeDDGS.peak = _FakeDDGS.calls = 0
    _FakeDDGS.fail_first_after_one = False
    monkeypatch.setattr(duckduckgo, "DDGS", _FakeDDGS)
    return _FakeDDGS


def _provider(retries: int = 0) -> duckduckgo.DuckDuckGoSearchProvider:
    return duckduckgo.DuckDuckGoSearchProvider(
        settings=SimpleNamespace(web_proxy_url=None, web_search_max_retries=retries)
    )


def test_concurrent_searches_never_overlap(fake_ddgs) -> None:
    provider = _provider()
    errors: list[BaseException] = []

    def run(query: str) -> None:
        try:
            provider.search(query)
        except BaseException as exc:  # surfaced below; a thread swallows it otherwise
            errors.append(exc)

    threads = [threading.Thread(target=run, args=(f"q{i}",)) for i in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert errors == []
    assert fake_ddgs.calls == 6
    assert fake_ddgs.peak == 1


def test_a_retry_does_not_repeat_the_failed_attempts_results(fake_ddgs) -> None:
    fake_ddgs.fail_first_after_one = True

    results = _provider(retries=1).search("q")

    assert [item["title"] for item in results] == ["q-1", "q-2"]


def test_the_lock_is_released_after_a_failed_search(fake_ddgs) -> None:
    fake_ddgs.fail_first_after_one = True

    with pytest.raises(duckduckgo.WebSearchError):
        _provider(retries=0).search("q")

    assert not duckduckgo._SEARCH_LOCK.locked()
