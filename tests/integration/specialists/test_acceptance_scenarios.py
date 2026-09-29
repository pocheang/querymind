"""The seven acceptance scenarios (plan section 13.3, A1-A7), through the real workflow.

Real: the LangGraph workflow, the router's specialist handling, the specialist
registry, the governed tool registry and every tool, the specialists' findings,
the synthesizer's prompt assembly, the verifier, the finalizer and
`output_filter`. Fake, and only these: the router model's decision, the tool
selector's choices, retrieval (each scenario supplies its evidence), and the
chat model -- which records the prompt it was given and answers with a fixed
text that cites what a correct answer would cite.

So what a scenario proves is the wiring: the right specialist and answer shape,
the tools called with the right arguments returning the right numbers, the
specialist's finding and the skill's template reaching the model, and the cited
tools and documents numbered for the reader. What a real model writes is
measured separately, by hand -- the plan records those runs.
"""

from __future__ import annotations

import asyncio
import gzip
import shutil
import tempfile
from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.agents.router.service import RouterAgentService
from app.agents.synthesizer import generation
from app.agents.tool.selector import ToolSelection
from app.agents.tool.service import ToolAgentService
from app.core.config import get_settings
from app.domain.contracts import EvidenceItem
from app.knowledge.context import ContextBuilder
from app.mcp.approvals import ApprovalStore
from app.mcp.audit import AuditLog
from app.mcp.authorization import AuthorizationPolicy
from app.mcp.contracts import ToolArgument, ToolCall
from app.mcp.gateway import MCPGateway
from app.mcp.registry import ToolRegistry
from app.orchestration.capabilities import CoreCapabilities
from app.orchestration.engine import OrchestrationEngine
from app.orchestration.request import OrchestrationRequest, RequestActor
from app.privacy.service import PrivacyService
from app.services.multimodal.models import TableContent
from app.services.security.access_scope import AccessScopeResolver
from app.services.security.security_guardrail import SecurityGuardrailService
from app.services.tables import store as table_store_module
from app.services.tables.store import TableStore
from app.services.threat_intel.store import ThreatIntelStore
from app.services.threat_intel.sync import sync_source
from app.tools.cyber import intel
from app.tools.registry import get_domain_tool_registry

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "threat_intel"
ACTOR = RequestActor(user_id="alice", tenant_id="alice", role="viewer")


# --- the fakes ---------------------------------------------------------------------------------


class RecordingModel:
    """A chat model that remembers what it was asked and gives one fixed answer."""

    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.prompts: list[str] = []

    def _record(self, messages) -> None:
        self.prompts.append("\n".join(str(content) for _, content in messages))

    def stream(self, messages):
        self._record(messages)
        yield SimpleNamespace(content=self.answer)

    def invoke(self, messages):
        self._record(messages)
        return SimpleNamespace(content=self.answer)


class ScriptedSelector:
    """Chooses the scripted calls in order within each run, then nothing.

    Keyed on how many steps the current run has taken (its observations), not on a
    cursor: the verifier's retry re-runs the tool stage from the top, and a real
    selector chooses again there.
    """

    def __init__(self, steps: Sequence[tuple[str, dict[str, str]]]) -> None:
        self.steps = list(steps)
        self.observations: list[tuple] = []

    async def select(self, question, conversation, catalog, *, observations=(), execution_id):
        del question, conversation
        self.observations.append(tuple(observations))
        offered = {tool.tool_id for tool in catalog}
        step = len(observations)
        if step >= len(self.steps):
            return ToolSelection(call=None, reason="done")
        tool_id, arguments = self.steps[step]
        assert tool_id in offered, f"{tool_id} was not offered to this specialist: {sorted(offered)}"
        return ToolSelection(
            call=ToolCall(
                tool_id=tool_id,
                arguments=tuple(ToolArgument(name=k, value=v) for k, v in arguments.items()),
                execution_id=execution_id,
            ),
            reason="scripted",
        )


def _decider(agent_class: str, skill: str):
    def decide(*_args, **_kwargs):
        return SimpleNamespace(
            route="vector",
            confidence=0.9,
            raw_confidence=0.9,
            reason="llm_decision",
            agent_class=agent_class,
            skill=skill,
        )

    return decide


