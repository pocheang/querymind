"""Per-run objects that must not live in the graph state.

`ExecutionBudget` is mutable and the reporter is a callback; neither can be
serialized, so keeping them in `OrchestrationGraphState` made every persistent
checkpointer unusable. The engine binds them here for the duration of one
`ainvoke`. A ContextVar is copied into the tasks and threads LangGraph starts,
and unlike an attribute on the (cached, shared) node runtime it cannot leak one
request's budget into another.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from app.domain.events import ExecutionEvent
from app.orchestration.timeout_control import ExecutionBudget


@dataclass(frozen=True)
class RunScope:
    budget: ExecutionBudget
    reporter: Callable[[ExecutionEvent], None]


_current: ContextVar[RunScope | None] = ContextVar("workflow_run_scope", default=None)


@contextmanager
def bind_run_scope(budget: ExecutionBudget, reporter: Callable[[ExecutionEvent], None]) -> Iterator[RunScope]:
    scope = RunScope(budget, reporter)
    token = _current.set(scope)
    try:
        yield scope
    finally:
        _current.reset(token)


def run_scope(state: Any = None) -> RunScope:
    """The bound scope, or `budget`/`reporter` supplied on `state`.

    The state fallback exists for code that calls a node method directly with a
    hand-built state; the engine never puts them there.
    """
    bound = _current.get()
    if bound is not None:
        return bound
    if state is not None:
        budget, reporter = state.get("budget"), state.get("reporter")
        if isinstance(budget, ExecutionBudget) and callable(reporter):
            return RunScope(budget, reporter)
    raise LookupError("no run scope is bound: budget and reporter are missing")
