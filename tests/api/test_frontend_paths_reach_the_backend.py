"""Every backend path the frontend requests exists, under one prefix (ARC-06).

Every endpoint is `/api/v1/...`; the production frontend is built with
VITE_API_BASE_URL=/api and served by an nginx that proxies only `/api/`, so
there is nothing to rewrite and nothing that can be reached in development and
missed in production. It used to be otherwise: bare routes such as `/admin/users`
were requested as `/api/admin/users` and reached the router only if a rewrite
knew their first segment. `admin`, `user` and `model-catalog` were missing from
that list and the whole admin console answered 404 behind nginx while development
(which proxied the bare paths) worked.

The guard intersects two facts rather than keeping a third list: the path
literals in the frontend's API layer and the backend's OpenAPI document.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import main

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "frontend" / "src"
ADMIN = {"X-Test-User": "ops-admin", "X-Test-User-Id": "ops-admin", "X-Test-Role": "admin"}

# Reachable by a fixed name, not an application endpoint.
INFRASTRUCTURE = {"/", "/health", "/ready", "/ready/dependencies", "/metrics"}


def _backend_paths() -> set[str]:
    return set(main.app.openapi()["paths"])


def _frontend_api_literals() -> set[str]:
    found: set[str] = set()
    for path in [*SOURCE.rglob("*.ts"), *SOURCE.rglob("*.tsx")]:
        if ".test." in path.name:
            continue
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"[\"'`](/api/v1/(?:[A-Za-z0-9_\-/.]|\$\{[^}]*\})*)", text):
            found.add(match.group(1).split("?")[0].rstrip("/"))
    return found


def test_every_application_endpoint_is_under_one_prefix():
    outside = {
        path
        for path in _backend_paths()
        if not path.startswith("/api/v1/") and path not in INFRASTRUCTURE and not path.startswith("/app")
    }
    assert outside == set()


def test_every_path_the_frontend_requests_names_a_backend_route():
    literals = _frontend_api_literals()
    assert literals, "the scan matched nothing -- it has stopped reading the frontend"
    backend = {re.sub(r"\{[^}]+\}", "{p}", path) for path in _backend_paths()}
    unknown = sorted(literal for literal in literals if not any(_matches(literal, route) for route in backend))
    assert unknown == []


def _matches(literal: str, route: str) -> bool:
    """`${x}` holes match any one segment of the route, including a fixed one (`/${action}` -> `/enable`)."""

    parts = re.split(r"\$\{[^}]*\}", literal)
    pattern = "[^/]+".join(re.escape(part) for part in parts)
    return re.match(pattern, route) is not None


@pytest.mark.parametrize("path", ["/api/v1/admin/system-logs", "/api/v1/admin/users", "/api/v1/model-catalog"])
def test_admin_paths_answer(path):
    response = TestClient(main.app).get(path, headers=ADMIN)

    assert response.status_code == 200, response.text


def test_the_active_model_poll_answers():
    response = TestClient(main.app).get(
        "/api/v1/user/active-model", headers={"X-Test-User": "u1", "X-Test-User-Id": "u1", "X-Test-Role": "viewer"}
    )

    assert response.status_code != 404, response.text


@pytest.mark.parametrize(
    "old", ["/admin/users", "/api/admin/users", "/sessions", "/api/sessions", "/auth/me", "/api/advanced-rag/health"]
)
def test_the_old_spellings_are_gone(old):
    """No alias: one spelling per endpoint. A 404 (or the SPA's 200 HTML for a GET) is not the API answering."""

    response = TestClient(main.app).get(old, headers=ADMIN)

    assert response.status_code == 404 or "text/html" in response.headers.get("content-type", ""), old


# ---- every middleware sees the path the router sees ------------------------------------
#
# Reaching the router is not enough: the rate limiter, the request metrics and the
# invalidation check each read the path too. The rewrite used to be registered
# first, which in Starlette makes it the *innermost* middleware, so behind the
# production nginx the limiter saw `/api/auth/register`, matched no rule, and
# limited nothing the frontend sends. Found in the phase 9 container run: six
# registrations through nginx under a rule allowing three, all 200.


def test_the_prefix_rewrite_runs_before_every_other_middleware():
    from app.api.application.factory import rewrite_app_prefixed_api_paths

    outermost = main.app.user_middleware[0]

    assert outermost.kwargs.get("dispatch") is rewrite_app_prefixed_api_paths


@pytest.mark.asyncio
async def test_a_rate_limit_applies_to_the_path_the_frontend_sends():
    """`create-admin` allows one request an hour per address; the /api spelling must share that bucket.

    Unauthenticated, so the first request is refused by the route before it can
    write anything; the second must be refused by the middleware.
    """

    import httpx

    from app.api.middleware.rate_limit import RATE_LIMIT_RULES

    rule = next(rule for rule in RATE_LIMIT_RULES if rule.name == "admin_create")
    transport = httpx.ASGITransport(app=main.app, client=("198.51.100.91", 40000))
    async with httpx.AsyncClient(transport=transport, base_url="http://backend") as client:
        statuses = [
            (await client.post("/api/v1/admin/users/create-admin", json={})).status_code
            for _ in range(rule.max_requests + 1)
        ]

    assert 429 not in statuses[: rule.max_requests]
    assert statuses[-1] == 429


def test_the_default_oauth_redirect_names_a_route():
    """`OAUTH_REDIRECT_URI` defaulted to `/api/auth/google/callback` after the move to one prefix, a path that
    no longer exists: Google would have sent every sign-in to a 404."""

    from urllib.parse import urlparse

    from app.core.config import Settings

    default = Settings.model_fields["google_redirect_uri"].default
    assert urlparse(default).path in _backend_paths()
