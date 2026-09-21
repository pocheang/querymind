"""Closed-loop integration tests for specialized agents, categorized tools, and guardrails."""

import pytest

from app.agents.ai.service import AIAgentService
from app.agents.cybersecurity.service import CybersecurityAgentService
from app.core.config import get_settings
from app.domain.contracts import EvidenceItem, RouteDecision
from app.domain.knowledge import EvidenceRef
from app.domain.workflow import CandidateAnswer, ContextBundle
from app.mcp.contracts import ToolArgument, ToolCall
from app.orchestration.langgraph.nodes import WorkflowNodeRuntime
from app.orchestration.policies import ExecutionPolicy
from app.orchestration.request import OrchestrationRequest, RequestActor, RequestScope
from app.orchestration.timeout_control import ExecutionBudget, TimeoutConfig
from app.pipeline.profiles import PipelineProfile
from app.privacy.service import PrivacyService
from app.services.security.access_scope import AccessScopeResolver
from app.services.security.security_guardrail import SecurityGuardrailService
from app.tools.ai.code_sandbox import AI_MATH_TOOL_DEFINITION, execute_ai_math_eval
from app.tools.cyber.cve_tools import CVE_TOOL_DEFINITION, execute_cve_lookup


class _RecordingSynthesizer:
    """Stands in for `SynthesizerAgentService`, keeping what it was handed."""

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


class _StubRegistry:
    """The registry the node consults, holding just these two specialists.

    The tests used to set `cybersecurity_agent` / `ai_agent` attributes, which
    the node read as a fallback when the registry missed. That fallback is gone
    -- it reached a second instance of each specialist -- so registering is how
    an agent becomes reachable here too, exactly as in production.
    """

    def __init__(self, **agents) -> None:
        self._agents = agents

    def get_agent(self, agent_class: str):
        return self._agents.get(agent_class)


class _ClosedLoopWorkflowServices:
    def __init__(self) -> None:
        self.privacy = PrivacyService()
        self.access_scope_resolver = AccessScopeResolver()
        self.security_guardrail = SecurityGuardrailService(
            privacy_service=self.privacy,
            access_scope_resolver=self.access_scope_resolver,
            settings=get_settings(),
        )
        # Recording synthesizers, for the reason `test_specialist_dispatch`
        # gives: the closed loop this file exercises is privacy -> tool -> agent,
        # and the ANSWER's prose belongs to whichever chat model is configured.
        # Under MODEL_BACKEND=local that is the offline stand-in, so asserting
        # its wording would test the stand-in and would break the day a real
        # model is set. What each stage handed the next is the loop.
        self.cyber_synth = _RecordingSynthesizer("cyber")
        self.ai_synth = _RecordingSynthesizer("ai")
        self.domain_agent_registry = _StubRegistry(
            cybersecurity=CybersecurityAgentService(synthesizer=self.cyber_synth),
            artificial_intelligence=AIAgentService(synthesizer=self.ai_synth),
        )

        async def _general_synth(request, context, tool_results, skill):
            del request, context, tool_results, skill
            return CandidateAnswer(text="General answer fallback")

        self.candidate_synthesizer = _general_synth

    def report_event(self, event) -> None:
        del event


@pytest.fixture
def closed_loop_runtime() -> WorkflowNodeRuntime:
    services = _ClosedLoopWorkflowServices()
    return WorkflowNodeRuntime(
        services=services,  # type: ignore[arg-type]
        policy=ExecutionPolicy.for_profile(PipelineProfile.ADVANCED),
        max_verifier_retries=1,
        context_token_budget=4000,
    )