def _evidence(source: str, content: str, *, page: int | None = 1, heading: str | None = None) -> EvidenceItem:
    return EvidenceItem(
        content=content,
        source=source,
        document_id=f"doc:{source}",
        version=1,
        page=page,
        heading=heading,
        retriever="vector",
        score=0.9,
    )


def _run(
    question: str,
    *,
    agent_class: str,
    skill: str,
    answer: str,
    steps: Sequence[tuple[str, dict[str, str]]] = (),
    evidence: Sequence[EvidenceItem] = (),
):
    model = RecordingModel(answer)
    selector = ScriptedSelector(steps)
    approvals = ApprovalStore(Path(tempfile.mkdtemp()) / "app.db")
    registry = ToolRegistry(
        authorization=AuthorizationPolicy(), approvals=approvals, audit=AuditLog(write=lambda _record: None)
    )
    get_domain_tool_registry().register_all_into(registry)

    async def retriever(request, route, plan, strategy, scope):
        del request, route, plan, strategy
        return ContextBuilder(token_budget=4_000).build(tuple(evidence), scope, diagnostics={})

    privacy = PrivacyService()
    rows = [{"source": item.source, "document_id": item.document_id, "tenant_id": "alice"} for item in evidence]
    capabilities = CoreCapabilities(
        typed_router=RouterAgentService(decider=_decider(agent_class, skill)),
        typed_tools=ToolAgentService(
            MCPGateway(registry),
            registry,
            approvals=approvals,
            selector=selector,
            settings=get_settings().model_copy(update={"tool_max_steps": 3}),
        ),
        typed_rag=SimpleNamespace(retrieve=retriever, set_degradation_reporter=lambda *_args: None),
        # Scope resolution belongs to the guardrail; this is where a test supplies the rows.
        security_guardrail=SecurityGuardrailService(
            privacy_service=privacy,
            access_scope_resolver=AccessScopeResolver(document_provider=lambda actor: rows),
        ),
        privacy=privacy,
    )
    engine = OrchestrationEngine(services=capabilities.orchestration_services())
    request = OrchestrationRequest(question=question, actor=ACTOR, execution_id="acceptance")
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(generation, "get_chat_model", lambda *a, **k: model)
        patch.setattr(generation, "get_reasoning_model", lambda *a, **k: model)
        final = asyncio.run(engine.execute(request))
    return final, model, selector


def _tools(final) -> list[tuple[str, str]]:
    return [(result.tool_id, result.status) for result in final.tool_results if not result.derived]


# --- stores the tools read ------------------------------------------------------------------------


@pytest.fixture
def threat_intel(monkeypatch) -> ThreatIntelStore:
    root = Path(tempfile.mkdtemp(prefix="querymind-acceptance-ti-"))
    directory = root / "import"
    (directory / "nvd").mkdir(parents=True)
    shutil.copy(FIXTURES / "kev.json", directory / "known_exploited_vulnerabilities.json")
    (directory / "epss_scores-current.csv.gz").write_bytes(gzip.compress((FIXTURES / "epss.csv").read_bytes()))
    shutil.copy(FIXTURES / "enterprise-attack.json", directory / "enterprise-attack.json")
    shutil.copy(FIXTURES / "nvd_page.json", directory / "nvd" / "page-0001.json")
    store = ThreatIntelStore(root / "ti.db")
    for source in ("nvd", "kev", "epss", "attack"):
        assert sync_source(source, store, from_dir=directory).status == "succeeded"
    monkeypatch.setattr(intel, "get_threat_intel_store", lambda: store)
    yield store
    shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
def empty_threat_intel(monkeypatch) -> ThreatIntelStore:
    root = Path(tempfile.mkdtemp(prefix="querymind-acceptance-ti-empty-"))
    store = ThreatIntelStore(root / "empty.db")
    monkeypatch.setattr(intel, "get_threat_intel_store", lambda: store)
    yield store
    shutil.rmtree(root, ignore_errors=True)


# --- A1-A3: cybersecurity -----------------------------------------------------------------------


