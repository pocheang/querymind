"""A fact taken from a governed tool result is cited as one, end to end.

Measured before this change, on the sentence grounding the finalizer runs:
"CVE-2021-44228 的 CVSS 评分为 10.0" was hedged as "基于当前可用证据，..." because
only retrieved evidence counted as support and the score came from the CVE
lookup; and an answer built from tools alone had no evidence at all, so
grounding reported `no_evidence` and checked nothing.

Tool results now have a marker space of their own, `[T{k}]`, separate from
`[E{k}]`: a tool is not a document, so it never takes a document's number.
These tests follow one tool result from the prompt to the reader-facing list.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.agents.finalizer.service import _ground
from app.agents.synthesizer.citations import (
    citable_tool_results,
    citation_labels_from_contexts,
    number_tool_markers,
    render_tool_source_list,
    tool_citation_labels,
)
from app.agents.synthesizer.generation import SynthesisContexts, _allowed_markers_line
from app.agents.synthesizer.service import SynthesizerAgentService, _render_tool_results
from app.agents.verifier.service import VerifierAgentService
from app.domain.contracts import EvidenceBundle, EvidenceItem, FinalAnswer, ToolResult
from app.domain.knowledge import AccessScope
from app.domain.workflow import CandidateAnswer, ContextBundle
from app.orchestration.langgraph.nodes import WorkflowNodeRuntime
from app.orchestration.policies import ExecutionPolicy
from app.orchestration.request import OrchestrationRequest
from app.orchestration.timeout_control import ExecutionBudget, TimeoutConfig
from app.privacy.service import PrivacyService
from app.services.security.access_scope import DEFAULT_CONTEXT_FIELDS

_CVE = ToolResult(
    tool_id="querymind_cyber_cve_lookup",
    status="succeeded",
    summary="[CVE-2021-44228] Log4Shell (CVSS 10.0 CRITICAL, NVD): Affects Apache Log4j 2.0-beta9 to before 2.15.0",
)
_ATTACK = ToolResult(
    tool_id="querymind_cyber_mitre_attack", status="succeeded", summary="[T1190] Exploit Public-Facing Application"
)
_FAILED = ToolResult(tool_id="querymind_cyber_cve_lookup", status="failed", summary="lookup failed")
_PENDING = ToolResult(tool_id="querymind_connector_disable_owned", status="approval_required", summary="needs approval")
_DERIVED = ToolResult(
    tool_id="querymind_cyber_indicator_extract", status="succeeded", derived=True, summary="cves: CVE-2021-44228"
)
_EVIDENCE = EvidenceItem(
    content="Log4Shell 应急预案：发现后先隔离受影响主机，再升级 log4j-core。",
    source="playbook.md",
    document_id="playbook.md",
    version=1,
    page=1,
    retriever="vector",
)
_ANSWER = "CVE-2021-44228 的 CVSS 评分为 10.0，属于严重级别。处置上应先隔离受影响主机，再升级 log4j-core。"


# --- what is citable ---------------------------------------------------------


def test_only_a_tool_that_ran_and_looked_something_up_is_citable() -> None:
    assert citable_tool_results((_FAILED, _CVE, _PENDING, _DERIVED, _ATTACK)) == (_CVE, _ATTACK)


def test_an_empty_summary_has_nothing_to_cite() -> None:
    assert citable_tool_results((_CVE.model_copy(update={"summary": "  "}),)) == ()


def test_the_prompt_labels_exactly_the_citable_results_in_order() -> None:
    rendered = _render_tool_results((_FAILED, _CVE, _DERIVED, _ATTACK))

    assert tool_citation_labels(rendered) == frozenset({"T1", "T2"})
    assert "[T1] (querymind_cyber_cve_lookup) -> succeeded" in rendered
    assert "[T2] (querymind_cyber_mitre_attack) -> succeeded" in rendered
    # Reported, never cited.
    assert "Tool (querymind_cyber_cve_lookup) -> failed" in rendered
    assert "Tool (querymind_cyber_indicator_extract) -> succeeded" in rendered


def test_the_two_label_spaces_never_mix() -> None:
    contexts = SynthesisContexts(
        vector="[E1] document=playbook.md\n隔离主机",
        tool=_render_tool_results((_CVE,)),
    )

    assert contexts.citation_labels == frozenset({"E1", "T1"})
    # Each space is read only from its own section, in both directions.
    assert citation_labels_from_contexts(*SynthesisContexts(tool=contexts.tool).evidence_sections) == frozenset()
    assert tool_citation_labels(contexts.vector) == frozenset()


def test_the_model_is_told_which_markers_are_for_tools() -> None:
    line = _allowed_markers_line({"E2", "E10", "E1", "T1", "doc1:3"})

    assert "retrieved evidence: [E1], [E2], [E10], [doc1:3]." in line
    assert "governed tool results: [T1]." in line


# --- synthesis ---------------------------------------------------------------


def _context(*items: EvidenceItem) -> ContextBundle:
    rendered = "\n\n".join(
        f"[E{index}] document={item.document_id}; source={item.source}\n{item.content}"
        for index, item in enumerate(items, start=1)
    )
    return ContextBundle(evidence=items, rendered_context=rendered)


async def _candidate_and_contexts(
    answer: str, context: ContextBundle, tools: tuple[ToolResult, ...]
) -> tuple[CandidateAnswer, SynthesisContexts]:
    seen: dict[str, object] = {}

    def generate(*_args: object, **kwargs: object) -> dict:
        seen.update(kwargs)
        return {"answer": answer}

    candidate = await SynthesizerAgentService(generate=generate).synthesize_candidate(
        OrchestrationRequest(question="Log4Shell 怎么处置"), context, tools
    )
    return candidate, seen["contexts"]


async def _candidate(answer: str, context: ContextBundle, tools: tuple[ToolResult, ...]) -> CandidateAnswer:
    return (await _candidate_and_contexts(answer, context, tools))[0]


@pytest.mark.asyncio
async def test_a_tool_citation_is_kept_and_recorded() -> None:
    candidate, contexts = await _candidate_and_contexts(
        "CVSS 为 10.0 [T1]，先隔离主机 [E1]。", _context(_EVIDENCE), (_CVE,)
    )

    assert "[T1]" in candidate.text
    assert candidate.tool_citations == ("T1",)
    assert candidate.tool_sources == (_CVE,)
    assert contexts.citation_labels == frozenset({"E1", "T1"})


@pytest.mark.asyncio
async def test_citing_only_a_tool_is_not_an_uncited_answer() -> None:
    candidate = await _candidate("CVSS 为 10.0 [T1]。", _context(_EVIDENCE), (_CVE,))
    assert "missing_citations" not in candidate.unresolved_items


@pytest.mark.asyncio
async def test_a_tool_marker_with_no_tool_behind_it_is_removed() -> None:
    candidate = await _candidate("CVSS 为 10.0 [T3]，先隔离主机 [E1]。", _context(_EVIDENCE), (_CVE,))

    assert "[T3]" not in candidate.text
    assert candidate.tool_citations == ()


@pytest.mark.asyncio
async def test_a_derived_finding_cannot_be_cited() -> None:
    candidate = await _candidate("编号是 CVE-2021-44228 [T1]。", _context(_EVIDENCE), (_DERIVED,))

    assert "[T1]" not in candidate.text
    assert candidate.tool_sources == ()


# --- verification -------------------------------------------------------------


class _Validator:
    def __init__(self) -> None:
        self.documents: list = []
        self.citations: list = []

    async def __call__(self, question, answer, documents, citations):
        self.documents, self.citations = list(documents), list(citations)
        return SimpleNamespace(is_valid=True, action="approve", issues=(), validation_details=None)


@pytest.mark.asyncio
async def test_a_tool_only_answer_is_not_treated_as_evidence_less() -> None:
    validator = _Validator()
    candidate = CandidateAnswer(text="CVSS 为 10.0 [T1]。", tool_sources=(_CVE,), tool_citations=("T1",))

    decision = await VerifierAgentService(validator=validator).verify(
        OrchestrationRequest(question="q"), ContextBundle(), candidate, retry_count=1
    )

    assert "no authorized evidence retrieved" not in decision.missing_aspects
    assert decision.status == "approved"
    assert [doc["content"] for doc in validator.documents] == [_CVE.summary]
    assert [record["content"] for record in validator.citations] == [_CVE.summary]


@pytest.mark.asyncio
async def test_citing_a_tool_beside_evidence_is_an_attributable_citation() -> None:
    candidate = CandidateAnswer(text="CVSS 为 10.0 [T1]。", tool_sources=(_CVE,), tool_citations=("T1",))
    decision = await VerifierAgentService(validator=_Validator()).verify(
        OrchestrationRequest(question="q"), _context(_EVIDENCE), candidate, retry_count=1
    )
    assert "answer has no attributable citation" not in decision.missing_aspects


@pytest.mark.asyncio
async def test_with_neither_evidence_nor_a_tool_the_answer_is_still_evidence_less() -> None:
    decision = await VerifierAgentService(validator=_Validator()).verify(
        OrchestrationRequest(question="q"), ContextBundle(), CandidateAnswer(text="x"), retry_count=1
    )
    assert "no authorized evidence retrieved" in decision.missing_aspects


# --- sentence grounding ---------------------------------------------------------


def test_a_sentence_taken_from_a_tool_is_not_hedged() -> None:
    """The measured case: the CVSS sentence was hedged with evidence alone."""

    evidence = EvidenceBundle(items=(_EVIDENCE,))
    hedged, _ = _ground(_ANSWER, evidence)
    grounded, stats = _ground(_ANSWER, evidence, (_CVE,))

    assert hedged.startswith("基于当前可用证据")
    assert grounded == _ANSWER
    assert stats["rewritten_sentences"] == 0


def test_an_answer_from_tools_alone_is_still_checked() -> None:
    _, stats = _ground("CVSS 评分为 10.0。", EvidenceBundle(), (_CVE,))
    assert stats["reason"] != "no_evidence"


def test_a_derived_finding_does_not_count_as_support() -> None:
    _, stats = _ground("CVSS 评分为 10.0。", EvidenceBundle(), (_DERIVED,))
    assert stats["reason"] == "no_evidence"


# --- numbering and the reader-facing list ------------------------------------------


def test_tool_markers_are_numbered_by_first_appearance() -> None:
    text, cited = number_tool_markers("a [T2], b [T1], c [T2], d [T9].", (_CVE, _ATTACK))

    # Renumbered in reading order, one number per tool, and a marker with no
    # tool behind it removed along with the space before its punctuation.
    assert text == "a [T1], b [T2], c [T1], d."
    assert cited == (_ATTACK, _CVE)


def test_the_tool_list_names_each_tool_and_what_it_returned() -> None:
    long_summary = _CVE.model_copy(update={"summary": "x" * 400 + "\nsecond line"})
    rendered = render_tool_source_list((_CVE, long_summary), "en")

    assert rendered.startswith("**Tool sources**")
    assert f"- [T1] querymind_cyber_cve_lookup: {_CVE.summary}" in rendered
    assert "second line" not in rendered
    assert rendered.rstrip().endswith("…")
    assert render_tool_source_list((), "zh") == ""


def _scope() -> AccessScope:
    return AccessScope(
        tenant_id="tenant-1",
        user_id="user-1",
        role="viewer",
        allowed_sources=frozenset({"playbook.md"}),
        allowed_fields=DEFAULT_CONTEXT_FIELDS,
    )


async def _filtered(answer_text: str, tools: tuple[ToolResult, ...]) -> FinalAnswer:
    runtime = WorkflowNodeRuntime(
        services=SimpleNamespace(privacy=PrivacyService()),
        policy=ExecutionPolicy(),
        max_verifier_retries=1,
        context_token_budget=2000,
    )
    evidence = EvidenceBundle(items=(_EVIDENCE,))
    state = {
        "request": OrchestrationRequest(question="Log4Shell 怎么处置"),
        "final_answer": FinalAnswer(
            answer=answer_text,
            evidence=evidence,
            evidence_ids=(_EVIDENCE.item_id,),
            tool_results=tools,
        ),
        "evidence_bundle": evidence,
        "permission_scope": _scope(),
        "budget": ExecutionBudget(TimeoutConfig()),
        "reporter": lambda _event: None,
    }
    return (await runtime.output_filter(state))["final_answer"]


@pytest.mark.asyncio
async def test_the_reader_sees_tool_sources_after_the_references() -> None:
    answer = await _filtered("CVSS 为 10.0 [T1]，先隔离主机 [E1]。", (_FAILED, _CVE))

    body, _, tail = answer.answer.partition("**参考来源**")
    assert "[T1]" in body and "[1]" in body
    assert tail.index("playbook.md") < tail.index("**工具来源**")
    assert "- [T1] querymind_cyber_cve_lookup: [CVE-2021-44228] Log4Shell" in tail


@pytest.mark.asyncio
async def test_no_tool_cited_no_tool_list() -> None:
    answer = await _filtered("先隔离主机 [E1]。", (_CVE,))
    assert "工具来源" not in answer.answer


@pytest.mark.asyncio
async def test_the_tool_list_goes_through_output_dlp() -> None:
    secret = _CVE.model_copy(update={"summary": "contact admin@example.com for the patch"})
    answer = await _filtered("见工具结果 [T1]。", (secret,))

    assert "admin@example.com" not in answer.answer
    assert answer.safety["output_dlp"]["redactions"] >= 1


# --- the live draft --------------------------------------------------------------


class _Collect:
    def __init__(self) -> None:
        self.fragments: list[str] = []

    def publish(self, execution_id: str, fragment: str) -> None:
        self.fragments.append(fragment)


def test_the_live_draft_shows_no_tool_marker(monkeypatch: pytest.MonkeyPatch) -> None:
    """The draft is streamed before output_filter numbers anything, so both
    internal marker kinds are stripped from it; a raw `[T1]` there would point
    at a list the reader has not been given yet."""

    from app.orchestration import answer_stream

    answers, thoughts = _Collect(), _Collect()
    monkeypatch.setattr(answer_stream, "get_default_answer_stream_store", lambda: answers)
    monkeypatch.setattr(answer_stream, "get_default_thought_stream_store", lambda: thoughts)

    def generate(*_args: object, on_token=None, **_kwargs: object) -> dict:
        text = "CVSS 为 10.0 [T1]，先隔离主机 [E1]，再升级 log4j-core。"
        for piece in (text[:12], text[12:]):
            on_token(piece)
        return {"answer": text}

    token = answer_stream.current_answer_stream_id.set("run-1")
    try:
        SynthesizerAgentService(generate=generate)._generate_streaming("q", "skill")
    finally:
        answer_stream.current_answer_stream_id.reset(token)

    draft = "".join(answers.fragments)
    assert "CVSS 为 10.0" in draft
    assert "[T1]" not in draft
    assert "[E1]" not in draft