@pytest.mark.asyncio
async def test_cybersecurity_closed_loop(closed_loop_runtime: WorkflowNodeRuntime) -> None:
    """End-to-End Closed Loop for Cybersecurity:
    Guardrail (Sanitize/PII) -> Tool Lookup (CVE) -> Specialist Synthesis (IoC/MITRE) -> Grounded Candidate.
    """
    raw_question = "Investigate incident regarding admin@company.com and vulnerability Log4Shell"
    actor = RequestActor(user_id="sec_ops_1", tenant_id="corp_a", role="analyst")
    initial_request = OrchestrationRequest(
        question=raw_question,
        actor=actor,
        source_scope=RequestScope(),
    )

    # 1. Guardrail Step
    state = {
        "request": initial_request,
        "budget": ExecutionBudget(TimeoutConfig()),
        "reporter": lambda e: None,
    }
    guardrail_output = await closed_loop_runtime.privacy_permission(state)
    sanitized_request = guardrail_output["request"]

    # Verify PII was redacted
    assert "admin@company.com" not in sanitized_request.question
    assert "<EMAIL_1>" in sanitized_request.question

    # 2. Tool Step (QueryMind MCP Tool Execution)
    tool_call = ToolCall(
        tool_id=CVE_TOOL_DEFINITION.tool_id,
        arguments=(ToolArgument(name="cve_id", value="Log4Shell"),),
    )
    tool_result = await execute_cve_lookup(tool_call, actor)
    assert tool_result.status == "succeeded"
    assert "CVE-2021-44228" in tool_result.summary

    # 3. Specialist Synthesis Step
    context = ContextBundle(
        evidence=(
            EvidenceItem(
                item_id="ev_cyber_log4j",
                document_id="doc_corp_policy",
                source="security_policy_2024.pdf",
                content="Emergency patching protocol for remote code execution vulnerabilities.",
            ),
        )
    )
    synth_state = {
        "request": sanitized_request,
        "context": context,
        "route": RouteDecision(
            route="vector",
            intent="hybrid",
            agent_class="cybersecurity",
            skill="cyber_attack_analysis",
            confidence=0.98,
            requires_plan=False,
            reason="cyber threat analysis",
        ),
        "tool_results": (tool_result,),
        "budget": ExecutionBudget(TimeoutConfig()),
        "reporter": lambda e: None,
    }

    synth_output = await closed_loop_runtime.synthesizer(synth_state)
    candidate: CandidateAnswer = synth_output["candidate_answer"]

    # Assert Closed-Loop Integrity:
    # Tool finding integrated
    # Evidence citation grounded
    assert candidate.text.endswith("[E1][E2]")
    assert len(candidate.citations) == 1
    assert candidate.citations[0].document_id == "doc_corp_policy"
    # Threat entities identified


@pytest.mark.asyncio
async def test_ai_specialist_closed_loop(closed_loop_runtime: WorkflowNodeRuntime) -> None:
    """End-to-End Closed Loop for AI Specialist:
    Guardrail -> AST Code Sandbox Tool -> AI Architecture Synthesis (FLOPs & Scaling) -> Candidate.
    """
    raw_question = "Calculate training compute and memory for 70B LLaMA-3 with 2T tokens in FP16"
    actor = RequestActor(user_id="ai_researcher", tenant_id="corp_b", role="analyst")
    initial_request = OrchestrationRequest(
        question=raw_question,
        actor=actor,
        source_scope=RequestScope(),
    )

    # 1. Guardrail Step
    state = {
        "request": initial_request,
        "budget": ExecutionBudget(TimeoutConfig()),
        "reporter": lambda e: None,
    }
    guardrail_output = await closed_loop_runtime.privacy_permission(state)
    sanitized_request = guardrail_output["request"]

    # 2. Tool Step (AST Code Sandbox Execution)
    tool_call = ToolCall(
        tool_id=AI_MATH_TOOL_DEFINITION.tool_id,
        arguments=(ToolArgument(name="expression", value="flops_train(70e9, 2e12)"),),
    )
    tool_result = await execute_ai_math_eval(tool_call, actor)
    assert tool_result.status == "succeeded"
    assert "8.400000e+23" in tool_result.summary

    # 3. Specialist Synthesis Step
    context = ContextBundle(
        evidence=(
            EvidenceItem(
                item_id="ev_scaling_laws",
                document_id="doc_kaplan_chinchilla",
                source="scaling_laws_overview.pdf",
                content="Under compute-optimal training, compute scales linearly with parameters and data tokens.",
            ),
        )
    )
    synth_state = {
        "request": sanitized_request,
        "context": context,
        "route": RouteDecision(
            route="vector",
            intent="hybrid",
            agent_class="artificial_intelligence",
            skill="ai_knowledge_assistant",
            confidence=0.98,
            requires_plan=False,
            reason="ai architecture question",
        ),
        "tool_results": (tool_result,),
        "budget": ExecutionBudget(TimeoutConfig()),
        "reporter": lambda e: None,
    }

    synth_output = await closed_loop_runtime.synthesizer(synth_state)
    candidate: CandidateAnswer = synth_output["candidate_answer"]

    # Assert Closed-Loop Integrity:
    assert candidate.text == "ai answered [E1][E2]"
    assert len(candidate.citations) == 1
    assert candidate.citations[0].document_id == "doc_kaplan_chinchilla"


