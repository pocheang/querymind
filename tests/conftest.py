"""Suite-wide fixtures. Keep this file small: a fixture here runs for every test."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_page_reads_from_the_suite(monkeypatch: pytest.MonkeyPatch) -> None:
    """A test that stubs `search_web` must not go on to fetch the pages it named.

    `run_web_research` reads the pages behind accepted results
    (`WEB_FETCH_PAGES_ENABLED` defaults on), so without this every test that
    returns a fake allowlisted URL would make a real HTTPS request -- slow, flaky,
    and different on a machine with no network. Here a page reads as unreadable,
    which is the path that keeps the snippet. Tests of page reading replace
    this with their own stub.
    """

    monkeypatch.setattr("app.agents.rag.web.fetch_page_text", lambda *args, **kwargs: None)
