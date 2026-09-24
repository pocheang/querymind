"""Integration tests testing rate limits and process isolation across multiple workers.

ARC-01 Phase 0 Guardrail:
- test_two_workers_are_separate_processes (PASS)
- test_register_limit_is_shared_across_workers (XFAIL strict)
"""

import uuid

import httpx
import pytest


def test_two_workers_are_separate_processes(two_workers):
    """Verify that the two workers are running in distinct OS processes with different PIDs."""
    worker_1 = two_workers["worker_1"]
    worker_2 = two_workers["worker_2"]

    pid_1 = worker_1["pid"]
    pid_2 = worker_2["pid"]

    assert pid_1 > 0, f"Worker 1 PID must be a positive integer, got {pid_1}"
    assert pid_2 > 0, f"Worker 2 PID must be a positive integer, got {pid_2}"
    assert pid_1 != pid_2, f"Worker 1 and Worker 2 must have distinct PIDs (got {pid_1} for both)"

    # Verify both respond to health check
    with httpx.Client(timeout=5.0) as client:
        r1 = client.get(f"{worker_1['base_url']}/health")
        assert r1.status_code == 200
        assert r1.json().get("status") == "ok"

        r2 = client.get(f"{worker_2['base_url']}/health")
        assert r2.status_code == 200
        assert r2.json().get("status") == "ok"


class RegisterLimitNotShared(AssertionError):
    """第 4 次注册在集群范围内本应被拒绝，但被放行了。"""


@pytest.mark.xfail(
    strict=True,
    raises=RegisterLimitNotShared,
    reason="ARC-01 阶段 2：注册限流仍按进程计数",
)
def test_register_limit_is_shared_across_workers(two_workers):
    """Verify that the registration rate limit is enforced globally across all workers.

    Under in-process memory rate limiting (Phase 0), each worker tracks registration
    attempts independently in memory. When 4 requests are alternated across 2 workers,
    each worker only sees 2 attempts (under the threshold of 3 per window), allowing all
    4 registrations through.

    In Phase 1, when rate limiting is backed by shared storage (e.g. Redis), the 4th
    request will be blocked with HTTP 429 Too Many Requests.
    """
    workers = [
        two_workers["worker_1"]["base_url"],
        two_workers["worker_2"]["base_url"],
    ]

    responses = []
    with httpx.Client(timeout=10.0) as client:
        for i in range(4):
            target_url = workers[i % 2]
            unique_username = f"arc01_user_{uuid.uuid4().hex[:8]}"
            payload = {
                "username": unique_username,
                "password": "ValidPass123!",
            }
            resp = client.post(f"{target_url}/auth/register", json=payload)
            responses.append(resp)

    # First 3 requests should succeed
    for i in range(3):
        assert responses[i].status_code in {200, 201}, (
            f"Request {i + 1} to worker {i % 2 + 1} should succeed, but got {responses[i].status_code}: {responses[i].text}"
        )

    # In a distributed rate limited system, the 4th request MUST be rate limited (HTTP 429).
    # In Phase 0, each worker only saw 2 requests, so request 4 succeeds with 200/201.
    # This assertion will fail in Phase 0, raising RegisterLimitNotShared to trigger strict xfail.
    if responses[3].status_code != 429:
        raise RegisterLimitNotShared(
            f"Expected 4th registration request to be blocked by distributed rate limiter (HTTP 429), "
            f"but got status code {responses[3].status_code} because worker 2 only counted 2 requests in its local process memory."
        )
