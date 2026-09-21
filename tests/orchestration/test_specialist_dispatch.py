"""The synthesizer node dispatches to the specialist the route named.

These assert DISPATCH, and deliberately not the answer's prose. They used to
check for the words a hardcoded template emitted ("安全工具与漏洞研判发现"), which
was the only path the specialist ever took because nothing supplied it a model.
Generation is delegated to the real synthesizer now, so the text is the
configured model's -- and under `MODEL_BACKEND=local`, which is what this suite
runs, that is the offline stand-in. Asserting its wording would be asserting the
stand-in, and it would go red the day a real model is configured.

So the specialists here are given a recording synthesizer: what the node
guarantees is which agent was called, with which mapped skill, and that the
specialist's own contribution -- the extracted indicators, as a tool finding --
reached the generator.
"""

import pytest

from app.agents.ai.service import AIAgentService
from app.agents.cybersecurity.service import CybersecurityAgentService
from app.domain.contracts import EvidenceItem, RouteDecision, ToolResult
from app.domain.knowledge import EvidenceRef
from app.domain.workflow import CandidateAnswer, ContextBundle
from app.orchestration.langgraph.nodes import WorkflowNodeRuntime
from app.orchestration.policies import ExecutionPolicy
from app.orchestration.request import OrchestrationRequest, RequestActor, RequestScope
from app.orchestration.timeout_control import ExecutionBudget, TimeoutConfig
from app.pipeline.profiles import PipelineProfile


