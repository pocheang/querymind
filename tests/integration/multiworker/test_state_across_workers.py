"""What one worker writes, the other reads (ARC-01 phase 10, scenarios 2, 3, 4 and 6).

Each scenario is written so that the second worker holds nothing of the first
one's in its own memory: an approval, a run's event stream, a conversation and
a log level all have to cross the process boundary through Redis or SQLite, or
the assertion fails.

One deviation from the plan's table, and why. Scenario 2 says worker A *issues*
the approval token. Tokens are issued by the tool stage when the model's tool
selector picks a write tool, and with MODEL_BACKEND=local -- the only backend a
test can run -- there is no model to pick one. So the token is minted by a
helper process running the real tool stack against the same database and Redis,
exactly as a worker's tool stage would; approving (B) and redeeming (A, then B
again) go through HTTP. Redeeming does work offline: a question naming a
connector command routes to the tool stage by rule, and a resume replays the
approved call without asking a model anything.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from multiworker_stack import Stack, build_stack

# The first test of a module includes starting the stack (init, an ingest worker,
# two API processes), and scenario 7 waits out a 40-second lease; CI's 120s
# per-test hang detector is sized for unit tests.
pytestmark = pytest.mark.timeout(300)

CONNECTOR = "falcon_runbook"


@pytest.fixture(scope="module")
def stack(tmp_path_factory):
    yield from build_stack(
        tmp_path_factory.mktemp("state"),
        RATE_LIMIT_ENABLED="false",
        # Scenario 4 sends fifty questions as one user.
        QUERY_RATE_LIMIT_MAX_ATTEMPTS="500",
    )


@pytest.fixture(scope="module")
def admin(stack: Stack):
    """One signed-in client per worker for the same administrator."""

    a, b = stack.workers
    return stack.login(a), stack.login(b)


@pytest.fixture(scope="module")
def admin_id(admin) -> str:
    return admin[0].get("/auth/me").json()["user_id"]


# ---- scenario 2: an approval issued in one process, approved and redeemed in the others ---

_MINT = """
import asyncio, sys
from app.mcp.contracts import ToolArgument, ToolCall
from app.mcp.runtime import DISABLE_CONNECTOR_TOOL_ID, get_tool_stack
from app.orchestration.request import RequestActor

