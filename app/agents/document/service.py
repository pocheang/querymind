"""Document specialist: reads content out of the user's documents, and says where it came from.

It answers with `pdf_text_reader` -- reproduce, keep structure, cite per
passage -- and reports, as a tool finding, which documents, pages and sections
the retrieved excerpts come from. That finding is built from evidence METADATA
(the chunk's recorded page and the heading the chunker carried onto it), never
from the text, so it is something the pipeline recorded rather than something a
document says about itself.

Its known limit is stated rather than hidden: section headings are recognised in
Markdown and Latin script only (`app/ingestion/processing/structure.py`), so a
Chinese document without `#` headings reaches this finding with pages and no
sections, and the finding says so.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import PurePosixPath

from app.agents.base import BaseSpecialistAgent
from app.agents.catalog import AgentClass
from app.domain.contracts import EvidenceItem, ToolResult

PIPELINE_SKILLS: dict[str, str] = {"pdf_text_reader": "pdf_text_reader"}

LOCATIONS_TOOL_ID = "querymind_document_locations"

# How many documents, pages and sections the finding names; the rest is counted.
_MAX_DOCUMENTS = 5
_MAX_PAGES = 12
_MAX_SECTIONS = 8

NO_HEADINGS_NOTE = (
    "no section headings were recognised -- headings are recognised in Markdown and Latin script only, "
    "so a document with Chinese headings has pages here but no sections"
)


def _document_name(item: EvidenceItem) -> str:
    return PurePosixPath(item.source.replace("\\", "/")).name or item.document_id


def _locations(evidence: Sequence[EvidenceItem]) -> dict[str, tuple[list[int], list[str]]]:
    by_document: dict[str, tuple[list[int], list[str]]] = {}
    for item in evidence:
        if item.layer != "evidence":
            continue
        pages, sections = by_document.setdefault(_document_name(item), ([], []))
        if item.page is not None and item.page not in pages:
            pages.append(item.page)
        if item.heading and item.heading not in sections:
            sections.append(item.heading)
    return by_document


def _describe(name: str, pages: list[int], sections: list[str]) -> str:
    parts = [name]
    if pages:
        shown = sorted(pages)[:_MAX_PAGES]
        more = f" (+{len(pages) - len(shown)})" if len(pages) > len(shown) else ""
        parts.append("pages " + ", ".join(str(page) for page in shown) + more)
    if sections:
        parts.append("sections: " + "; ".join(sections[:_MAX_SECTIONS]))
    return " -- ".join(parts)


def locations_tool_result(evidence: Sequence[EvidenceItem]) -> ToolResult | None:
    """Which documents, pages and sections the evidence comes from."""

    by_document = _locations(evidence)
    if not by_document:
        return None
    lines = [_describe(name, pages, sections) for name, (pages, sections) in list(by_document.items())[:_MAX_DOCUMENTS]]
    if not any(sections for _, sections in by_document.values()):
        lines.append(NO_HEADINGS_NOTE)
    return ToolResult(
        tool_id=LOCATIONS_TOOL_ID,
        status="succeeded",
        derived=True,
        summary="Where the retrieved excerpts come from -- " + "; ".join(lines),
    )


class DocumentAgentService(BaseSpecialistAgent):
    """Specialist for reading PDFs, scans, images and other documents."""

    @property
    def agent_class(self) -> str:
        return AgentClass.PDF_TEXT

    @property
    def supported_skills(self) -> tuple[str, ...]:
        return ("pdf_text_reader",)

    def pick_skill(self, question: str) -> str:
        del question
        return "pdf_text_reader"

    @property
    def intent_keywords(self) -> tuple[str, ...]:
        # Moved here from `app/services/agent_classifier.py`, where they were the
        # one class no registered specialist owned. Matched as words.
        return (
            "pdf",
            "pdf提取",
            "提取pdf",
            "读取pdf",
            "pdf文字",
            "pdf文本",
            "ocr",
            "图片",
            "图像",
            "照片",
            "截图",
            "image",
        )

    pipeline_skills = PIPELINE_SKILLS
    fallback_pipeline_skill = "pdf_text_reader"

    def evidence_findings(self, evidence: Sequence[EvidenceItem]) -> ToolResult | None:
        return locations_tool_result(evidence)


__all__ = ["NO_HEADINGS_NOTE", "PIPELINE_SKILLS", "DocumentAgentService", "locations_tool_result"]
