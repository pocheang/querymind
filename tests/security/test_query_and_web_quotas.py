"""Query and web-search quotas are enforced, counted once for every worker, and refuse the right way.

Replaces test_quota_guard_is_not_wired.py, whose two strict xfails recorded that
`QuotaGuard` was built into every query runtime and never called. It is called
now -- at the API edge for queries, inside retrieval for each web search -- and
it counts through `make_limiter`, so with STATE_BACKEND=shared the count is one
Redis window shared by every worker instead of one per process.

Every path is under tmp_path and the runtime settings file is empty.
"""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path

import pytest

fakeredis = pytest.importorskip("fakeredis")

from app.core.config import get_settings  # noqa: E402
from app.services.runtime import shared_state  # noqa: E402
from app.services.security import quota  # noqa: E402
from app.services.security.quota import (  # noqa: E402
    QuotaExceededError,
    QuotaGuard,
    WebQuotaExceededError,
    get_quota_guard,
    reset_quota_guard,
)

REPO = Path(__file__).resolve().parents[2]
APP = REPO / "app"


@pytest.fixture
def settings(tmp_path, monkeypatch):
    empty = tmp_path / "empty.env"
    empty.write_text("", encoding="utf-8")

    def apply(**values: str) -> None:
        base = {
            "RUNTIME_ENV_FILE": str(empty),
            "NACOS_ENABLED": "false",
            "APP_DB_PATH": str(tmp_path / "app.db"),
            "API_SETTINGS_ENCRYPTION_KEY": "0123456789abcdef0123456789abcdef0123456789abcdef",
            "QUOTA_ENABLED": "true",
            "QUOTA_QUERY_MAX_PER_MINUTE": "2",
            "QUOTA_WEB_MAX_PER_MINUTE": "2",
            "STATE_BACKEND": "memory",
        }
        for key, value in {**base, **values}.items():
            monkeypatch.setenv(key, value)
        get_settings.cache_clear()
        reset_quota_guard()

    apply()
    yield apply
    get_settings.cache_clear()
    reset_quota_guard()


@pytest.fixture
def redis(monkeypatch):
    client = fakeredis.FakeRedis(server=fakeredis.FakeServer(), decode_responses=True)
    monkeypatch.setattr(shared_state._CONNECTOR, "_client", client)
    monkeypatch.setattr(shared_state._CONNECTOR, "_unavailable_until", 0.0)
    return client


# ---- it is wired -------------------------------------------------------------------


def _called_in_app(method: str, exclude: Path) -> bool:
    """Any reference to `<something>.<method>` outside quota.py: a call, or the bound
    method handed to `asyncio.to_thread`, which is how the web adapter calls it."""

    for path in APP.rglob("*.py"):
        if path == exclude:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Attribute) and node.attr == method:
                return True
    return False


@pytest.mark.parametrize("method", ["enforce_query_quota", "allow_web_search"])
def test_each_gate_has_a_call_site(method):
    """What the deleted xfails asserted, now true: nothing in app/ called either."""

    assert _called_in_app(method, exclude=APP / "services" / "security" / "quota.py")


def test_the_reload_rebuilds_the_guard(settings):
    """Limits and mode are read at construction; a reload must not keep the old ones."""

    first = get_quota_guard()
    reset_quota_guard()
    assert get_quota_guard() is not first

    source = (APP / "api" / "application" / "config_reload.py").read_text(encoding="utf-8")
    sequence = source.split("def apply_config_reload(", 1)[1].split("\ndef ", 1)[0]
    assert "reset_quota_guard()" in sequence


# ---- the query quota ------------------------------------------------------------------


def test_a_user_over_the_query_quota_is_refused_with_a_retry_after(settings):
    guard = get_quota_guard()
    guard.enforce_query_quota("alice")
    guard.enforce_query_quota("alice")

    with pytest.raises(QuotaExceededError) as refused:
        guard.enforce_query_quota("alice")

    assert 1 <= refused.value.retry_after <= 60
    guard.enforce_query_quota("bob")  # someone else's budget is untouched


def test_switched_off_it_counts_nothing(settings):
    settings(QUOTA_ENABLED="false")
    guard = get_quota_guard()

    for _ in range(10):
        guard.enforce_query_quota("alice")
        assert guard.allow_web_search("alice") is True


def test_workers_share_one_count_with_shared_state(settings, redis):
    """Two guards are two workers: neither holds the other's count in memory."""

    settings(STATE_BACKEND="shared")
    worker_a, worker_b = QuotaGuard(), QuotaGuard()
    worker_a.enforce_query_quota("alice")
    worker_b.enforce_query_quota("alice")

    with pytest.raises(QuotaExceededError):
        worker_a.enforce_query_quota("alice")
    assert worker_b.allow_web_search("alice") is True
    assert worker_a.allow_web_search("alice") is True
    assert worker_b.allow_web_search("alice") is False


def _register(settings_unit: str | None, username: str) -> str:
    from app.services.auth.auth_service import AuthDBService

    service = AuthDBService()
    user = service.register(username, "Quota-password-1!")
    if settings_unit:
        service.update_user_classification(user["user_id"], business_unit=settings_unit)
    return user["user_id"]


