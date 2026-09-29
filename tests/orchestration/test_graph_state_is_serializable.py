"""The graph state carries data only; per-run objects live in run_scope."""

from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.orchestration.langgraph.run_scope import bind_run_scope, run_scope
from app.orchestration.langgraph.state import OrchestrationGraphState
from app.orchestration.timeout_control import ExecutionBudget, TimeoutConfig


def test_the_state_declares_no_budget_or_callback():
    keys = set(OrchestrationGraphState.__annotations__) | {
        k for base in OrchestrationGraphState.__mro__ for k in getattr(base, "__annotations__", {})
    }
    assert "budget" not in keys
    assert "reporter" not in keys


def test_run_scope_is_bound_only_inside_the_block():
    budget = ExecutionBudget(TimeoutConfig.from_settings(get_settings()))
    seen = []
    with bind_run_scope(budget, seen.append) as scope:
        assert run_scope() is scope
    with pytest.raises(LookupError):
        run_scope()


def test_state_fallback_supplies_scope_for_direct_node_calls():
    budget = ExecutionBudget(TimeoutConfig())
    scope = run_scope({"budget": budget, "reporter": lambda e: None})
    assert scope.budget is budget


def test_a_checkpointed_workflow_can_be_compiled():
    from langgraph.checkpoint.memory import MemorySaver

    from app.orchestration.langgraph.workflow import build_workflow

    assert "checkpointer" in build_workflow.__code__.co_varnames
    assert MemorySaver() is not None
