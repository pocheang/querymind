"""Unit tests for DomainAgentRegistry, BaseSpecialistAgent, and DomainExtensionBundle."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from app.agents.base import BaseSpecialistAgent
from app.agents.registry import DomainAgentRegistry, reset_domain_agent_registry
from app.domain.contracts import ToolResult
from app.domain.extension import DomainExtensionBundle
from app.domain.workflow import CandidateAnswer, ContextBundle
from app.mcp.contracts import ToolDefinition
from app.mcp.registry import ToolExecutor
from app.orchestration.request import OrchestrationRequest
from app.tools.base import BaseToolProvider
from app.tools.category import ToolCategory
from app.tools.registry import DomainToolRegistry


@pytest.fixture(autouse=True)
def _cleanup_agent_registry():
    reset_domain_agent_registry()
    yield
    reset_domain_agent_registry()


class DummyDataAnalysisAgent(BaseSpecialistAgent):
    """Dummy domain specialist for testing dynamic extensibility."""

    @property
    def agent_class(self) -> str:
        return "data_analysis"

    @property
    def supported_skills(self) -> tuple[str, ...]:
        return ("sql_generation", "statistical_summary")

    @property
    def default_tool_category(self) -> ToolCategory:
        return ToolCategory.DATA_ANALYSIS

    async def synthesize_candidate(
        self,
        request: OrchestrationRequest,
        context: ContextBundle,
        tool_results: Sequence[ToolResult] | tuple[ToolResult, ...] = (),
        skill: str = "statistical_summary",
    ) -> CandidateAnswer:
        return CandidateAnswer(
            answer=f"Data analysis response for {request.question}",
            citations=(),
        )


class DummyDataAnalysisToolProvider(BaseToolProvider):
    """Dummy tool provider for testing domain bundles."""

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
                description="Executes a sandboxed SQL query",
                parameters=(),
                category=ToolCategory.DATA_ANALYSIS.value,
            ),
        )

    def get_executor(self, tool_id: str) -> ToolExecutor | None:
        if tool_id == "querymind_data_sql_query":

            async def _exec(**_kwargs):
                return {"rows": [{"count": 42}]}

            return _exec
        return None


def test_default_agent_registry_contains_cyber_and_ai():
    reg = DomainAgentRegistry()
    classes = reg.list_agent_classes()
    assert "cybersecurity" in classes
    assert "artificial_intelligence" in classes

    cyber = reg.get_agent("cybersecurity")
    assert cyber is not None
    assert cyber.agent_class == "cybersecurity"
    assert cyber.default_tool_category == ToolCategory.CYBERSECURITY

    ai = reg.get_agent("artificial_intelligence")
    assert ai is not None
    assert ai.agent_class == "artificial_intelligence"
    assert ai.default_tool_category == ToolCategory.ARTIFICIAL_INTELLIGENCE


def test_agent_skill_lookup():
    reg = DomainAgentRegistry()
    cyber = reg.get_agent_for_skill("cybersecurity_incident_response")
    assert cyber is not None
    assert cyber.agent_class == "cybersecurity"

    ai = reg.get_agent_for_skill("compute_estimation")
    assert ai is not None
    assert ai.agent_class == "artificial_intelligence"

    unknown = reg.get_agent_for_skill("non_existent_skill_xyz")
    assert unknown is None


def test_dynamic_agent_registration():
    reg = DomainAgentRegistry()
    custom_agent = DummyDataAnalysisAgent()
    reg.register_agent(custom_agent)

    classes = reg.list_agent_classes()
    assert "data_analysis" in classes

    retrieved = reg.get_agent("data_analysis")
    assert retrieved is custom_agent

    by_skill = reg.get_agent_for_skill("sql_generation")
    assert by_skill is custom_agent

    desc = reg.describe()
    assert "data_analysis" in desc["agents"]
    assert desc["agents"]["data_analysis"]["agent_class"] == "data_analysis"
    assert desc["agents"]["data_analysis"]["tool_category"] == "data_analysis"


def test_domain_extension_bundle_registers_both_agent_and_tools():
    agent_reg = DomainAgentRegistry()
    tool_reg = DomainToolRegistry()

    bundle = DomainExtensionBundle(
        domain_id="data_analysis_suite",
        display_name="数据分析与探索套件",
        agent=DummyDataAnalysisAgent(),
        tool_provider=DummyDataAnalysisToolProvider(),
    )

    bundle.register(agent_registry=agent_reg, tool_registry=tool_reg)

    # 1. Verify agent registered
    assert agent_reg.get_agent("data_analysis") is not None
    # 2. Verify tool provider registered
    tools = tool_reg.get_tools_by_category(ToolCategory.DATA_ANALYSIS)
    assert len(tools) == 1
    assert tools[0].tool_id == "querymind_data_sql_query"

    desc = bundle.describe()
    assert desc["domain_id"] == "data_analysis_suite"
    assert desc["agent"]["agent_class"] == "data_analysis"
    assert desc["tool_provider"]["tools_count"] == 1
