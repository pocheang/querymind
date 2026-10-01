"""Outbound URLs fail closed and connect to the address that was checked (SEC-08).

Four findings, one test group each: a name that did not resolve passed the
check (`any([])` is False); the HTTP client resolved the name again, so a
zero-TTL name could answer the check with a public address and the connection
with 169.254.169.254; the connector probe checked its allowlist on the
*response*, after the request had gone out; and its DNS ran on the event loop.
"""

from __future__ import annotations

import socket
import threading

import httpx
import pytest

from app.services.connectors import management
from app.services.security import network
from app.services.security.network import OutboundURLValidationError, pin_public_http_url, validate_public_http_url


def _answers(monkeypatch, *addresses: str) -> list[str]:
    """Make each successive lookup answer with the next address; record the names asked."""

    asked: list[str] = []
    queue = list(addresses)

    def resolve(host, port, *args, **kwargs):
        asked.append(host)
        address = queue.pop(0) if len(queue) > 1 else queue[0]
        family = socket.AF_INET6 if ":" in address else socket.AF_INET
        return [(family, socket.SOCK_STREAM, 6, "", (address, port))]

    monkeypatch.setattr(network.socket, "getaddrinfo", resolve)
    return asked


def test_a_name_that_does_not_resolve_is_refused(monkeypatch):
    def fail(*args, **kwargs):
        raise socket.gaierror("no such name")

    monkeypatch.setattr(network.socket, "getaddrinfo", fail)

    with pytest.raises(OutboundURLValidationError, match="could not be resolved"):
        validate_public_http_url("https://nowhere.invalid/")


def test_a_name_resolving_to_metadata_is_refused(monkeypatch):
    _answers(monkeypatch, "169.254.169.254")

    with pytest.raises(OutboundURLValidationError):
        pin_public_http_url("https://rebind.example/")


def test_the_pinned_address_is_the_one_that_was_checked(monkeypatch):
    # First answer public, every later one the metadata service: a rebinding
    # name. Whatever is connected to must be an address that passed the check.
    _answers(monkeypatch, "93.184.215.14", "169.254.169.254")

    with pytest.raises(OutboundURLValidationError):
        pin_public_http_url("https://rebind.example/")


def test_the_request_goes_to_the_address_with_the_name_kept(monkeypatch):
    _answers(monkeypatch, "93.184.215.14")
    target = pin_public_http_url("https://api.example.com:8443/v1/ping")

    assert target.request_url() == "https://93.184.215.14:8443/v1/ping"
    assert target.host_header() == "api.example.com:8443"
    assert target.host == "api.example.com"


# --- the connector probe -----------------------------------------------------


@pytest.fixture
def sent(monkeypatch) -> list[httpx.Request]:
    """Capture what the probe sends, and on which thread it resolved."""

    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200)

    real_client = httpx.AsyncClient

    def client(*args, **kwargs):
        return real_client(*args, transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(management.httpx, "AsyncClient", client)
    return requests


@pytest.mark.asyncio
async def test_the_probe_connects_to_the_checked_address(monkeypatch, sent):
    _answers(monkeypatch, "93.184.215.14")

    result = await management.probe_http_connector("https://api.example.com/v1", frozenset({"api.example.com"}))

    assert result.status == "passed"
    assert [str(request.url) for request in sent] == ["https://93.184.215.14/v1"]
    assert sent[0].headers["Host"] == "api.example.com"
    assert sent[0].extensions["sni_hostname"] == "api.example.com"


@pytest.mark.asyncio
async def test_the_allowlist_is_checked_before_anything_is_sent(monkeypatch, sent):
    asked = _answers(monkeypatch, "93.184.215.14")

    result = await management.probe_http_connector("https://other.example.com/", frozenset({"api.example.com"}))

    assert result.status == "failed"
    assert sent == []
    assert asked == []


@pytest.mark.asyncio
async def test_the_probe_resolves_off_the_event_loop(monkeypatch, sent):
    threads: list[str] = []

    def resolve(host, port, *args, **kwargs):
        threads.append(threading.current_thread().name)
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.215.14", port))]

    monkeypatch.setattr(network.socket, "getaddrinfo", resolve)
    await management.probe_http_connector("https://api.example.com/", frozenset({"api.example.com"}))

    assert threads and threading.main_thread().name not in threads
