"""A verifier retry replays only what can change.

Two things a retry repeated for nothing, both seen in a live trace:

- Retrieval that found nothing was retried. For a user with no documents and no
  web search, round two found zero results again and paid for a second
  synthesis to say so.
- The tool stage ran again. Tool selection sees the request, the route and the
  plan -- never the evidence -- so a retry gave it the same inputs, and it
  repeated the same calls: the same lookups, and for a write tool a second
  approval token for one action.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.agents.verifier.service import VerifierAgentService
from app.domain.contracts import EvidenceItem, RouteDecision, ToolResult
from app.domain.knowledge import AccessScope, KnowledgeSourcePlan, KnowledgeStrategy
from app.domain.workflow import CandidateAnswer, ContextBundle, RouterDecision
from app.orchestration.langgraph.nodes import WorkflowNodeRuntime
from app.orchestration.policies import ExecutionPolicy
from app.orchestration.request import OrchestrationRequest
from app.orchestration.timeout_control import ExecutionBudget, TimeoutConfig
from app.services.security.access_scope import DEFAULT_CONTEXT_FIELDS


def _validator(*issues):
    async def validate(question, answer, documents, citations):
        return SimpleNamespace(
            is_valid=False,
            action="regenerate",
            issues=tuple(SimpleNamespace(type=t, content=c) for t, c in issues),
            validation_details=SimpleNamespace(factual_consistency=0.2, citation_completeness=1.0),
        )

    return validate


def _verify(context: ContextBundle, *, retry_count: int = 0):
    return asyncio.run(
        VerifierAgentService(validator=_validator(("hallucination", "not entailed"))).verify(
            OrchestrationRequest(question="log4j 2.14.1 受影响吗？"),
            context,
            CandidateAnswer(text="当前没有检索到可以支撑回答的证据。"),
            retry_count,
        )
    )


def test_retrieval_that_found_nothing_is_not_retried() -> None:
    decision = _verify(ContextBundle())

    assert decision.status != "retry_retrieval"
    assert "no authorized evidence retrieved" in decision.missing_aspects


def test_retrieval_that_found_something_unsupported_still_is() -> None:
    item = EvidenceItem(content="Log4Shell affects 2.0-2.14.1.", source="a", document_id="a", version=1)

    assert _verify(ContextBundle(evidence=(item,))).status == "retry_retrieval"


# --- the tool stage on a retry ---------------------------------------------------------------

_ROUTE = RouteDecision(
    intent="knowledge_retrieval",
    route="vector",
    confidence=0.9,
    requires_plan=False,
    allowed_capabilities=frozenset({"rag", "tool"}),
    reason="test",
    agent_class="cybersecurity",
)
_ROUTE_DECISION = RouterDecision(
    intent="knowledge_retrieval",
    complexity="simple",
    completeness="complete",
    next_stage="knowledge",
    confidence=0.9,
    reason="test",
)
_SCOPE = AccessScope(
    tenant_id="t1",
    user_id="u1",
    role="viewer",
    allowed_sources=frozenset({"a.pdf"}),
    allowed_fields=DEFAULT_CONTEXT_FIELDS,
)
_FIRST_ROUND = (ToolResult(tool_id="querymind_cyber_product_exposure", status="succeeded", summary="CVE-2021-44228"),)


def _runtime(tool_calls: list[str]) -> WorkflowNodeRuntime:
    async def knowledge_agent(*_args, **_kwargs):
        return KnowledgeStrategy(
            sources=(KnowledgeSourcePlan(source="vector", queries=("q",), top_k=4, timeout_ms=1_000),), rationale="test"
        )

    async def retriever(*_args, **_kwargs):
        return ContextBundle()

    async def tool_runner(*_args, **_kwargs):
        tool_calls.append("ran")
        return _FIRST_ROUND

    return WorkflowNodeRuntime(
        services=SimpleNamespace(
            knowledge_agent=knowledge_agent,
            retriever=retriever,
            knowledge_orchestrator=None,
            tool_runner=tool_runner,
        ),
        policy=ExecutionPolicy(),
        max_verifier_retries=1,
        context_token_budget=2_000,
    )


def _state(**extra) -> dict:
    return {
        "request": OrchestrationRequest(question="log4j 2.14.1 受影响吗？"),
        "budget": ExecutionBudget(TimeoutConfig()),
        "reporter": lambda _event: None,
        "route": _ROUTE,
        "route_decision": _ROUTE_DECISION,
        "permission_scope": _SCOPE,
        **extra,
    }


@pytest.mark.asyncio
async def test_the_first_round_runs_the_tools() -> None:
    calls: list[str] = []

    result = await _runtime(calls).knowledge(_state())

    assert calls == ["ran"]
    assert result["tool_results"] == _FIRST_ROUND


@pytest.mark.asyncio
async def test_a_retry_keeps_the_first_rounds_tool_results_instead_of_running_them_again() -> None:
    calls: list[str] = []

    result = await _runtime(calls).knowledge(_state(retry_count=1, tool_results=_FIRST_ROUND))

    assert calls == []
    assert result["tool_results"] == _FIRST_ROUND