class _RecordingSynthesizer:
    """Stands in for `SynthesizerAgentService` and keeps what it was handed."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.seen: dict[str, object] = {}

    async def synthesize_candidate(self, request, context, tool_results, skill):
        self.seen.update(request=request, context=context, tool_results=tool_results, skill=skill)
        return CandidateAnswer(
            text=f"{self.label} answered [E1][E2]",
            # Mirrors what `SynthesizerAgentService` returns, so assertions about
            # citations downstream stay meaningful rather than passing on a stub
            # that simply never carries any.
            citations=tuple(
                EvidenceRef(
                    document_id=item.document_id,
                    version=item.version,
                    page=item.page,
                    chunk_id=item.chunk_id,
                    image_id=item.image_id,
                )
                for item in context.evidence
            ),
        )


class _MockDispatchServices:
    def __init__(self, cyber_agent: CybersecurityAgentService, ai_agent: AIAgentService) -> None:
        self.cybersecurity_agent = cyber_agent
        self.ai_agent = ai_agent

        async def _general_candidate(request, context, tool_results, skill):
            del request, context, tool_results, skill
            return CandidateAnswer(text="General candidate fallback response")

        self.candidate_synthesizer = _general_candidate

    def report_event(self, event) -> None:
        del event


@pytest.fixture
def recorders() -> dict[str, _RecordingSynthesizer]:
    return {"cyber": _RecordingSynthesizer("cyber"), "ai": _RecordingSynthesizer("ai")}


@pytest.fixture
def runtime(recorders: dict[str, _RecordingSynthesizer]) -> WorkflowNodeRuntime:
    cyber_agent = CybersecurityAgentService(synthesizer=recorders["cyber"])
    ai_agent = AIAgentService(synthesizer=recorders["ai"])
    services = _MockDispatchServices(cyber_agent, ai_agent)
    return WorkflowNodeRuntime(
        services=services,  # type: ignore[arg-type]
        policy=ExecutionPolicy.for_profile(PipelineProfile.ADVANCED),
        max_verifier_retries=1,
        context_token_budget=4000,
    )


@pytest.mark.asyncio
async def test_dispatch_to_cybersecurity_agent(
    runtime: WorkflowNodeRuntime, recorders: dict[str, _RecordingSynthesizer]
) -> None:
    req = OrchestrationRequest(
        question="Analysis for CVE-2021-44228",
        actor=RequestActor(user_id="u1", tenant_id="t1", role="user"),
        source_scope=RequestScope(),
    )
    context = ContextBundle(
        evidence=(EvidenceItem(item_id="e1", document_id="d1", source="s1", content="Log4j vulnerability advisory"),)
    )
    state = {
        "request": req,
        "context": context,
        "route": RouteDecision(
            route="vector",
            intent="knowledge_retrieval",
            agent_class="cybersecurity",
            skill="cyber_attack_analysis",
            confidence=0.95,
            requires_plan=False,
            reason="cyber topic",
        ),
        "tool_results": (
            ToolResult(
                tool_id="querymind_cyber_cve_lookup",
                status="succeeded",
                summary="CVE-2021-44228 Log4Shell CVSS 10.0",
            ),
        ),
        "budget": ExecutionBudget(TimeoutConfig()),
        "reporter": lambda e: None,
    }

    output = await runtime.synthesizer(state)
    ans = output["candidate_answer"]
    assert ans.text == "cyber answered [E1][E2]", "the cybersecurity specialist was not the agent that ran"
    assert not recorders["ai"].seen, "the wrong specialist was consulted as well"
    seen = recorders["cyber"].seen
    # `cyber_attack_analysis` is already a pipeline skill, so it maps to itself.
    assert seen["skill"] == "cyber_attack_analysis"
    # The lookup result AND the indicators the specialist itself extracted.
    summaries = " ".join(r.summary for r in seen["tool_results"])
    assert "CVE-2021-44228 Log4Shell CVSS 10.0" in summaries
    assert "querymind_cyber_indicator_extract" in {r.tool_id for r in seen["tool_results"]}


@pytest.mark.asyncio
async def test_dispatch_to_ai_agent(runtime: WorkflowNodeRuntime, recorders: dict[str, _RecordingSynthesizer]) -> None:
    req = OrchestrationRequest(
        question="Calculate FLOPs for 7B model",
        actor=RequestActor(user_id="u1", tenant_id="t1", role="user"),
        source_scope=RequestScope(),
    )
    context = ContextBundle(
        evidence=(
            EvidenceItem(item_id="e1", document_id="d1", source="s1", content="Transformer compute scaling laws"),
        )
    )
    state = {
        "request": req,
        "context": context,
        "route": RouteDecision(
            route="vector",
            intent="knowledge_retrieval",
            agent_class="artificial_intelligence",
            skill="ai_knowledge_assistant",
            confidence=0.95,
            requires_plan=False,
            reason="ai topic",
        ),
        "tool_results": (
            ToolResult(
                tool_id="querymind_ai_math_eval",
                status="succeeded",
                summary="Evaluated '6 * 7e9 * 2e12' = 8.400000e+22",
            ),
        ),
        "budget": ExecutionBudget(TimeoutConfig()),
        "reporter": lambda e: None,
    }

    output = await runtime.synthesizer(state)
    ans = output["candidate_answer"]
    assert ans.text == "ai answered [E1][E2]", "the AI specialist was not the agent that ran"
    assert not recorders["cyber"].seen
    assert recorders["ai"].seen["skill"] in {"ai_knowledge_assistant"}


@pytest.mark.asyncio
async def test_dispatch_fallback_to_general_synthesizer(runtime: WorkflowNodeRuntime) -> None:
    req = OrchestrationRequest(
        question="Tell me a joke",
        actor=RequestActor(user_id="u1", tenant_id="t1", role="user"),
        source_scope=RequestScope(),
    )
    context = ContextBundle(evidence=())
    state = {
        "request": req,
        "context": context,
        "route": RouteDecision(
            route="vector",
            intent="general_qa",
            agent_class="general",
            skill="answer_with_citations",
            confidence=0.95,
            requires_plan=False,
            reason="general qa",
        ),
        "tool_results": (),
        "budget": ExecutionBudget(TimeoutConfig()),
        "reporter": lambda e: None,
    }

    output = await runtime.synthesizer(state)
    ans = output["candidate_answer"]
    assert ans.text == "General candidate fallback response"


@pytest.mark.asyncio
async def test_dispatch_to_dynamically_registered_custom_specialist_agent() -> None:
    from app.agents.base import BaseSpecialistAgent
    from app.agents.registry import DomainAgentRegistry

    class CustomAuditAgent(BaseSpecialistAgent):
        @property
        def agent_class(self) -> str:
            return "code_audit"

        @property
        def supported_skills(self) -> tuple[str, ...]:
            return ("ast_static_analysis",)

        async def synthesize_candidate(
            self,
            request: OrchestrationRequest,
            context: ContextBundle,
            tool_results: tuple[ToolResult, ...] = (),
            skill: str = "ast_static_analysis",
        ) -> CandidateAnswer:
            return CandidateAnswer(
                text=f"Custom Audit Report for {request.question} with {len(tool_results)} findings.",
                citations=(),
            )

    custom_registry = DomainAgentRegistry()
    custom_registry.register_agent(CustomAuditAgent())

    class _MockCustomServices:
        def __init__(self, registry: DomainAgentRegistry) -> None:
            self.domain_agent_registry = registry

            async def _fallback(request, context, tool_results, skill):
                return CandidateAnswer(text="fallback")

            self.candidate_synthesizer = _fallback

    custom_runtime = WorkflowNodeRuntime(
        services=_MockCustomServices(custom_registry),  # type: ignore[arg-type]
        policy=ExecutionPolicy.for_profile(PipelineProfile.ADVANCED),
        max_verifier_retries=1,
        context_token_budget=4000,
    )

    req = OrchestrationRequest(
        question="Audit SQL injection vulnerability in user_dao.py",
        actor=RequestActor(user_id="u1", tenant_id="t1", role="user"),
        source_scope=RequestScope(),
    )
    context = ContextBundle(evidence=())
    state = {
        "request": req,
        "context": context,
        "route": RouteDecision(
            route="vector",
            intent="knowledge_retrieval",
            agent_class="code_audit",
            skill="ast_static_analysis",
            confidence=0.98,
            requires_plan=False,
            reason="audit query",
        ),
        "tool_results": (
            ToolResult(
                tool_id="code_ast_scan",
                status="succeeded",
                summary="Detected raw query concatenation on line 42",
            ),
        ),
        "budget": ExecutionBudget(TimeoutConfig()),
        "reporter": lambda e: None,
    }

    output = await custom_runtime.synthesizer(state)
    ans = output["candidate_answer"]
    assert "Custom Audit Report for Audit SQL injection vulnerability in user_dao.py" in ans.text
    assert "1 findings" in ans.text
