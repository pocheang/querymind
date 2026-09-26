"""Every backend path the production frontend requests reaches the backend (ARC-01 phase 9).

The production frontend is built with VITE_API_BASE_URL=/api and served by an
nginx that proxies only `/api/`, so a bare route such as `/admin/users` is
requested as `/api/admin/users` and reaches the router only if
`rewrite_app_prefixed_api_paths` strips the prefix for its first segment.
`admin`, `user` and `model-catalog` were missing from that list, so behind the
production nginx the whole admin console answered 404 -- and nothing noticed,
because development proxies the bare paths straight through Vite and the CI
smoke test checks only `/api/advanced-rag/health`.

The guard intersects two facts rather than keeping a third list: the first
segments of the backend's bare routes (from its OpenAPI document) and the path
literals in the frontend's API layer. A literal like `/export` is a suffix, not
a route, and drops out because no bare route starts with it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import main
from app.api.application.factory import _LEGACY_API_PREFIX_SEGMENTS

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ROOT / "frontend" / "src" / "services"
ADMIN = {"X-Test-User": "ops-admin", "X-Test-User-Id": "ops-admin", "X-Test-Role": "admin"}


def _bare_route_segments() -> set[str]:
    paths = main.app.openapi()["paths"]
    return {path.split("/")[1] for path in paths if path.split("/")[1] and not path.startswith("/api/")}


def _frontend_literal_segments() -> set[str]:
    found: set[str] = set()
    for path in SERVICES.rglob("*.ts"):
        if path.name.endswith(".test.ts"):
            continue
        found |= set(re.findall(r"[\"'`]/([a-zA-Z][a-zA-Z0-9_-]*)", path.read_text(encoding="utf-8")))
    return found


def test_every_bare_route_the_frontend_calls_is_reachable_under_api():
    requested = _frontend_literal_segments() & _bare_route_segments()

    assert requested, "the scan matched nothing -- it has stopped reading the frontend"
    assert requested - _LEGACY_API_PREFIX_SEGMENTS == set()


@pytest.mark.parametrize("path", ["/api/admin/system-logs", "/api/admin/users", "/api/model-catalog"])
def test_admin_paths_answer_under_the_api_prefix(path):
    response = TestClient(main.app).get(path, headers=ADMIN)

    assert response.status_code == 200, response.text


def test_the_active_model_poll_answers_under_the_api_prefix():
    response = TestClient(main.app).get(
        "/api/user/active-model", headers={"X-Test-User": "u1", "X-Test-User-Id": "u1", "X-Test-Role": "viewer"}
    )

    assert response.status_code != 404, response.text


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
            (await client.post("/api/admin/users/create-admin", json={})).status_code
            for _ in range(rule.max_requests + 1)
        ]

    assert 429 not in statuses[: rule.max_requests]
    assert statuses[-1] == 429
