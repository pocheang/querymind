"""A cached retrieval result is the same in process memory and in Redis (ARC-01 phase 10).

`cache_lookup` / `cache_store` sit in front of hybrid retrieval, and
RETRIEVAL_CACHE_BACKEND (or STATE_BACKEND=shared, which forces Redis) decides
where results live. A hit must be the same answer either way -- which is a
stronger statement than it looks, because Redis stores JSON and so always hands
back a *copy* of what was stored, while a memory cache hands back whatever
object it holds unless it is careful not to.

Results are JSON-safe here on purpose: Redis round-trips through JSON, so a
tuple comes back a list and an integer key a string. That is a property of the
wire format, not a disagreement the two could settle.
"""

from __future__ import annotations

import contextlib
import time

import pytest

from app.core.config import get_settings
from app.retrievers.hybrid import caching


def _no_span(_name, _attrs):
    return contextlib.nullcontext()


@pytest.fixture(params=["memory", "redis"])
def settings(request, settings_env, fake_server, install, monkeypatch):
    import fakeredis

    settings_env(RETRIEVAL_CACHE_BACKEND=request.param, RETRIEVAL_CACHE_TTL_SECONDS="1", STATE_BACKEND="memory")
    caching.drop_local_retrieval_cache()
    if request.param == "redis":
        install(caching._REDIS, fakeredis.FakeRedis(server=fake_server, decode_responses=False))
    else:
        monkeypatch.setattr(caching._REDIS, "_client", None)
        monkeypatch.setattr(caching._REDIS, "_unavailable_until", float("inf"))
    yield get_settings()
    caching.drop_local_retrieval_cache()


def _results() -> list[dict]:
    return [
        {"id": "doc-1#0", "text": "Backups are kept for 35 days.", "score": 0.91, "metadata": {"source": "a.md"}},
        {"id": "doc-2#3", "text": "EU region only.", "score": 0.42, "metadata": {"source": "b.md"}},
    ]


def _lookup(settings, key="q1"):
    return caching.cache_lookup(key, settings, _no_span)


def test_a_miss_is_none(settings):
    assert _lookup(settings) is None


def test_a_stored_result_comes_back_equal_and_marked_as_a_hit(settings):
    caching.cache_store("q1", _results(), {"sources": ["vector", "bm25"]}, settings)

    results, diagnostics = _lookup(settings)

    assert results == _results()
    assert diagnostics["sources"] == ["vector", "bm25"]
    assert diagnostics["cache_hit"] is True


def test_keys_do_not_share_results(settings):
    caching.cache_store("q1", _results(), {}, settings)

    assert _lookup(settings, "q2") is None


def test_changing_results_after_storing_them_does_not_change_the_cache(settings):
    """Retrieval goes on to rerank and mask what it just cached; the cache must hold what was stored."""

    results = _results()
    caching.cache_store("q1", results, {}, settings)

    results[0]["text"] = "[REDACTED]"
    results[0]["metadata"]["source"] = "changed.md"
    results.append({"id": "extra"})

    assert _lookup(settings)[0] == _results()


def test_changing_a_hit_does_not_change_the_next_hit(settings):
    caching.cache_store("q1", _results(), {"sources": ["vector"]}, settings)

    first, diagnostics = _lookup(settings)
    first[0]["score"] = 0.0
    first[1]["metadata"]["source"] = "changed.md"
    diagnostics["sources"].append("web")

    second, again = _lookup(settings)
    assert second == _results()
    assert again["sources"] == ["vector"]


def test_a_result_expires_after_its_ttl(settings):
    caching.cache_store("q1", _results(), {}, settings)
    assert _lookup(settings) is not None

    time.sleep(1.3)

    assert _lookup(settings) is None


def test_clearing_the_cache_forgets_everything(settings):
    caching.cache_store("q1", _results(), {}, settings)

    caching.clear_retrieval_cache()

    assert _lookup(get_settings()) is None


def test_a_disabled_cache_stores_nothing(settings, settings_env):
    backend = settings.retrieval_cache_backend
    settings_env(RETRIEVAL_CACHE_BACKEND=backend, RETRIEVAL_CACHE_ENABLED="false", STATE_BACKEND="memory")
    disabled = get_settings()

    caching.cache_store("q1", _results(), {}, disabled)

    assert _lookup(disabled) is None
    assert _lookup(settings) is None