actor = RequestActor(user_id=sys.argv[1], role="admin")
call = ToolCall(tool_id=DISABLE_CONNECTOR_TOOL_ID, arguments=(ToolArgument(name="connector_id", value=sys.argv[2]),))
stack = get_tool_stack()
result = asyncio.run(stack.gateway.invoke(call, actor))
stack.registry.flush_audit()
print(result.status, result.approval_token)
"""


def _mint_approval(stack: Stack, user_id: str) -> str:
    done = subprocess.run(
        [sys.executable, "-c", _MINT, user_id, CONNECTOR],
        env=stack.env,
        cwd=stack.root,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert done.returncode == 0, done.stderr[-2000:]
    status, token = done.stdout.strip().splitlines()[-1].split()
    assert status == "approval_required"
    return token


def _connector_enabled(client: httpx.Client) -> bool:
    connectors = client.get("/api/v1/connectors").json()["connectors"]
    return next(c for c in connectors if c["connector_id"] == CONNECTOR)["status"] == "enabled"


def _resume(client: httpx.Client, token: str) -> httpx.Response:
    return client.post(
        "/api/advanced-rag/query", json={"query": f"disable connector {CONNECTOR}", "approval_token": token}
    )


def test_an_approval_crosses_workers_and_is_redeemed_exactly_once(stack, admin, admin_id):
    """Scenario 2: issued elsewhere, approved on B, redeemed on A; a second redemption on B does nothing."""

    on_a, on_b = admin
    created = on_a.post(
        "/api/v1/connectors",
        json={
            "connector_id": CONNECTOR,
            "name": "Falcon runbook",
            "base_url": "https://runbook.example.com",
            "allowed_hosts": ["runbook.example.com"],
            "secret": "stack-test-secret-value",
        },
    )
    assert created.status_code == 201, created.text
    token = _mint_approval(stack, admin_id)

    assert on_b.post(f"/api/v1/connectors/approvals/{token}", json={"confirmed": True}).status_code == 200
    assert _resume(on_a, token).status_code == 200
    assert _connector_enabled(on_b) is False, "the approved call ran"

    assert on_a.post(f"/api/v1/connectors/{CONNECTOR}/enable").status_code == 200
    assert _resume(on_b, token).status_code == 200
    assert _connector_enabled(on_a) is True, "a spent token ran the call a second time"


# ---- scenario 3: the run on A, the subscription on B -------------------------------------


def _sse_messages(response: httpx.Response) -> list[tuple[str, str]]:
    messages, event = [], None
    for line in response.iter_lines():
        if line.startswith("event:"):
            event = line.split(":", 1)[1].strip()
        elif line.startswith("data:") and event:
            messages.append((event, line.split(":", 1)[1].strip()))
            event = None
    return messages


def test_a_subscriber_on_b_receives_a_run_on_a_complete_and_in_order(stack, admin):
    """Scenario 3. B's stream must equal what A wrote to Redis, entry for entry."""

    on_a, on_b = admin
    execution_id = str(uuid.uuid4())
    received: dict = {}

    def subscribe():
        with on_b.stream("GET", f"/api/v1/orchestration/executions/{execution_id}/events", timeout=120) as r:
            received["status"] = r.status_code
            received["messages"] = _sse_messages(r)

    subscriber = threading.Thread(target=subscribe)
    subscriber.start()
    time.sleep(0.3)
    answer = on_a.post(
        "/api/advanced-rag/query",
        json={"query": "What is the retention window for backups?", "execution_id": execution_id},
    )
    subscriber.join(90)

    assert answer.status_code == 200, answer.text
    assert received["status"] == 200
    written = stack.redis().xrange(stack.key("exec", execution_id, "s"))
    kinds = {"event": "execution_event", "terminal": "execution_event", "answer": "answer_fragment"}
    expected = [kinds.get(fields["kind"], "thought_fragment") for _id, fields in written]
    assert [name for name, _ in received["messages"]] == expected
    assert len(expected) > 3
    stages = [json.loads(data)["stage"] for name, data in received["messages"] if name == "execution_event"]
    assert stages[-1] == "complete"
    assert json.loads(received["messages"][-1][1])["status"] == "completed"


# ---- scenario 4: one conversation, written from both workers at once ----------------------


def test_concurrent_writes_to_one_conversation_from_both_workers_lose_nothing(stack, admin):
    """Scenario 4: fifty questions, alternating workers, all in flight together -- 100 appends."""

    session_id = uuid.uuid4().hex
    questions = [f"question number {n} about backups" for n in range(50)]

    def ask(n: int) -> int:
        client = admin[n % 2]
        return client.post(
            "/api/advanced-rag/query", json={"query": questions[n], "session_id": session_id}
        ).status_code

    with ThreadPoolExecutor(max_workers=16) as pool:
        statuses = list(pool.map(ask, range(50)))

    assert statuses == [200] * 50
    messages = admin[1].get(f"/sessions/{session_id}").json()["messages"]
    assert len(messages) == 100
    assert sorted(m["content"] for m in messages if m["role"] == "user") == sorted(questions)
    assert sum(1 for m in messages if m["role"] == "assistant") == 50


# ---- scenario 6: a configuration change made on A takes effect on B ----------------------

PROPAGATION_SECONDS = 5.0


def test_a_log_level_set_on_a_takes_effect_on_b(stack, admin):
    """Scenario 6. Propagates through the phase 6 generation counters, checked at the start of each request."""

    on_a, on_b = admin
    logger_name = f"qm.phase10.{uuid.uuid4().hex[:6]}"
    set_on_a = on_a.post("/admin/ops/logging/level", json={"logger": logger_name, "level": "DEBUG"})
    assert set_on_a.status_code == 200, set_on_a.text
    assert set_on_a.json()["applies_to"] == "all_workers"

    deadline = time.monotonic() + PROPAGATION_SECONDS
    seen = None
    while time.monotonic() < deadline:
        seen = on_b.get("/admin/ops/logging/levels").json()["loggers"].get(logger_name)
        if seen == "DEBUG":
            break
        time.sleep(0.2)

    assert seen == "DEBUG", f"B still reports {seen!r} after {PROPAGATION_SECONDS}s"
    on_a.post("/admin/ops/logging/reset")
