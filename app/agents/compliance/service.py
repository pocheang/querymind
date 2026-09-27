"""Compliance specialist: does a practice meet what a regulation or standard requires.

Two answer shapes. `compliance_gap_analysis` -- conclusion, a clause-by-clause
table (the requirement, the current practice, met / partly met / missing /
cannot tell), remediation, and a statement that this is not legal advice --
for a question asking whether something complies. Every other question about a
regulation or an internal policy is answered with citations as usual.

What it extracts is the regulations a text cites: a book-title law with its
article (《个人信息保护法》第十三条), a national standard (GB/T 22239-2019), a
GDPR article. Like the other specialists' extractions this is a tool finding,
not evidence: it is derived from material the model can already read.

The boundary with the security specialist, as the router's guide states it:
whether a practice meets a law or standard is compliance; how to implement a
technical control is security.
"""

from __future__ import annotations

import re

from app.agents.base import BaseSpecialistAgent
from app.agents.catalog import AgentClass
from app.domain.contracts import ToolResult
from app.services.query.keyword_match import any_keyword

PIPELINE_SKILLS: dict[str, str] = {
    "compliance_gap_analysis": "compliance_gap_analysis",
    "compliance_qa": "answer_with_citations",
}

# Every quantifier below is bounded and every pattern opens on a literal, so a
# failed attempt costs at most its bound before the scan moves on: the work is
# linear in the text however it is shaped (tests/agents/test_compliance_agent.py
# asserts the bounds on these compiled objects).
_BOOK_TITLE = re.compile(r"《([^《》\n]{1,40})》(?:第([一二三四五六七八九十百零〇\d]{1,8})条)?")
_STANDARD = re.compile(r"(?<![A-Za-z])(GB(?:/[TZ])?)[ \t]{0,2}(\d{4,5}(?:\.\d{1,2})?(?:-\d{4})?)")
# A paragraph is numbered and a point lettered: Article 17(1)(a).
_ARTICLE = re.compile(r"(?<![A-Za-z])Art(?:icle|\.)[ \t]{0,2}(\d{1,3})((?:\((?:\d{1,2}|[a-z])\)){0,2})")

CITATION_PATTERNS: tuple[re.Pattern[str], ...] = (_BOOK_TITLE, _STANDARD, _ARTICLE)

_MAX_PER_KIND = 12

# A question asking whether something complies, rather than what a rule says.
_GAP_KEYWORDS = (
    "符合",
    "合规吗",
    "满足",
    "差距",
    "违反",
    "达标",
    "不合规",
    "comply",
    "compliant",
    "compliance gap",
    "gap analysis",
    "meet",
    "meets",
    "violate",
    "violates",
)

REGULATIONS_TOOL_ID = "querymind_compliance_citation_extract"


def _first_distinct(values: list[str]) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return seen[:_MAX_PER_KIND]


def extract_regulation_citations(text: str) -> dict[str, list[str]]:
    """The laws, standards and GDPR articles a text cites, in order of appearance."""

    laws = [f"《{m.group(1)}》" + (f"第{m.group(2)}条" if m.group(2) else "") for m in _BOOK_TITLE.finditer(text)]
    standards = [f"{m.group(1)} {m.group(2)}" for m in _STANDARD.finditer(text)]
    articles = [f"Article {m.group(1)}{m.group(2)}" for m in _ARTICLE.finditer(text)]
    return {
        "laws": _first_distinct(laws),
        "standards": _first_distinct(standards),
        "articles": _first_distinct(articles),
    }


def citation_tool_result(citations: dict[str, list[str]]) -> ToolResult | None:
    """The cited regulations, carried as a tool finding rather than as evidence."""

    lines = [f"{kind}: {', '.join(values)}" for kind, values in sorted(citations.items()) if values]
    if not lines:
        return None
    return ToolResult(
        tool_id=REGULATIONS_TOOL_ID,
        status="succeeded",
        derived=True,
        summary="Regulations cited in the question and retrieved material -- " + "; ".join(lines),
    )


class ComplianceAgentService(BaseSpecialistAgent):
    """Specialist for regulations, standards and internal policy."""

    @property
    def agent_class(self) -> str:
        return AgentClass.COMPLIANCE

    @property
    def supported_skills(self) -> tuple[str, ...]:
        return ("compliance_gap_analysis", "compliance_qa")

    def pick_skill(self, question: str) -> str:
        """A gap analysis when the question asks whether something complies; a cited answer otherwise."""

        if any_keyword(question, _GAP_KEYWORDS):
            return "compliance_gap_analysis"
        return "compliance_qa"

    @property
    def intent_keywords(self) -> tuple[str, ...]:
        return (
            "合规",
            "法规",
            "监管",
            "法律条款",
            "个人信息保护法",
            "个保法",
            "数据安全法",
            "网络安全法",
            "等级保护",
            "等保",
            "gdpr",
            "ccpa",
            "hipaa",
            "pci dss",
            "iso 27001",
            "compliance",
            "regulation",
            "regulatory",
        )

    pipeline_skills = PIPELINE_SKILLS
    fallback_pipeline_skill = "answer_with_citations"

    def domain_findings(self, text: str) -> ToolResult | None:
        return citation_tool_result(extract_regulation_citations(text))


__all__ = [
    "CITATION_PATTERNS",
    "PIPELINE_SKILLS",
    "ComplianceAgentService",
    "citation_tool_result",
    "extract_regulation_citations",
]
