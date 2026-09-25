"""Limits hold across workers (ARC-01 phase 0 guardrail, scenario 1 of phase 10).

Phase 0 wrote the registration test as a strict xfail: each worker counted in
its own memory, so four registrations alternating between two workers all got
through a limit of three. With STATE_BACKEND=shared it passes, and the marker is
gone. Login failures are scenario 1 of the phase 10 table: counted across
workers, and once over the limit refused on both.

The per-address middleware limiter is switched off in this stack
(RATE_LIMIT_ENABLED=false): every request here comes from 127.0.0.1, so it
would count all of them together and turn one test's traffic into another's
refusal. The limits under test are the route's own; the middleware has its own
contract suite (tests/contracts/test_middleware_limiter_contract.py).
"""

from __future__ import annotations

import uuid

import httpx
import pytest
from multiworker_stack import build_stack

# The first test of a module includes starting the stack (init, an ingest worker,
# two API processes), and scenario 7 waits out a 40-second lease; CI's 120s
# per-test hang detector is sized for unit tests.
pytestmark = pytest.mark.timeout(300)

MAX_FAILURES = 3
QUERY_QUOTA = 3


@pytest.fixture(scope="module")
def stack(tmp_path_factory):
    yield from build_stack(
        tmp_path_factory.mktemp("limits"),
        RATE_LIMIT_ENABLED="false",
        AUTH_REGISTER_MAX_ATTEMPTS="3",
        AUTH_LOGIN_MAX_FAILURES=str(MAX_FAILURES),
        QUOTA_ENABLED="true",
        QUOTA_QUERY_MAX_PER_MINUTE=str(QUERY_QUOTA),
    )


def test_the_workers_are_separate_processes(stack):
    a, b = stack.workers

    assert a.pid != b.pid
    for worker in (a, b):
        assert httpx.get(f"{worker.base_url}/health").json().get("status") == "ok"


def test_the_register_limit_is_shared_across_workers(stack):
    """Four registrations alternating between two workers, against a limit of three."""

    statuses = []
    for n in range(4):
        worker = stack.workers[n % 2]
        body = {"username": f"reg_{uuid.uuid4().hex[:8]}", "password": "ValidPass123!"}
        statuses.append(httpx.post(f"{worker.base_url}/auth/register", json=body).status_code)

    assert statuses == [200, 200, 200, 429]


def test_the_query_quota_is_one_count_for_every_worker(stack):
    """A quota counted per process would admit QUERY_QUOTA per worker -- the ARC-01 defect it had.

    Before the login-lockout test below, which locks this administrator on purpose.
    """

    clients = [stack.login(worker) for worker in stack.workers]

    statuses = [
        clients[n % 2].post("/api/advanced-rag/query", json={"query": f"quota probe {n}"}).status_code
        for n in range(QUERY_QUOTA + 1)
    ]

    assert statuses == [200] * QUERY_QUOTA + [429]


def test_login_failures_add_up_across_workers_and_lock_both(stack):
    """Scenario 1. The lock is the route's own answer, not a middleware refusal."""

    a, b = stack.workers
    wrong = {"username": "stackadmin", "password": "not-the-password"}

    failures = [httpx.post(f"{stack.workers[n % 2].base_url}/auth/login", json=wrong).status_code for n in range(3)]
    assert failures == [401, 401, 401]

    for worker in (a, b):
        locked = httpx.post(f"{worker.base_url}/auth/login", json=wrong)
        assert locked.status_code == 429, worker.name
        detail = locked.json()["detail"]
        assert (detail["error"], detail["attempts_used"], detail["max_attempts"]) == (
            "rate_limited",
            MAX_FAILURES,
            MAX_FAILURES,
        )
        assert int(locked.headers["Retry-After"]) > 0