def test_business_unit_mode_counts_a_unit_together(settings):
    """The unit comes from the profile: the signed-in user dict does not carry it."""

    settings(QUOTA_MODE="business_unit")
    alice, bob, carol = _register("Finance", "alice_q"), _register("Finance", "bob_q"), _register(None, "carol_q")
    guard = get_quota_guard()

    guard.enforce_query_quota(alice)
    guard.enforce_query_quota(bob)
    with pytest.raises(QuotaExceededError):
        guard.enforce_query_quota(alice)
    guard.enforce_query_quota(carol)  # no unit: counted alone
    assert guard.scope_key(alice) == guard.scope_key(bob) == "bu:finance"
    assert guard.scope_key(carol) == f"user:{carol}"


# ---- the web quota --------------------------------------------------------------------


def test_every_search_call_is_one_unit(settings):
    guard = get_quota_guard()

    assert [guard.allow_web_search("alice") for _ in range(3)] == [True, True, False]


def _plan(queries: tuple[str, ...]):
    from app.domain.knowledge import KnowledgeSourcePlan

    return KnowledgeSourcePlan(source="web", queries=queries, top_k=3, timeout_ms=5000)


def _scope():
    from app.domain.knowledge import AccessScope

    return AccessScope(tenant_id="t1", user_id="alice", role="viewer")


def test_a_question_near_its_quota_searches_what_the_quota_allows(settings, monkeypatch):
    from app.agents.rag import web
    from app.knowledge import adapters

    searched: list[str] = []

    def fake_search(query, user_id, session_id):
        searched.append(query)
        return {"answer": "", "citations": [{"source": f"https://example.com/{query}", "content": query}]}

    monkeypatch.setattr(web, "run_web_research", fake_search)

    groups = asyncio.run(adapters._retrieve_web(_plan(("q1", "q2", "q3")), _scope()))

    assert searched == ["q1", "q2"]
    assert len(groups) == 3, "one list per planned query, refused ones empty"
    assert groups[2] == ()


def test_a_question_with_no_search_left_fails_the_web_source_with_the_quota_type(settings, monkeypatch):
    from app.agents.rag import web
    from app.knowledge import adapters

    monkeypatch.setattr(web, "run_web_research", lambda *a: pytest.fail("searched past the quota"))
    guard = get_quota_guard()
    guard.allow_web_search("alice")
    guard.allow_web_search("alice")

    with pytest.raises(WebQuotaExceededError) as refused:
        asyncio.run(adapters._retrieve_web(_plan(("q1",)), _scope()))

    assert refused.value.retry_after >= 1


# ---- what a caller sees -------------------------------------------------------------------


@pytest.fixture
def signed_in_user(settings, monkeypatch) -> dict[str, str]:
    """A real account, as pytest's test headers, in a store on this test's own database.

    The route's credit reservation reads `app.api.deps.auth.auth_service`, a
    process-wide proxy built on first use against whatever APP_DB_PATH was set
    then -- in a plain `pytest -q`, possibly the developer's data/app.db. So the
    proxy is handed a store built here, under the fixture's temporary path.
    """

    import uuid

    from app.api.deps.auth import auth_service
    from app.services.auth.auth_service import AuthDBService

    monkeypatch.setattr(auth_service, "_service", AuthDBService())
    user = auth_service.register(f"quota_{uuid.uuid4().hex[:8]}", "Quota-password-1!")
    return {"X-Test-User": user["username"], "X-Test-User-Id": user["user_id"], "X-Test-Role": "analyst"}


def _client():
    from fastapi.testclient import TestClient

    from app.api import main

    return TestClient(main.app)


def test_the_query_route_answers_429_with_retry_after_before_running_anything(signed_in_user, monkeypatch):
    from app.api.routes.public import query as query_module

    user = signed_in_user
    guard = get_quota_guard()
    guard.enforce_query_quota(user["X-Test-User-Id"])
    guard.enforce_query_quota(user["X-Test-User-Id"])
    monkeypatch.setattr(query_module, "_run_advanced_query", lambda *a, **k: pytest.fail("the pipeline ran"))

    response = _client().post("/api/advanced-rag/query", json={"query": "anything"}, headers=user)

    assert response.status_code == 429, response.text
    assert int(response.headers["Retry-After"]) >= 1


@pytest.mark.parametrize(
    ("error_type", "status"),
    [("WebQuotaExceededError", 429), ("ConnectTimeout", 503)],
)
def test_web_as_the_only_source_refused_by_quota_is_a_429_not_an_outage(
    signed_in_user, monkeypatch, error_type, status
):
    from app.agents.rag.service import RetrievalFailureError
    from app.api.routes.public import query as query_module

    async def fail(*_args, **_kwargs):
        raise RetrievalFailureError(1, {"web"}, 0, {"web": error_type})

    monkeypatch.setattr(query_module, "_run_advanced_query", fail)

    response = _client().post("/api/advanced-rag/query", json={"query": "latest news"}, headers=signed_in_user)

    assert response.status_code == status, response.text
    if status == 429:
        assert int(response.headers["Retry-After"]) >= 1


def test_quota_names_are_not_module_state_nobody_counts(settings):
    """The old guard kept its own SlidingWindowLimiter: per process whatever STATE_BACKEND said."""

    source = (APP / "services" / "security" / "quota.py").read_text(encoding="utf-8")
    assert "SlidingWindowLimiter(" not in source
    assert "make_limiter(" in source
    assert quota.QuotaGuard is QuotaGuard
