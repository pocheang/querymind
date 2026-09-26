"""A client cannot choose the address its limits are keyed on (SEC-02, ARC-01 phase 9).

The rate-limit middleware used to take the first value of `X-Forwarded-For`,
and nginx *appended* to that header, so the first value was whatever the client
wrote: rotating it gave every request a fresh bucket and every per-IP limit --
login, registration, the admin operations -- was a limit on nothing.

The fix is one rule in three places, and these tests drive the real mechanism
for each rather than a restatement of it. nginx overwrites the header with the
address it saw (tests/core/test_nginx_proxy_config.py). uvicorn's
`ProxyHeadersMiddleware` -- which `app/gunicorn_worker.py` switches on with
`trusted_proxies()` -- rewrites the connection's client only when the peer is
trusted. And the application reads `request.client.host`, never a header.
"""

from __future__ import annotations

import ast
from pathlib import Path

import httpx
import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api.middleware.rate_limit import RATE_LIMIT_RULES, RateLimitMiddleware
from app.api.transport.client_address import UNKNOWN, client_ip, trusted_proxies

APP = Path(__file__).resolve().parents[2] / "app"
SUBNET = "172.29.72.0/24"  # compose.yaml's default QUERYMIND_SUBNET
NGINX = "172.29.72.5"
_FORWARDING_HEADERS = {"x-forwarded-for", "x-real-ip", "forwarded"}


def _served(app, trusted: str = SUBNET):
    """What a QueryMindWorker hands uvicorn: proxy headers honoured from trusted peers only."""

    return ProxyHeadersMiddleware(app, trusted_hosts=trusted_proxies(trusted))


async def _request(app, peer: str, path: str, *, method: str = "GET", headers: dict[str, str] | None = None):
    transport = httpx.ASGITransport(app=app, client=(peer, 40000))
    async with httpx.AsyncClient(transport=transport, base_url="http://backend") as client:
        return await client.request(method, path, headers=headers or {})


def _whoami():
    return Starlette(routes=[Route("/whoami", lambda request: PlainTextResponse(client_ip(request)))])


@pytest.mark.asyncio
async def test_a_forwarded_header_from_an_untrusted_peer_is_ignored():
    spoofed = {"X-Forwarded-For": "1.2.3.4", "X-Real-IP": "5.6.7.8"}

    response = await _request(_served(_whoami()), "203.0.113.9", "/whoami", headers=spoofed)

    assert response.text == "203.0.113.9"


@pytest.mark.asyncio
async def test_nginx_anywhere_in_the_subnet_names_the_client():
    """The trust is a network, because Docker picks nginx's address -- gunicorn's own check refuses one."""

    response = await _request(_served(_whoami()), NGINX, "/whoami", headers={"X-Forwarded-For": "198.51.100.7"})

    assert response.text == "198.51.100.7"


@pytest.mark.asyncio
async def test_the_default_trusts_only_loopback(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("QUERYMIND_TRUSTED_PROXIES", raising=False)
    app = ProxyHeadersMiddleware(_whoami(), trusted_hosts=trusted_proxies())

    response = await _request(app, NGINX, "/whoami", headers={"X-Forwarded-For": "198.51.100.7"})

    assert trusted_proxies() == ["127.0.0.1"]
    assert response.text == NGINX


@pytest.mark.asyncio
async def test_a_rotating_forwarded_header_does_not_buy_more_attempts():
    """The bypass itself: a fresh X-Forwarded-For per request used to mean a fresh bucket."""

    register = next(rule for rule in RATE_LIMIT_RULES if rule.name == "register")
    inner = Starlette(routes=[Route("/auth/register", lambda request: PlainTextResponse("ok"), methods=["POST"])])
    inner.add_middleware(RateLimitMiddleware)
    app = _served(inner)
    peer = "203.0.113.41"  # distinct from every other test's, so the process-wide counters cannot mix

    statuses = []
    for attempt in range(register.max_requests + 1):
        headers = {"X-Forwarded-For": f"10.9.8.{attempt}", "X-Real-IP": f"10.9.7.{attempt}"}
        statuses.append((await _request(app, peer, "/auth/register", method="POST", headers=headers)).status_code)

    assert statuses == [200] * register.max_requests + [429]


def test_a_request_with_no_peer_is_unknown_rather_than_a_header():
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"x-forwarded-for", b"1.2.3.4")],
        "client": None,
    }

    assert client_ip(Request(scope)) == UNKNOWN


@pytest.mark.parametrize("value", ["not-an-address", f"{SUBNET}, 10.0.0.300", "172.29.72.0/33"])
def test_an_entry_that_does_not_parse_refuses_rather_than_trusting_nobody(value: str):
    """A typo would otherwise key every limit on nginx's address again, with nothing reporting it."""

    bad = value.split(",")[-1].strip()
    with pytest.raises(ValueError, match=bad.split("/")[0]):
        trusted_proxies(value)


def test_the_list_form_is_what_uvicorn_is_given():
    assert trusted_proxies(f" {SUBNET} , ,127.0.0.1 ") == [SUBNET, "127.0.0.1"]
    assert trusted_proxies("*") == ["*"]
    assert trusted_proxies("") == ["127.0.0.1"]


def test_the_environment_supplies_it(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("QUERYMIND_TRUSTED_PROXIES", "10.1.0.0/16")

    assert trusted_proxies() == ["10.1.0.0/16"]


def _header_reads(tree: ast.AST) -> list[int]:
    """Lines reading a forwarding header: `headers.get("X-Forwarded-For")` or `headers["X-Real-IP"]`."""

    found = []
    for node in ast.walk(tree):
        key = None
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get":
            key = node.args[0] if node.args else None
        elif isinstance(node, ast.Subscript):
            key = node.slice
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            if key.value.lower() in _FORWARDING_HEADERS:
                found.append(node.lineno)
    return found


def test_nothing_in_the_application_reads_a_forwarding_header():
    """uvicorn decides from them, once, for trusted peers only; a second reader is the old bypass."""

    offenders = [
        f"{path.relative_to(APP.parent).as_posix()}:{line}"
        for path in sorted(APP.rglob("*.py"))
        for line in _header_reads(ast.parse(path.read_text(encoding="utf-8")))
    ]

    assert not offenders, offenders


def test_the_scanner_can_see_both_shapes():
    source = 'a = request.headers.get("X-Forwarded-For")\nb = request.headers["x-real-ip"]\n'

    assert _header_reads(ast.parse(source)) == [1, 2]
