"""Unit and extensibility tests for ToolCategory and DomainToolRegistry."""

from app.domain.contracts import ToolResult
from app.mcp.contracts import ToolCall, ToolDefinition, ToolParameter
from app.mcp.registry import ToolExecutor
from app.orchestration.request import RequestActor
from app.tools.base import BaseToolProvider
from app.tools.category import ToolCategory, get_category_metadata
from app.tools.cyber.cve_tools import ATTACK_TOOL_DEFINITION, CVE_TOOL_DEFINITION
from app.tools.registry import DomainToolRegistry


def test_tool_category_metadata() -> None:
    cyber_meta = get_category_metadata(ToolCategory.CYBERSECURITY)
    assert cyber_meta.category == ToolCategory.CYBERSECURITY
    assert "网络安全" in cyber_meta.display_name
    assert cyber_meta.icon_tag == "shield-alert"

    ai_meta = get_category_metadata("artificial_intelligence")
    assert ai_meta.category == ToolCategory.ARTIFICIAL_INTELLIGENCE
    assert "AI" in ai_meta.display_name

    unknown_meta = get_category_metadata("non_existent_category")
    assert unknown_meta.category == ToolCategory.GENERAL


def test_domain_tool_registry_defaults() -> None:
    registry = DomainToolRegistry()
    tools = registry.list_all_tools()
    tool_ids = {t.tool_id for t in tools}

    assert CVE_TOOL_DEFINITION.tool_id in tool_ids
    assert ATTACK_TOOL_DEFINITION.tool_id in tool_ids
    assert "querymind_ai_math_eval" in tool_ids


def test_domain_tool_registry_filtering_by_category() -> None:
    registry = DomainToolRegistry()
    cyber_tools = registry.get_tools_by_category(ToolCategory.CYBERSECURITY)
    assert len(cyber_tools) >= 2
    for t in cyber_tools:
        assert t.category == ToolCategory.CYBERSECURITY.value

    ai_tools = registry.get_tools_by_category(ToolCategory.ARTIFICIAL_INTELLIGENCE)
    assert len(ai_tools) >= 1
    for t in ai_tools:
        assert t.category == ToolCategory.ARTIFICIAL_INTELLIGENCE.value


def test_domain_tool_registry_extensibility() -> None:
    """Verify that a new 3rd-party/plugin tool provider can be dynamically registered."""

    mock_def = ToolDefinition(
        tool_id="querymind_plugin_finance_calc",
        operation="read",
        risk="read_only",
        category="finance_extension",
        description="Calculate financial ROI and metrics.",
        parameters=(ToolParameter(name="metric", description="Metric to compute", required=True),),
    )

    async def mock_exec(call: ToolCall, actor: RequestActor) -> ToolResult:
        del actor
        return ToolResult(tool_id=call.tool_id, status="succeeded", summary="Metric calculated")

    class MockFinanceProvider(BaseToolProvider):
        @property
        def category(self) -> ToolCategory:
            return ToolCategory.GENERAL

        @property
        def tool_definitions(self) -> tuple[ToolDefinition, ...]:
            return (mock_def,)

        def get_executor(self, tool_id: str) -> ToolExecutor | None:
            return mock_exec if tool_id == mock_def.tool_id else None

    registry = DomainToolRegistry()
    provider = MockFinanceProvider()
    registry.register_provider(provider)

    all_tools = registry.list_all_tools()
    assert any(t.tool_id == "querymind_plugin_finance_calc" for t in all_tools)

    diag = registry.describe()
    assert "general" in diag
