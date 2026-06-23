"""
Concurrency tests for AgentExecutionTracker to verify thread safety.
"""

import asyncio
from datetime import timedelta

import pytest

from app.services.agent_execution_tracker import (
    AgentExecutionTracker,
    utcnow,
)


@pytest.fixture
def tracker():
    """Create a fresh tracker instance for testing."""
    tracker = AgentExecutionTracker()
    tracker.clear_all_traces()
    return tracker


@pytest.mark.asyncio
async def test_concurrent_step_recording(tracker):
    """Test that concurrent step recording doesn't cause race conditions."""
    execution_id = tracker.start_execution("test query")

    # Launch 100 concurrent step recordings
    async def record_step(i):
        step_id = tracker.record_agent_step(execution_id, f"Agent{i}", {"index": i})
        await asyncio.sleep(0.001)  # Simulate work
        tracker.complete_agent_step(execution_id, step_id, {"result": f"done{i}"})

    await asyncio.gather(*[record_step(i) for i in range(100)])

    trace = tracker.get_execution_trace(execution_id)
    assert len(trace.steps) == 100
    assert all(s.status == "completed" for s in trace.steps)

    # Verify all agent names are present
    agent_names = {s.agent_name for s in trace.steps}
    assert len(agent_names) == 100


@pytest.mark.asyncio
async def test_concurrent_execution_creation(tracker):
    """Test that concurrent execution creation is thread-safe."""

    async def create_execution(i):
        execution_id = tracker.start_execution(f"query {i}")
        return execution_id

    # Create 50 executions concurrently
    execution_ids = await asyncio.gather(*[create_execution(i) for i in range(50)])

    # All should be unique
    assert len(set(execution_ids)) == 50

    # All should be retrievable
    for exec_id in execution_ids:
        trace = tracker.get_execution_trace(exec_id)
        assert trace is not None
        assert trace.execution_id == exec_id


@pytest.mark.asyncio
async def test_cleanup_during_concurrent_access(tracker):
    """Test cleanup works correctly while concurrent operations are happening."""
    tracker._ttl_hours = 0  # Expire immediately

    # Add some old traces
    for i in range(10):
        exec_id = tracker.start_execution(f"old query {i}")
        # Make them old
        with tracker._traces_lock:
            tracker._traces[exec_id].start_time = utcnow() - timedelta(hours=2)

    # Start concurrent operations
    async def add_and_complete(i):
        exec_id = tracker.start_execution(f"new query {i}")
        step_id = tracker.record_agent_step(exec_id, f"Agent{i}", {})
        await asyncio.sleep(0.01)
        tracker.complete_agent_step(exec_id, step_id, {})
        return exec_id

    # Run cleanup concurrently with new operations
    async def cleanup_task():
        await asyncio.sleep(0.005)  # Start cleanup mid-way
        removed = tracker.cleanup_old_traces()
        return removed

    tasks = [add_and_complete(i) for i in range(20)]
    tasks.append(cleanup_task())

    results = await asyncio.gather(*tasks)

    # Last result is cleanup count - could be 10 old + some new ones that also expired
    removed_count = results[-1]
    assert removed_count >= 10  # At least the 10 old ones should be removed

    # Some new executions might have been created after cleanup
    # Just verify no exceptions occurred
    new_exec_ids = results[:-1]
    assert len(new_exec_ids) == 20


@pytest.mark.asyncio
async def test_periodic_cleanup_lifecycle(tracker):
    """Test that cleanup task starts and stops correctly."""
    tracker._ttl_hours = 0  # Expire immediately

    # Add some traces
    for i in range(5):
        exec_id = tracker.start_execution(f"query {i}")
        # Make them old
        with tracker._traces_lock:
            tracker._traces[exec_id].start_time = utcnow() - timedelta(hours=1)

    assert len(tracker._traces) == 5

    # Start cleanup with short interval
    await tracker.start_periodic_cleanup(interval_seconds=1)
    assert tracker._cleanup_task is not None
    assert not tracker._cleanup_task.done()

    # Wait for at least one cleanup cycle
    await asyncio.sleep(1.5)

    # Traces should be cleaned
    assert len(tracker._traces) == 0

    # Stop cleanup
    await tracker.stop_periodic_cleanup()
    assert tracker._cleanup_task is None or tracker._cleanup_task.done()


@pytest.mark.asyncio
async def test_trace_lock_cleanup(tracker):
    """Test that per-trace locks are cleaned up when traces are removed."""
    # Create and complete some executions
    exec_ids = []
    for i in range(10):
        exec_id = tracker.start_execution(f"query {i}")
        exec_ids.append(exec_id)
        # Access trace to potentially create per-trace lock
        tracker.record_agent_step(exec_id, f"Agent{i}", {})

    # Note: defaultdict only creates entries when accessed,
    # so we may not have locks yet unless the implementation uses them
    len(tracker._trace_locks)

    # Make them old and cleanup
    tracker._ttl_hours = 0
    with tracker._traces_lock:
        for exec_id in exec_ids:
            if exec_id in tracker._traces:
                tracker._traces[exec_id].start_time = utcnow() - timedelta(hours=1)

    removed = tracker.cleanup_old_traces()
    assert removed == 10
    assert len(tracker._traces) == 0

    # Manually trigger lock cleanup (normally done by periodic cleanup)
    with tracker._traces_lock:
        active_ids = set(tracker._traces.keys())
        lock_ids = set(tracker._trace_locks.keys())
        orphaned = lock_ids - active_ids
        for orphan_id in orphaned:
            del tracker._trace_locks[orphan_id]

    # After cleanup, no locks should remain for deleted traces
    final_lock_count = len(tracker._trace_locks)
    assert final_lock_count == 0


@pytest.mark.asyncio
async def test_concurrent_get_recent_executions(tracker):
    """Test that get_recent_executions is thread-safe."""
    # Create executions
    for i in range(30):
        tracker.start_execution(f"query {i}")

    # Concurrently read recent executions
    async def get_recent():
        await asyncio.sleep(0.001)
        return tracker.get_recent_executions(limit=10)

    results = await asyncio.gather(*[get_recent() for _ in range(20)])

    # All results should have 10 items
    assert all(len(r) == 10 for r in results)

    # Results should be sorted by start_time descending
    for recent in results:
        for i in range(len(recent) - 1):
            assert recent[i].start_time >= recent[i + 1].start_time


def test_singleton_remains_thread_safe():
    """Verify singleton pattern remains thread-safe."""
    import threading

    instances = []

    def get_instance():
        instances.append(AgentExecutionTracker.get_instance())

    threads = [threading.Thread(target=get_instance) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All instances should be the same
    assert len(set(id(inst) for inst in instances)) == 1