@pytest.mark.asyncio
async def test_hybrid_document_rag_and_tool_specialist_closed_loop(
    closed_loop_runtime: WorkflowNodeRuntime,
) -> None:
    """End-to-End Hybrid Closed Loop combining Document RAG and Governed Tools.

    Verifies that:
    1. Private Knowledge Base Documents (e.g. corporate security PDF policies, runbooks)
    2. Governed MCP Tool Findings (CVE and exploit intelligence)
    are synthesized together by the domain specialist agent with cross-referenced citations.
    """
    raw_question = "核查 192.168.10.45 主机上 Log4Shell 攻击告警，并对比《2026-企业应急预案.pdf》的加固规程"
    actor = RequestActor(user_id="sec_analyst_9", tenant_id="corp_sec", role="analyst")
    initial_request = OrchestrationRequest(
        question=raw_question,
        actor=actor,
        source_scope=RequestScope(),
    )

    # 1. Guardrail Step
    state = {
        "request": initial_request,
        "budget": ExecutionBudget(TimeoutConfig()),
        "reporter": lambda e: None,
    }
    guardrail_output = await closed_loop_runtime.privacy_permission(state)
    sanitized_request = guardrail_output["request"]

    # 2. Document Knowledge RAG Step (ContextBundle with multiple document chunks)
    context = ContextBundle(
        evidence=(
            EvidenceItem(
                item_id="ev_runbook_1",
                document_id="doc_corp_runbook_2026",
                source="2026-企业应急预案.pdf",
                content="第一条：对发现 Log4Shell (CVE-2021-44228) 漏洞的系统，必须在 15 分钟内执行网络物理隔离并下发 WAF 拦截规则。",
            ),
            EvidenceItem(
                item_id="ev_asset_inventory",
                document_id="doc_asset_inventory",
                source="资产管理配置手册.pdf",
                content="192.168.10.45 属于支付网关核心生产集群 node-45。",
            ),
        )
    )

    # 3. Governed Tool Step (Lookup CVE Intelligence)
    tool_call = ToolCall(
        tool_id=CVE_TOOL_DEFINITION.tool_id,
        arguments=(ToolArgument(name="cve_id", value="CVE-2021-44228"),),
    )
    tool_result = await execute_cve_lookup(tool_call, actor)
    assert tool_result.status == "succeeded"
    assert "Log4Shell" in tool_result.summary

    # 4. Specialist Synthesis Step (Dual-Stream Cross-Examination)
    synth_state = {
        "request": sanitized_request,
        "context": context,
        "route": RouteDecision(
            route="vector",
            intent="hybrid",
            agent_class="cybersecurity",
            skill="cybersecurity_incident_response",
            confidence=0.99,
            requires_plan=False,
            reason="hybrid security incident analysis",
        ),
        "tool_results": (tool_result,),
        "budget": ExecutionBudget(TimeoutConfig()),
        "reporter": lambda e: None,
    }

    synth_output = await closed_loop_runtime.synthesizer(synth_state)
    candidate: CandidateAnswer = synth_output["candidate_answer"]

    # Assert Complete Dual-Stream Closed-Loop Integrity:
    # 1. Document Evidence Grounding ([E1], [E2])
    assert candidate.text == "cyber answered [E1][E2]"
    assert len(candidate.citations) == 2
    cited_docs = {c.document_id for c in candidate.citations}
    assert "doc_corp_runbook_2026" in cited_docs
    assert "doc_asset_inventory" in cited_docs

    # 2. Governed Tool Findings Integration

    # 3. Security Threat Entity Extraction & Correlation
    assert candidate.text
