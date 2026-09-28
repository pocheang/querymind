"""A worker killed while holding a query slot gives it back when the lease runs out (ARC-01 phase 10, scenario 7).

The query guard's slots are leases in a Redis sorted set, scored by expiry. The
counters they replaced leaked: a worker that died holding a slot never gave it
back, and the cluster ran one slot short from then on. Here the gate is one slot
wide; worker A takes it and is killed without running any handler; worker B is
refused while the lease is live and admitted once it has expired -- not before,
and not much after.

To have something to kill, A's query must still be running. Web search is sent
through a proxy that accepts a connection and never answers, so the slot is held
until the web source's timeout. The lease is the stage budget plus 30 seconds
(app/api/dependencies.py), so a small budget keeps the wait short.

It used to be graph retrieval pointed at the silent socket, and that could never
have held the slot: the caller here has no documents, and the orchestrator skips
every document-backed source -- graph included -- for an empty scope before any
connection is made. What held the slot was A's cold start, which is why warming
A up made the question answer at once, and why the test failed whenever a runner
started A quickly: the lease lived for less than one 50 ms poll (CI, 2026-09-26
and three times on 2026-09-27). Web search is the one source that runs on an
empty scope, and a silent proxy makes its duration the configured timeout.
"""

from __future__ import annotations

import socket
import threading
import time

import httpx
import pytest
from multiworker_stack import build_stack

# The first test of a module includes starting the stack (init, an ingest worker,
# two API processes), and scenario 7 waits out a 40-second lease; CI's 120s
# per-test hang detector is sized for unit tests.
pytestmark = pytest.mark.timeout(300)

TOTAL_BUDGET_MS = 10_000
# Every stage ceiling has to fit inside the total (Settings refuses otherwise), so
# the whole budget is scaled down together. Retrieval keeps the largest share:
# that is the stage the slow question spends its time in.
_STAGES = {
    "STAGE_TIMEOUT_ROUTE_MS": "1000",
    "STAGE_TIMEOUT_PLAN_MS": "500",
    "STAGE_TIMEOUT_RETRIEVAL_MS": "4000",
    "STAGE_TIMEOUT_TOOL_MS": "1000",
    "STAGE_TIMEOUT_SYNTHESIS_MS": "2000",
    "STAGE_TIMEOUT_FINALIZATION_MS": "1000",
    "STAGE_TIMEOUT_OVERHEAD_MS": "500",
    "KNOWLEDGE_SOURCE_TIMEOUT_MS": "3500",
}
LEASE_SECONDS = (TOTAL_BUDGET_MS + 30_000) / 1000
SLOW_QUESTION = "服务之间的依赖关系是什么"


class _Silent:
    """A TCP listener that accepts and never replies, so a client waits on it until its own timeout."""

    def __init__(self) -> None:
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.bind(("127.0.0.1", 0))
        self._server.listen(16)
        self.port = self._server.getsockname()[1]
        self._held: list[socket.socket] = []
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self) -> None:
        while True:
            try:
                connection, _ = self._server.accept()
            except OSError:
                return
            self._held.append(connection)

    def close(self) -> None:
        for connection in self._held:
            connection.close()
        self._server.close()


@pytest.fixture(scope="module")
def silent_graph():
    listener = _Silent()
    yield listener
    listener.close()


@pytest.fixture(scope="module")
def stack(tmp_path_factory, silent_graph):
    yield from build_stack(
        tmp_path_factory.mktemp("crash"),
        RATE_LIMIT_ENABLED="false",
        QUERY_MAX_CONCURRENT="1",
        QUERY_MAX_WAITING="0",
        # B is polled through the whole lease; the per-user window must not be what refuses it.
        QUERY_RATE_LIMIT_MAX_ATTEMPTS="500",
        STAGE_TIMEOUT_TOTAL_MS=str(TOTAL_BUDGET_MS),
        **_STAGES,
        NEO4J_URI=f"bolt://127.0.0.1:{silent_graph.port}",
        # The slot holder: web search through a proxy that never answers. Never
        # leaves the machine -- the proxy is the silent socket.
        WEB_SEARCH_ON_EMPTY_CORPUS="true",
        WEB_PROXY_URL=f"http://127.0.0.1:{silent_graph.port}",
        WEB_SEARCH_TIMEOUT_SECONDS="3",
        WEB_SEARCH_MAX_RETRIES="0",
        WEB_FETCH_PAGES_ENABLED="false",
    )


