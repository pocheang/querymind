"""In-process SSE subscribers sleep until told, rather than polling (ARC-02)."""

from __future__ import annotations

import asyncio
import threading
import time

from app.orchestration.answer_stream import AnswerStreamStore
from app.services.runtime import execution_wake


def test_a_write_from_another_thread_wakes_a_sleeping_subscriber():
    async def scenario() -> float:
        with execution_wake.subscribe("e1") as waiter:
            waiter.clear()
            started = time.monotonic()
            threading.Timer(0.05, lambda: AnswerStreamStore().publish("e1", "hello")).start()
            woken = await waiter.wait(5.0)
            assert woken
            return time.monotonic() - started

    assert asyncio.run(scenario()) < 1.0


def test_a_change_between_the_look_and_the_wait_is_not_missed():
    async def scenario() -> bool:
        with execution_wake.subscribe("e2") as waiter:
            waiter.clear()
            execution_wake.notify("e2")  # lands after "looking", before waiting
            await asyncio.sleep(0)
            return await waiter.wait(5.0)

    assert asyncio.run(scenario()) is True


def test_an_idle_subscriber_times_out_instead_of_spinning():
    async def scenario() -> bool:
        with execution_wake.subscribe("e3") as waiter:
            waiter.clear()
            return await waiter.wait(0.05)

    assert asyncio.run(scenario()) is False


def test_other_executions_do_not_wake_it():
    async def scenario() -> bool:
        with execution_wake.subscribe("mine") as waiter:
            waiter.clear()
            execution_wake.notify("someone-else")
            return await waiter.wait(0.05)

    assert asyncio.run(scenario()) is False


def test_subscriptions_are_released():
    async def scenario() -> None:
        with execution_wake.subscribe("e4"):
            pass

    asyncio.run(scenario())
    assert "e4" not in execution_wake._waiters
