"""The document specialist: where an answer's excerpts come from, read from metadata only.

A7 asks "这份合同第 3 章讲了什么？"; the answer has to say which document, page and
section it quotes. The finding is built from what the pipeline recorded (page,
the heading the chunker carried onto a chunk), never from what the text says
about itself, and it states plainly when no heading was recognised -- which is
every Chinese document without Markdown headings.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.agents.catalog import AgentClass
from app.agents.document.service import NO_HEADINGS_NOTE, DocumentAgentService, locations_tool_result
from app.agents.rag.evidence_builder import bundle_from_bm25_records
from app.agents.registry import get_domain_agent_registry, reset_domain_agent_registry
from app.domain.contracts import EvidenceItem
from app.domain.knowledge import AccessScope
from app.domain.workflow import ContextBundle
from app.orchestration.request import OrchestrationRequest
from app.privacy.dlp import mask_evidence
from app.services.agent_classifier import classify_agent_class
from app.services.security.access_scope import DEFAULT_CONTEXT_FIELDS


@pytest.fixture(autouse=True)
def _fresh_registry():
    reset_domain_agent_registry()
    yield
    reset_domain_agent_registry()


def _item(name: str, page: int | None, heading: str | None = None, layer: str = "evidence") -> EvidenceItem:
    return EvidenceItem(
        content=f"text on page {page}",
        source=f"/uploads/alice/{name}",
        document_id=f"doc-{name}",
        page=page,
        heading=heading,
        layer=layer,
        retriever="vector",
    )


# --- the finding --------------------------------------------------------------------------


def test_pages_and_sections_are_reported_per_document() -> None:
    evidence = (
        _item("contract.pdf", 4, "Chapter 3 Payment"),
        _item("contract.pdf", 3, "Chapter 3 Payment"),
        _item("contract.pdf", 5, "Chapter 4 Delivery"),
        _item("annex.pdf", 1, "Annex A"),
    )

    summary = locations_tool_result(evidence).summary

    assert "contract.pdf -- pages 3, 4, 5 -- sections: Chapter 3 Payment; Chapter 4 Delivery" in summary
    assert "annex.pdf -- pages 1 -- sections: Annex A" in summary
    assert NO_HEADINGS_NOTE not in summary


def test_no_recognised_heading_is_said_rather_than_hidden() -> None:
    summary = locations_tool_result((_item("合同.pdf", 3), _item("合同.pdf", 4))).summary

    assert "合同.pdf -- pages 3, 4" in summary
    assert NO_HEADINGS_NOTE in summary


def test_web_tool_and_memory_items_are_not_documents() -> None:
    evidence = (_item("page.html", None, layer="web"), _item("m", None, layer="memory"))

    assert locations_tool_result(evidence) is None


def test_the_finding_is_derived_not_evidence() -> None:
    finding = locations_tool_result((_item("a.pdf", 1),))

    assert finding.derived and finding.status == "succeeded"


def test_long_lists_are_cut() -> None:
    evidence = tuple(_item("big.pdf", page) for page in range(1, 30))

    assert "(+17)" in locations_tool_result(evidence).summary


# --- the finding reaches synthesis --------------------------------------------------------


def test_the_specialist_hands_the_finding_to_synthesis() -> None:
    seen = {}

    async def synthesize_candidate(request, context, tool_results, skill):
        seen["tools"] = tool_results
        seen["skill"] = skill
        return "answer"

    agent = DocumentAgentService(synthesizer=SimpleNamespace(synthesize_candidate=synthesize_candidate))
    context = ContextBundle(evidence=(_item("contract.pdf", 3, "Chapter 3 Payment"),))

    asyncio.run(
        agent.synthesize_candidate(OrchestrationRequest(question="第 3 章讲了什么"), context, (), "pdf_text_reader")
    )

    assert seen["skill"] == "pdf_text_reader"
    assert [tool.tool_id for tool in seen["tools"]] == ["querymind_document_locations"]


# --- the heading reaches the evidence, and DLP covers it ----------------------------------


def test_the_chunk_heading_reaches_the_evidence_item() -> None:
    record = {
        "id": "c1",
        "text": "Payment is due in 30 days.",
        "metadata": {"source": "/u/a/contract.md", "document_id": "d1", "page": 3, "heading": "## Chapter 3 Payment"},
        "bm25_score": 1.0,
    }

    (item,) = bundle_from_bm25_records([record]).items

    assert item.heading == "## Chapter 3 Payment"


def _scope(fields=DEFAULT_CONTEXT_FIELDS) -> AccessScope:
    return AccessScope(
        tenant_id="alice", user_id="alice", role="viewer", allowed_sources=frozenset({"/u/a.md"}), allowed_fields=fields
    )


def test_a_heading_is_redacted_like_the_content() -> None:
    item = EvidenceItem(
        content="body", source="/u/a.md", document_id="d", heading="Contact 13800138000", retriever="vector"
    )

    masked = mask_evidence(item, _scope())

    assert "13800138000" not in masked.heading


def test_no_content_permission_means_no_heading() -> None:
    item = EvidenceItem(content="body", source="/u/a.md", document_id="d", heading="Salaries", retriever="vector")

    masked = mask_evidence(item, _scope(fields=frozenset({"source"})))

    assert masked.heading is None and masked.content == "[REDACTED_FIELD]"


# --- routing ----------------------------------------------------------------------------------


def test_the_registry_builds_the_specialist() -> None:
    assert isinstance(get_domain_agent_registry().get_agent(AgentClass.PDF_TEXT), DocumentAgentService)


@pytest.mark.parametrize("question", ["OCR 这张照片上的文字", "提取这份pdf第三页的表述", "Read the text in this image"])
def test_reading_questions_still_route_to_it(question: str) -> None:
    assert classify_agent_class(question) == AgentClass.PDF_TEXT