def test_a1_an_affected_version_is_answered_from_the_store_with_the_playbook(threat_intel) -> None:
    playbook = _evidence(
        "/uploads/alice/log4shell-playbook.md", "Log4Shell 应急预案：先隔离受影响主机，再升级 log4j-core。"
    )
    final, model, _ = _run(
        "我们用的 log4j 2.14.1 受影响吗？怎么处置？",
        agent_class="cybersecurity",
        skill="cve_vulnerability_assessment",
        answer="结论：log4j 2.14.1 受 CVE-2021-44228 影响 [T1]。处置：先隔离受影响主机，再升级 log4j-core [E1]。",
        steps=[
            ("querymind_cyber_product_exposure", {"product": "log4j", "version": "2.14.1", "vendor": "apache"}),
            ("querymind_cyber_cve_lookup", {"cve_id": "CVE-2021-44228"}),
        ],
        evidence=[playbook],
    )

    assert (final.route.agent_class, final.route.skill) == ("cybersecurity", "cve_vulnerability_assessment")
    assert _tools(final) == [
        ("querymind_cyber_product_exposure", "succeeded"),
        ("querymind_cyber_cve_lookup", "succeeded"),
    ]
    exposure = next(r for r in final.tool_results if r.tool_id == "querymind_cyber_product_exposure")
    assert "CVE-2021-44228" in exposure.summary and "KEV" in exposure.summary
    assert 'Answer template for "are we affected by this vulnerability' in model.prompts[0]
    assert "querymind_cyber_product_exposure" in final.answer, "the cited tool is listed for the reader"
    assert "log4shell-playbook.md" in final.answer and "[E1]" not in final.answer
    # The tool panel shows the number the answer uses: only the cited result
    # carries one, and a tool that ran but was not cited carries none.
    markers = {r.tool_id: r.citation_marker for r in final.tool_results if not r.derived}
    assert markers == {"querymind_cyber_product_exposure": "T1", "querymind_cyber_cve_lookup": None}


def test_a2_a_technique_is_answered_from_the_synced_attack_data(threat_intel) -> None:
    final, _, _ = _run(
        "T1190 怎么检测和缓解？",
        agent_class="cybersecurity",
        skill="cyber_attack_analysis",
        answer="T1190 的检测与缓解见 ATT&CK [T1]。",
        steps=[("querymind_cyber_mitre_attack", {"technique_id": "T1190"})],
    )

    (attack,) = [r for r in final.tool_results if r.tool_id == "querymind_cyber_mitre_attack"]
    assert attack.status == "succeeded"
    assert "[T1190] Exploit Public-Facing Application" in attack.summary


def test_a3_an_empty_store_never_turns_not_found_into_safe(empty_threat_intel) -> None:
    final, _, _ = _run(
        "我们用的 log4j 2.14.1 受影响吗？怎么处置？",
        agent_class="cybersecurity",
        skill="cve_vulnerability_assessment",
        answer="本地情报库为空，无法判断 [T1]。",
        steps=[("querymind_cyber_product_exposure", {"product": "log4j", "version": "2.14.1", "vendor": "apache"})],
    )

    (exposure,) = [r for r in final.tool_results if r.tool_id == "querymind_cyber_product_exposure"]
    summary = exposure.summary.lower()
    assert "not affected" not in summary and "no known" not in summary
    assert "store" in summary or "curated" in summary, "the answer must say where the verdict came from"


# --- A4: AI --------------------------------------------------------------------------------------


def test_a4_the_memory_estimate_is_computed_not_written() -> None:
    final, model, _ = _run(
        "70B 模型 FP16 推理，32k 上下文、batch 4，需要多少显存？",
        agent_class="artificial_intelligence",
        skill="ai_engineering_estimate",
        answer="结论：约 130.4 GiB（仅权重）[T1]。",
        steps=[
            (
                "querymind_ai_memory_estimate",
                {"params": "70B", "precision": "fp16", "context_len": "32k", "batch": "4"},
            )
        ],
    )

    (estimate,) = [r for r in final.tool_results if r.tool_id == "querymind_ai_memory_estimate"]
    assert "70B x 2 (fp16) = 130.4 GiB" in estimate.summary
    assert "needs layers, kv_heads, head_dim" in estimate.summary, "no architecture is invented"
    assert "Answer template for an AI engineering estimate" in model.prompts[0]


# --- A5: data analysis ----------------------------------------------------------------------------


