"""The web source asks for more than it keeps, and reads the pages it keeps.

Measured on 2026-09-27 over eight real questions, with an empty corpus so the
web was the only source: five raw results through the strict allowlist left
2/0/0/1/0/0/1/0 accepted, and each accepted result was a 93-306 character
snippet. Answers of 1.5k-6k characters were then written on top of that, and
the verifier rejected them for exceeding their sources -- correctly.

Two changes, both pinned here: ask for 20 and keep the first 5 that pass the
unchanged filter; and replace a kept result's snippet with the passages of its
page that bear on the question. `tests/tools/test_page_fetch.py` covers what may
be fetched; this file covers how the web source uses it.
"""

from __future__ import annotations

import pytest

import app.agents.rag.web as web
from app.core.config import get_settings

PAGE = "\n".join(
    [
        "Kubernetes is an open-source system for automating deployment and scaling of containers.",
        "The weather section of the page, with nothing to do with the question at all here.",
    ]
)


def _results(count: int, host: str = "en.wikipedia.org") -> list[dict]:
    return [
        {"title": f"t{index}", "href": f"https://{host}/wiki/{index}", "body": f"snippet {index}"}
        for index in range(count)
    ]


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch):
    def install(**overrides):
        active = get_settings().model_copy(update=overrides)
        monkeypatch.setattr(web, "get_settings", lambda: active)
        return active

    return install


@pytest.fixture
def pages(monkeypatch: pytest.MonkeyPatch):
    """Replace page reading, recording which URLs were read and with what filter."""

    calls: list[dict] = []

    def install(text: str | None):
        def fake(url, *, host_allowed, timeout_seconds, proxy=None):
            calls.append({"url": url, "host_allowed": host_allowed, "timeout": timeout_seconds})
            return text

        monkeypatch.setattr(web, "fetch_page_text", fake)
        return calls

    return install


def test_it_asks_for_twenty_and_keeps_five(monkeypatch, settings):
    settings(web_fetch_pages_enabled=False)
    asked: list[int] = []

    def search(question, max_results=5):
        asked.append(max_results)
        return _results(12)

    monkeypatch.setattr(web, "search_web", search)

    result = web.run_web_research("what is kubernetes")

    assert asked == [20]
    assert [c["source"] for c in result["citations"]] == [f"https://en.wikipedia.org/wiki/{i}" for i in range(5)]


def test_the_filter_still_decides_what_is_kept(monkeypatch, settings):
    """More candidates, same trust policy: a rejected host stays rejected however many are asked for."""

    settings(web_fetch_pages_enabled=False)
    monkeypatch.setattr(web, "search_web", lambda question, max_results=5: _results(15, "blog.csdn.net") + _results(1))

    result = web.run_web_research("what is kubernetes")

    assert [c["source"] for c in result["citations"]] == ["https://en.wikipedia.org/wiki/0"]


def test_a_read_page_contributes_the_passages_that_bear_on_the_question(monkeypatch, settings, pages):
    settings(web_fetch_pages_enabled=True, web_fetch_max_pages=3)
    pages(PAGE)
    monkeypatch.setattr(web, "search_web", lambda question, max_results=5: _results(1))

    result = web.run_web_research("What is Kubernetes?")

    citation = result["citations"][0]
    assert "open-source system for automating deployment" in citation["content"]
    assert "weather" not in citation["content"]
    assert citation["content"].startswith("snippet 0"), "the snippet is kept beside the passages"
    assert citation["metadata"]["page_read"] is True
    assert "open-source system" in result["context"], "the legacy context carries the same text"
    assert result["metrics"]["pages_read"] == 1


def test_an_unreadable_page_keeps_its_snippet(monkeypatch, settings, pages):
    """Reading can only add evidence, never remove it."""

    settings(web_fetch_pages_enabled=True)
    pages(None)
    monkeypatch.setattr(web, "search_web", lambda question, max_results=5: _results(2))

    result = web.run_web_research("What is Kubernetes?")

    assert [c["content"] for c in result["citations"]] == ["snippet 0", "snippet 1"]
    assert all("page_read" not in c["metadata"] for c in result["citations"])


def test_a_page_sharing_nothing_with_the_question_keeps_its_snippet(monkeypatch, settings, pages):
    settings(web_fetch_pages_enabled=True)
    pages("A page entirely about gardening, tomatoes, soil, and nothing technical whatsoever.")
    monkeypatch.setattr(web, "search_web", lambda question, max_results=5: _results(1))

    result = web.run_web_research("What is Kubernetes?")

    assert result["citations"][0]["content"] == "snippet 0"


def test_only_the_first_few_pages_are_read(monkeypatch, settings, pages):
    settings(web_fetch_pages_enabled=True, web_fetch_max_pages=2, web_fetch_timeout_seconds=3.0)
    calls = pages(PAGE)
    monkeypatch.setattr(web, "search_web", lambda question, max_results=5: _results(5))

    web.run_web_research("What is Kubernetes?")

    assert sorted(call["url"] for call in calls) == [
        "https://en.wikipedia.org/wiki/0",
        "https://en.wikipedia.org/wiki/1",
    ]
    assert {call["timeout"] for call in calls} == {3.0}


def test_switched_off_no_page_is_read(monkeypatch, settings, pages):
    settings(web_fetch_pages_enabled=False)
    calls = pages(PAGE)
    monkeypatch.setattr(web, "search_web", lambda question, max_results=5: _results(3))

    web.run_web_research("What is Kubernetes?")

    assert calls == []


def test_every_hop_of_a_page_read_faces_the_same_filter_the_result_did(monkeypatch, settings, pages):
    """The filter handed to the fetcher is what stops a redirect leaving the trusted set."""

    settings(web_fetch_pages_enabled=True)
    calls = pages(PAGE)
    monkeypatch.setattr(web, "search_web", lambda question, max_results=5: _results(1))

    web.run_web_research("What is Kubernetes?")

    host_allowed = calls[0]["host_allowed"]
    assert host_allowed("https://en.wikipedia.org/wiki/Other") is True
    assert host_allowed("https://blog.csdn.net/redirected") is False
