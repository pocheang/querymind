"""A specialist can consult its own read-only tools, and only those.

Only a `react` route carried the `tool` capability, and the router's prompt
reserves `react` for multi-step reasoning. Measured on a real model, none of
six questions naming a CVE, an ATT&CK technique or a model size reached the
tool stage -- "look up the CVSS score of CVE-2022-22965" included -- so the CVE
lookup, the ATT&CK lookup and the calculator were unreachable from ordinary
questions. `default_tool_category` existed on every specialist and nothing read
it.

What these pin: the route gains `tool` when the answering specialist has a
read-only tool, and nothing else about the route changes; a consulted catalogue
holds that specialist's read tools and nothing else; a consultation that finds
nothing to do reports nothing; and the requested path still reports "no action
taken".
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.agents.base import BaseSpecialistAgent
from app.agents.catalog import AgentClass
from app.agents.registry import get_domain_agent_registry, reset_domain_agent_registry
from app.agents.router.service import RouterAgentService
from app.agents.tool.catalog import catalog_for_route, is_consulted
from app.agents.tool.selector import ToolSelection
from app.agents.tool.service import SELECTOR_TOOL_ID, ToolAgentService
from app.core.config import get_settings
from app.domain.contracts import RouteDecision, ToolResult
from app.mcp.approvals import ApprovalStore
from app.mcp.audit import AuditLog
from app.mcp.authorization import AuthorizationPolicy
from app.mcp.contracts import ToolArgument, ToolCall, ToolDefinition, ToolParameter
from app.mcp.gateway import MCPGateway
from app.mcp.registry import ToolRegistry
from app.orchestration.langgraph.nodes import _knowledge_hints
from app.orchestration.policies import ExecutionPolicy
from app.orchestration.request import OrchestrationRequest, RequestActor, RequestScope
from app.tools.category import ToolCategory

_ACTOR = RequestActor(user_id="alice", tenant_id="acme", role="viewer")


@pytest.fixture(autouse=True)
def _fresh_registry():
    reset_domain_agent_registry()
    yield
    reset_domain_agent_registry()


def _tool(tool_id: str, category: str, operation: str = "read") -> ToolDefinition:
    return ToolDefinition(
        tool_id=tool_id,
        operation=operation,
        risk="read_only" if operation == "read" else "idempotent",
        category=category,
        parameters=(ToolParameter(name="value", required=False, max_length=64),),
    )


_CVE = _tool("querymind_test_cve", ToolCategory.CYBERSECURITY)
_CYBER_WRITE = _tool("querymind_test_isolate_host", ToolCategory.CYBERSECURITY, operation="write")
_MATH = _tool("querymind_test_math", ToolCategory.ARTIFICIAL_INTELLIGENCE)
_TABLE = _tool("querymind_test_table", ToolCategory.GENERAL)
_CATALOG = (_CVE, _CYBER_WRITE, _MATH, _TABLE)


def _route(agent_class: str, *, intent: str = "knowledge_retrieval", tool: bool = True) -> RouteDecision:
    return RouteDecision(
        intent=intent,
        route="react" if intent == "tool_call" else "vector",
        confidence=0.9,
        requires_plan=intent == "tool_call",
        allowed_capabilities=frozenset({"rag", "tool"} if tool else {"rag"}),
        reason="test",
        agent_class=agent_class,
    )


# --- the router --------------------------------------------------------------


def _legacy(agent_class: str, route: str = "vector", reason: str = "llm_decision"):
    return SimpleNamespace(
        route=route, confidence=0.9, raw_confidence=0.9, reason=reason, agent_class=agent_class, skill="x"
    )


async def _routed(agent_class: str, **legacy) -> RouteDecision:
    router = RouterAgentService(decider=lambda *a, **k: _legacy(agent_class, **legacy))
    return await router.route(OrchestrationRequest(question="CVE-2021-44228 影响哪些版本", source_scope=RequestScope()))


@pytest.mark.asyncio
async def test_a_specialist_with_read_tools_gets_the_tool_capability() -> None:
    decision = await _routed(AgentClass.CYBERSECURITY)

    assert "tool" in decision.allowed_capabilities
    assert decision.intent == "knowledge_retrieval", "the route must not become a tool request"
    assert decision.route == "vector"
    assert decision.reason.endswith("|specialist_tools:cybersecurity")


@pytest.mark.asyncio
async def test_the_capability_changes_nothing_about_retrieval() -> None:
    with_tools = await _routed(AgentClass.CYBERSECURITY)
    without = with_tools.model_copy(update={"allowed_capabilities": frozenset({"rag"})})

    assert _knowledge_hints(with_tools) == _knowledge_hints(without)


@pytest.mark.asyncio
@pytest.mark.parametrize("agent_class", [AgentClass.GENERAL, AgentClass.PDF_TEXT, AgentClass.POLICY, "unknown"])
async def test_no_specialist_tools_no_capability(agent_class: str) -> None:
    decision = await _routed(agent_class)
    assert "tool" not in decision.allowed_capabilities


@pytest.mark.asyncio
async def test_a_greeting_consults_nothing() -> None:
    decision = await _routed(AgentClass.CYBERSECURITY, reason="smalltalk_local_only")
    assert "tool" not in decision.allowed_capabilities


@pytest.mark.asyncio
async def test_the_switch_turns_it_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "specialist_tools_enabled", False)
    decision = await _routed(AgentClass.CYBERSECURITY)
    assert "tool" not in decision.allowed_capabilities


@pytest.mark.asyncio
async def test_a_specialist_whose_category_has_no_tools_gets_nothing() -> None:
    class _Finance(BaseSpecialistAgent):
        def __init__(self) -> None:
            super().__init__(synthesizer=SimpleNamespace())

        @property
        def agent_class(self) -> str:
            return "finance"

        @property
        def default_tool_category(self) -> ToolCategory:
            return ToolCategory.WEB_SEARCH  # a category with no registered provider

    get_domain_agent_registry().register_agent(_Finance())
    decision = await _routed("finance")
    assert "tool" not in decision.allowed_capabilities


@pytest.mark.asyncio
async def test_the_capability_reaches_the_tool_stage() -> None:
    from app.agents.planner.service import PlannerAgentService

    decision = await _routed(AgentClass.CYBERSECURITY)
    request = OrchestrationRequest(question="CVE-2021-44228 影响哪些版本")
    plan = await PlannerAgentService().plan(request, decision)

    assert ExecutionPolicy.for_profile("advanced").should_run_tools(decision, plan)


# --- the catalogue -----------------------------------------------------------


def test_a_consulted_catalogue_is_the_specialists_read_tools_only() -> None:
    offered = catalog_for_route(_CATALOG, _route(AgentClass.CYBERSECURITY))
    assert offered == (_CVE,)


def test_a_consulted_catalogue_never_offers_a_write_tool() -> None:
    offered = catalog_for_route(_CATALOG, _route(AgentClass.CYBERSECURITY))
    assert all(tool.operation == "read" for tool in offered)
    assert _CYBER_WRITE not in offered


def test_a_request_keeps_the_specialists_category_and_the_shared_ones() -> None:
    offered = catalog_for_route(_CATALOG, _route(AgentClass.CYBERSECURITY, intent="tool_call"))
    assert set(offered) == {_CVE, _CYBER_WRITE, _TABLE}


def test_a_request_with_no_specialist_keeps_everything() -> None:
    assert catalog_for_route(_CATALOG, _route(AgentClass.GENERAL, intent="tool_call")) == _CATALOG
    assert catalog_for_route(_CATALOG, None) == _CATALOG


def test_nothing_is_consulted_without_a_specialist() -> None:
    assert catalog_for_route(_CATALOG, _route(AgentClass.GENERAL)) == ()


def test_consulted_means_the_user_did_not_ask_for_an_action() -> None:
    assert is_consulted(_route(AgentClass.CYBERSECURITY))
    assert not is_consulted(_route(AgentClass.CYBERSECURITY, intent="tool_call"))
    assert not is_consulted(None)


# --- the tool stage ----------------------------------------------------------


def _stack(*definitions: ToolDefinition):
    registry = ToolRegistry(
        authorization=AuthorizationPolicy(),
        approvals=ApprovalStore(Path(tempfile.mkdtemp()) / "app.db"),
        audit=AuditLog(write=lambda _record: None),
    )

    async def executor(call: ToolCall, actor: RequestActor) -> ToolResult:
        del actor
        return ToolResult(tool_id=call.tool_id, status="succeeded", summary=f"{call.tool_id} ran")

    for definition in definitions:
        registry.register(definition, executor)
    return MCPGateway(registry), registry


class _Selector:
    def __init__(self, tool_id: str | None) -> None:
        self._tool_id = tool_id
        self.catalogues: list[tuple[str, ...]] = []

    async def select(self, question, conversation, catalog, *, observations=(), execution_id):
        del question, conversation
        self.catalogues.append(tuple(tool.tool_id for tool in catalog))
        if self._tool_id is None or observations:
            return ToolSelection(call=None, reason="nothing fits")
        return ToolSelection(
            call=ToolCall(
                tool_id=self._tool_id,
                arguments=(ToolArgument(name="value", value="CVE-2021-44228"),),
                execution_id=execution_id,
            ),
            reason="picked",
        )


def _service(selector: _Selector) -> ToolAgentService:
    gateway, registry = _stack(*_CATALOG)
    return ToolAgentService(
        gateway, registry, approvals=ApprovalStore(Path(tempfile.mkdtemp()) / "app.db"), selector=selector
    )


def _request() -> OrchestrationRequest:
    return OrchestrationRequest(question="CVE-2021-44228 影响哪些版本", actor=_ACTOR, execution_id="run-1")


@pytest.mark.asyncio
async def test_a_consultation_runs_the_chosen_tool() -> None:
    selector = _Selector("querymind_test_cve")
    results = await _service(selector).run(_request(), _route(AgentClass.CYBERSECURITY), plan=None)

    assert [(r.tool_id, r.status) for r in results] == [("querymind_test_cve", "succeeded")]
    assert selector.catalogues[0] == ("querymind_test_cve",)


@pytest.mark.asyncio
async def test_a_consultation_that_finds_nothing_reports_nothing() -> None:
    results = await _service(_Selector(None)).run(_request(), _route(AgentClass.CYBERSECURITY), plan=None)
    assert results == ()


@pytest.mark.asyncio
async def test_a_request_that_finds_nothing_still_says_so() -> None:
    results = await _service(_Selector(None)).run(
        _request(), _route(AgentClass.CYBERSECURITY, intent="tool_call"), plan=None
    )
    assert [(r.tool_id, r.status) for r in results] == [(SELECTOR_TOOL_ID, "skipped")]


@pytest.mark.asyncio
async def test_an_empty_consultation_spends_no_model_call() -> None:
    selector = _Selector("querymind_test_cve")
    results = await _service(selector).run(_request(), _route(AgentClass.GENERAL), plan=None)

    assert results == ()
    assert selector.catalogues == [], "the selector must not be asked when nothing may be consulted"