@pytest.fixture
def tables(monkeypatch) -> TableStore:
    store = TableStore()
    store.save_table(
        "alice",
        TableContent(
            table_id="table-sales",
            doc_id="d1",
            page_number=1,
            headers=["区域", "季度", "销售额"],
            rows=[["华东", "Q3", 1200], ["华北", "Q3", 800], ["华东", "Q3", 300], ["华东", "Q2", 1100]],
            summary="",
        ),
        owner_user_id="alice",
        source="/uploads/alice/销售表.xlsx",
    )
    store.save_table(
        "alice",
        TableContent(
            table_id="table-payroll", doc_id="d2", page_number=1, headers=["员工"], rows=[["张三"]], summary=""
        ),
        owner_user_id="bob",
        source="/uploads/bob/payroll.xlsx",
    )
    monkeypatch.setattr(table_store_module._GLOBAL_TABLE_STORE, "_value", store)
    return store


def test_a5_list_then_query_and_nobody_elses_table(tables) -> None:
    sql = "SELECT 区域, SUM(销售额) AS 销售额 FROM t WHERE 季度 = 'Q3' GROUP BY 区域 ORDER BY 区域"
    final, model, selector = _run(
        "我上传的销售表里，各区域第三季度的销售额是多少？",
        agent_class="data_analysis",
        skill="data_analysis_report",
        answer="结论：华东 1500、华北 800 [T2]。",
        steps=[
            ("querymind_table_list", {}),
            ("querymind_table_query", {"table_id": "table-sales", "sql": sql}),
        ],
    )

    assert _tools(final) == [("querymind_table_list", "succeeded"), ("querymind_table_query", "succeeded")]
    listing, query = (r for r in final.tool_results if not r.derived)
    assert "table-payroll" not in listing.summary and "区域" not in listing.summary
    assert "华东 | 1500" in query.summary.replace("  ", " ")
    assert selector.observations[-1][-1].summary == "", "the query's rows never reach the next selection"
    assert "Answer template for a computation over the user's tables" in model.prompts[0]


# --- A6: compliance -------------------------------------------------------------------------------


def test_a6_a_gap_analysis_cites_the_law_and_the_policy() -> None:
    law = _evidence(
        "/docs/compliance/中华人民共和国个人信息保护法.md",
        "#### 个人信息保护法 第十九条\n\n除法律、行政法规另有规定外，个人信息的保存期限应当为实现处理目的所必要的最短时间。",
        heading="#### 个人信息保护法 第十九条",
    )
    policy = _evidence("/uploads/alice/客户数据保留制度.md", "客户注销账户后，公司继续保留其全部个人信息十年。")
    final, model, _ = _run(
        "我们的数据保留制度符合个保法吗？",
        agent_class="compliance",
        skill="compliance_gap_analysis",
        answer=(
            "结论：不符合《个人信息保护法》第十九条 [E1]。\n\n"
            "| 要求 | 现状 | 状态 |\n|---|---|---|\n"
            "| 保存期限应为最短必要时间 [E1] | 注销后保留十年 [E2] | 缺失 |\n\n"
            "声明：以上是对所引文本的分析，不构成法律意见。"
        ),
        evidence=[law, policy],
    )

    assert (final.route.agent_class, final.route.skill) == ("compliance", "compliance_gap_analysis")
    assert 'Answer template for "does this practice or policy meet' in model.prompts[0]
    assert "laws: 《个人信息保护法》第十九条" in model.prompts[0], "the cited law reaches the model as a finding"
    assert "中华人民共和国个人信息保护法.md" in final.answer and "客户数据保留制度.md" in final.answer
    assert "不构成法律意见" in final.answer


# --- A7: documents --------------------------------------------------------------------------------


def test_a7_the_answer_is_told_which_page_and_section_it_quotes() -> None:
    chapter = _evidence(
        "/uploads/alice/软件服务合同.md",
        "## 第三章 付款与结算\n\n合同总价为人民币四十八万元，分三期支付。",
        page=3,
        heading="## 第三章 付款与结算",
    )
    final, model, _ = _run(
        "这份合同第 3 章讲了什么？",
        agent_class="pdf_text",
        skill="pdf_text_reader",
        answer="第三章 付款与结算 [E1]：合同总价为人民币四十八万元，分三期支付 [E1]。",
        evidence=[chapter],
    )

    assert (final.route.agent_class, final.route.skill) == ("pdf_text", "pdf_text_reader")
    assert "软件服务合同.md -- pages 3 -- sections: ## 第三章 付款与结算" in model.prompts[0]
    assert "Answer template for reading content out of documents" in model.prompts[0]
    assert "软件服务合同.md" in final.answer
