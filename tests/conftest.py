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


# A public address (is_global) for names the outbound URL check resolves.
PUBLIC_TEST_ADDRESS = "93.184.215.14"


@pytest.fixture
def resolvable_public_hosts(monkeypatch: pytest.MonkeyPatch) -> str:
    """Make every name resolve to one public address for the outbound URL check.

    Since SEC-08 a name that does not resolve is refused rather than passed.
    Tests that create connectors for `example.invalid` -- a TLD reserved never
    to resolve -- passed only through that fail-open path; they need DNS
    answered, not the check weakened.
    """

    import socket

    def resolve(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC_TEST_ADDRESS, port))]

    monkeypatch.setattr("app.services.security.network.socket.getaddrinfo", resolve)
    return PUBLIC_TEST_ADDRESS
