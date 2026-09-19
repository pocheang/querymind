"""Tests for dynamic adaptive routing and planning across extensible domain agents."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from app.agents.base import BaseSpecialistAgent
from app.agents.planner.service import PlannerAgentService
from app.agents.registry import DomainAgentRegistry, reset_domain_agent_registry
from app.agents.router.routing import _skill_for
from app.agents.router.service import RouterAgentService
from app.domain.contracts import EvidenceItem, ToolResult
from app.domain.extension import DomainExtensionBundle
from app.domain.workflow import CandidateAnswer, ContextBundle
from app.mcp.contracts import ToolDefinition
from app.mcp.registry import ToolExecutor
from app.orchestration.langgraph.nodes import WorkflowNodeRuntime
from app.orchestration.policies import ExecutionPolicy
from app.orchestration.request import OrchestrationRequest, RequestActor, RequestScope
from app.orchestration.timeout_control import ExecutionBudget, TimeoutConfig
from app.pipeline.profiles import PipelineProfile
from app.services.agent_classifier import classify_agent_class
from app.tools.base import BaseToolProvider
from app.tools.category import ToolCategory
from app.tools.registry import reset_domain_tool_registry


@pytest.fixture(autouse=True)
def _cleanup_registries():
    reset_domain_agent_registry()
    reset_domain_tool_registry()
    yield
    reset_domain_agent_registry()
    reset_domain_tool_registry()


class MockDataAnalysisAgent(BaseSpecialistAgent):
    """Dynamic 3rd-party domain specialist agent for SQL and statistical analysis."""

    @property
    def agent_class(self) -> str:
        return "data_analysis"

    @property
    def supported_skills(self) -> tuple[str, ...]:
        return ("sql_generation", "statistical_summary")

    @property
    def default_tool_category(self) -> ToolCategory:
        return ToolCategory.DATA_ANALYSIS

    @property
    def intent_keywords(self) -> tuple[str, ...]:
        return ("sql", "数据分析", "统计分析", "销售额", "留存率", "均值")

    @property
    def intent_patterns(self) -> tuple[str, ...]:
        return (r"\bsql\b", r"数据分析", r"留存率")

    def pick_skill(self, question: str) -> str:
        text = question.lower()
        if "sql" in text:
            return "sql_generation"
        return "statistical_summary"

    async def synthesize_candidate(
        self,
        request: OrchestrationRequest,
        context: ContextBundle,
        tool_results: Sequence[ToolResult] | tuple[ToolResult, ...] = (),
        skill: str = "sql_generation",
    ) -> CandidateAnswer:
        tool_findings = "; ".join(t.summary for t in tool_results) if tool_results else "无工具执行数据"
        return CandidateAnswer(
            text=f"【数据分析研判报告】针对问题 '{request.question}'，执行技能 [{skill}]。分析结果: {tool_findings} [E1]",
            citations=(),
        )


class MockDataAnalysisToolProvider(BaseToolProvider):
    """Governed tool provider for SQL sandboxed queries."""

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DATA_ANALYSIS

    @property
    def tool_definitions(self) -> tuple[ToolDefinition, ...]:
        return (
            ToolDefinition(
                tool_id="querymind_data_sql_query",
                operation="read",
                risk="read_only",
                description="Executes a safe sandboxed read-only SQL query",
                parameters=(),
                category=ToolCategory.DATA_ANALYSIS.value,
            ),
        )

    def get_executor(self, tool_id: str) -> ToolExecutor | None:
        if tool_id == "querymind_data_sql_query":

            async def _exec(**_kwargs):
                return {"rows": [{"quarter": "Q3", "revenue": 1280000, "retention": 0.88}]}

            return _exec
        return None


@pytest.mark.asyncio
async def test_end_to_end_dynamic_adaptive_routing_and_execution_closed_loop():
    """Verify that registering a DomainExtensionBundle dynamically enables:

    1. Automatic intent identification in agent_classifier (0 config change)
    2. Dynamic skill suggestion in _skill_for
    3. Dynamic agent_class and skill in RouteDecision
    4. Adaptive tool budget allocation in PlannerAgentService
    5. Dynamic multi-dispatch in LangGraph WorkflowNodeRuntime.synthesizer
    """
    # Step 1: Register domain bundle
    agent = MockDataAnalysisAgent()
    tool_provider = MockDataAnalysisToolProvider()
    bundle = DomainExtensionBundle(
        domain_id="data_analysis_plugin",
        display_name="数据分析插件包",
        agent=agent,
        tool_provider=tool_provider,
    )
    bundle.register()

    # Step 2: Test automatic intent classification in agent_classifier
    query = "请帮我用 SQL 分析上季度的留存率和销售额"
    matched_class = classify_agent_class(query)
    assert matched_class == "data_analysis", "Router classifier must dynamically identify new domain agent_class"

    # Step 3: Test dynamic skill selection
    suggested_skill = _skill_for(matched_class, query)
    assert suggested_skill == "sql_generation", "Router must dynamically query the specialist agent for skill"

    # Step 4: Test RouterAgentService end-to-end route resolution
    actor = RequestActor(user_id="analyst_1", tenant_id="t1", role="user")
    req = OrchestrationRequest(
        question=query,
        actor=actor,
        source_scope=RequestScope(),
    )
    # Using decider mock that leverages _classify and _skill_for
    router_service = RouterAgentService()
    route = await router_service.route(req)

    assert route.agent_class == "data_analysis"
    assert route.skill == "sql_generation"

    # Step 5: Test PlannerAgentService adaptive tool planning
    tool_route = route.model_copy(
        update={
            "intent": "tool_call",
            "route": "react",
            "requires_plan": True,
            "allowed_capabilities": frozenset({"rag", "tool"}),
        }
    )
    planner = PlannerAgentService()
    plan = await planner.plan(req, tool_route)
    assert plan.requires_tools is True
    assert any(t.tool_required for t in plan.tasks)

    # Step 6: Test LangGraph synthesizer dynamic dispatch
    class _MockServices:
        def __init__(self, agent_reg: DomainAgentRegistry) -> None:
            self.domain_agent_registry = agent_reg

            async def _fallback(request, context, tool_results, skill):
                return CandidateAnswer(text="fallback")

            self.candidate_synthesizer = _fallback

    from app.agents.registry import get_domain_agent_registry

    runtime = WorkflowNodeRuntime(
        services=_MockServices(get_domain_agent_registry()),  # type: ignore[arg-type]
        policy=ExecutionPolicy.for_profile(PipelineProfile.ADVANCED),
        max_verifier_retries=1,
        context_token_budget=4000,
    )

    state = {
        "request": req,
        "context": ContextBundle(
            evidence=(EvidenceItem(item_id="e1", document_id="d1", source="s1", content="Q3 financial report"),)
        ),
        "route": route,
        "tool_results": (
            ToolResult(
                tool_id="querymind_data_sql_query",
                status="succeeded",
                summary="revenue=1280000, retention=0.88",
            ),
        ),
        "budget": ExecutionBudget(TimeoutConfig()),
        "reporter": lambda e: None,
    }

    synthesizer_output = await runtime.synthesizer(state)
    ans = synthesizer_output["candidate_answer"]
    assert "【数据分析研判报告】" in ans.text
    assert "revenue=1280000, retention=0.88" in ans.text
    assert "[sql_generation]" in ans.text