def _leases(stack) -> list[tuple[str, float]]:
    return stack.redis().zrange(stack.key("qguard", "inflight"), 0, -1, withscores=True)


def test_a_slot_held_by_a_killed_worker_is_reclaimed_when_its_lease_expires(stack):
    a, b = stack.workers
    on_a, on_b = stack.login(a), stack.login(b)
    warm = on_b.post("/api/advanced-rag/query", json={"query": "warm up"})
    assert _ran(warm), warm.text
    # A is deliberately NOT warmed up: its first graph lookup is the one that
    # hangs on the silent socket. Warming it was tried (2026-09-26) and the slow
    # question then answered 200 at once without holding the slot.

    # What A answered, so a failure below says whether its query finished fast or
    # never started. This failed once in CI (2026-09-26) with no way to tell.
    outcome: dict[str, object] = {}

    def slow_query() -> None:
        started = time.monotonic()
        try:
            outcome["status"] = on_a.post("/api/advanced-rag/query", json={"query": SLOW_QUESTION}).status_code
        except httpx.HTTPError as exc:  # the worker serving it is killed mid-request
            outcome["error"] = type(exc).__name__
        outcome["seconds"] = round(time.monotonic() - started, 2)

    threading.Thread(target=slow_query, daemon=True).start()
    # Generous on purpose: A's first query also pays A's cold start, and a shared
    # CI runner can take longer than 10 s for that. Nothing below is timed from
    # here -- the lease's own expiry is read from Redis.
    deadline = time.monotonic() + 30
    while not _leases(stack) and time.monotonic() < deadline:
        time.sleep(0.05)
    leases = _leases(stack)
    assert len(leases) == 1, f"A's query never took the slot; A answered: {outcome or 'nothing yet'}"
    expires_at = leases[0][1] / 1000  # milliseconds, Redis's clock

    stack.kill(a)
    assert not a.alive()

    refused = on_b.post("/api/advanced-rag/query", json={"query": "anything"})
    assert refused.status_code == 503 and not _ran(refused), refused.text
    assert _leases(stack) == leases, "the dead worker's lease is still there"

    admitted_at = _first_admission(stack, on_b, timeout=LEASE_SECONDS + 20)
    assert admitted_at is not None, f"B never admitted a query after {LEASE_SECONDS + 20}s"
    assert admitted_at >= expires_at - 1.0, "admitted before the dead worker's lease expired"
    assert admitted_at <= expires_at + 5.0, "the slot came back long after its lease expired"


def _first_admission(stack, client: httpx.Client, *, timeout: float) -> float | None:
    """Redis's clock when the first admitted request was SENT.

    Taken at the start of the request, not after it: an admitted query runs to
    completion -- here, through the silent web proxy -- and timing its end would
    charge the query's own duration to the lease.
    """

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        sent_at = _redis_time(stack)
        response = client.post("/api/advanced-rag/query", json={"query": "anything"})
        if _ran(response):
            return sent_at
        assert response.status_code == 503, response.text
        time.sleep(0.5)
    return None


# What a query that was admitted and ran answers when its only source -- the web,
# through the silent proxy -- fails: 503 with this detail (app/api/routes/public/
# query.py). The query guard's refusal is also a 503, so the two are told apart
# by the body, not the status.
_RETRIEVAL_FAILED = "No evidence could be retrieved"


def _ran(response: httpx.Response) -> bool:
    """Admitted and executed: answered, or ran and found no source that worked."""

    return response.status_code == 200 or (response.status_code == 503 and _RETRIEVAL_FAILED in response.text)


def _redis_time(stack) -> float:
    seconds, microseconds = stack.redis().time()
    return seconds + microseconds / 1_000_000
