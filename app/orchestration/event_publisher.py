"""Execution-event publisher abstractions with a deterministic test implementation."""

from __future__ import annotations

from typing import Protocol

from app.domain.events import ExecutionEvent
from app.orchestration.execution_events import ExecutionEventStore, current_execution_id


class EventPublisher(Protocol):
    """Publish a safe execution event without coupling the engine to SSE.

    Synchronous on purpose. Every implementation hands the event to an
    in-process structure and returns, so the coroutine boundary this used to
    declare was never a suspension point -- it only made every caller on the
    reporting path ``await`` something that could not wait (python:S7503). A
    sink that genuinely needs I/O should enqueue here and drain elsewhere,
    rather than make each pipeline stage wait on it.
    """

    def publish(self, event: ExecutionEvent) -> None:
        """Deliver one event to the configured trace sink."""


class NullEventPublisher:
    """Default publisher used before API/SSE delivery is introduced."""

    def publish(self, event: ExecutionEvent) -> None:
        """Intentionally drop the event."""
        del event


class InMemoryEventPublisher:
    """Append events in order for unit tests and in-process callers."""

    def __init__(self) -> None:
        self.events: list[ExecutionEvent] = []

    def publish(self, event: ExecutionEvent) -> None:
        self.events.append(event)


class ExecutionStoreEventPublisher:
    """Route engine events into the store the SSE endpoint reads.

    Deliberately stateless apart from the store itself: one engine instance is
    cached per profile and shared by concurrent requests, so the execution id
    must come from the per-task ``current_execution_id`` ContextVar the engine
    binds, never from an attribute set at construction or per request.

    Events produced without a bound execution id (a direct pipeline call that
    set none) have nowhere to go and are dropped, which is the previous
    NullEventPublisher behaviour.
    """

    def __init__(self, store: ExecutionEventStore) -> None:
        self._store = store

    def publish(self, event: ExecutionEvent) -> None:
        execution_id = current_execution_id.get()
        if not execution_id:
            return
        self._store.publish(execution_id, event)
