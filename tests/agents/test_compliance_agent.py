"""The compliance specialist: its answer shapes, what it extracts, and the `policy` alias.

Also the shared-corpus folder label, which is how a regulation placed in
`data/docs/compliance/` becomes compliance material without a registry row.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.agents.catalog import AgentClass, normalize_agent_class
from app.agents.compliance.service import (
    CITATION_PATTERNS,
    ComplianceAgentService,
    extract_regulation_citations,
)
from app.agents.registry import get_domain_agent_registry, reset_domain_agent_registry
from app.agents.synthesizer.skills import SKILL_TEMPLATES
from app.services.documents import domain_labels
from app.services.documents.domain_labels import folder_label, load_domain_labels
from app.services.parser_profiles import choose_parser_profile


@pytest.fixture(autouse=True)
def _fresh_registry():
    reset_domain_agent_registry()
    yield
    reset_domain_agent_registry()


# --- what it extracts ------------------------------------------------------------------


def test_laws_are_extracted_with_their_article() -> None:
    found = extract_regulation_citations(
        "依据《个人信息保护法》第十三条和《数据安全法》，以及《个人信息保护法》第十三条。"
    )

    assert found["laws"] == ["《个人信息保护法》第十三条", "《数据安全法》"]


def test_a_named_article_without_book_title_marks_is_extracted() -> None:
    """How the bundled texts' article headings and most prose write a citation."""

    found = extract_regulation_citations("#### 个人信息保护法 第十九条\n依据中华人民共和国数据安全法第二十一条执行。")

    assert found["laws"] == ["《个人信息保护法》第十九条", "《数据安全法》第二十一条"]


def test_the_same_article_in_both_forms_is_listed_once() -> None:
    found = extract_regulation_citations("《个人信息保护法》第十九条，即个人信息保护法 第十九条")

    assert found["laws"] == ["《个人信息保护法》第十九条"]


def test_standards_are_extracted_with_their_year() -> None:
    found = extract_regulation_citations("按 GB/T 22239-2019 与 GB 17859 执行，另见GB/T35273。")

    assert found["standards"] == ["GB/T 22239-2019", "GB 17859", "GB/T 35273"]


def test_gdpr_articles_are_extracted_with_their_paragraphs() -> None:
    found = extract_regulation_citations("Under Article 17(1)(a) and Art. 32 of the GDPR, and Article 17(1)(a) again.")

    assert found["articles"] == ["Article 17(1)(a)", "Article 32"]


def test_text_citing_nothing_yields_no_finding() -> None:
    assert ComplianceAgentService(synthesizer=object()).domain_findings("我们每年做一次安全培训。") is None


def test_the_finding_is_a_derived_tool_result() -> None:
    finding = ComplianceAgentService(synthesizer=object()).domain_findings("《网络安全法》第二十一条")

    assert finding is not None and finding.derived
    assert "laws: 《网络安全法》第二十一条" in finding.summary


def _unbounded(pattern: str) -> list[str]:
    """Quantifiers with no upper bound, outside character classes."""

    body = re.sub(r"\\.", "", pattern)
    body = re.sub(r"\[[^\]]*\]", "", body)
    return re.findall(r"[*+]|\{\d+,\}", body)


@pytest.mark.parametrize("compiled", CITATION_PATTERNS, ids=lambda c: c.pattern[:20])
def test_every_quantifier_in_the_patterns_is_bounded(compiled: re.Pattern[str]) -> None:
    """With every repetition bounded, a failed attempt costs at most its bound: linear in the text."""

    assert not _unbounded(compiled.pattern), compiled.pattern


def test_the_bound_check_can_fail() -> None:
    assert _unbounded(r"《([^《》]+)》") == ["+"]
    assert _unbounded(r"GB\d{4,}") == ["{4,}"]
    assert not _unbounded(r"[a+*]{1,3}")


# --- answer shapes ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("question", "skill"),
    [
        ("我们的数据保留制度符合个人信息保护法吗？", "compliance_gap_analysis"),
        ("员工监控制度满足数据安全法的要求吗？", "compliance_gap_analysis"),
        ("Does our password policy meet GDPR requirements?", "compliance_gap_analysis"),
        ("个人信息保护法对敏感个人信息有什么要求？", "compliance_qa"),
        ("What does GDPR Article 17 require?", "compliance_qa"),
    ],
)
def test_a_gap_analysis_only_when_the_question_asks_whether_something_complies(question: str, skill: str) -> None:
    assert ComplianceAgentService(synthesizer=object()).pick_skill(question) == skill


@pytest.mark.parametrize(
    ("skill", "pipeline"),
    [
        ("compliance_gap_analysis", "compliance_gap_analysis"),
        ("compliance_qa", "answer_with_citations"),
        ("", "answer_with_citations"),
    ],
)
def test_each_skill_reaches_a_template(skill: str, pipeline: str) -> None:
    assert ComplianceAgentService(synthesizer=object()).pipeline_skill_for(skill) == pipeline


def test_the_gap_template_forbids_quoting_a_clause_from_memory() -> None:
    template = SKILL_TEMPLATES["compliance_gap_analysis"]

    for text in ("满足", "部分满足", "缺失", "无法判断", "not legal advice", "never quote a clause"):
        assert text in template, text


def test_the_registry_builds_the_specialist() -> None:
    specialist = get_domain_agent_registry().get_agent(AgentClass.COMPLIANCE)

    assert isinstance(specialist, ComplianceAgentService)
    assert get_domain_agent_registry().get_agent("policy") is None, "the alias is resolved by normalize, not here"


# --- the `policy` alias -----------------------------------------------------------------


@pytest.mark.parametrize("value", ["policy", "POLICY", " compliance "])
def test_policy_reads_as_compliance(value: str) -> None:
    assert normalize_agent_class(value) == AgentClass.COMPLIANCE


@pytest.mark.parametrize("agent_class", ["policy", "compliance"])
def test_both_names_get_the_policy_parser_profile(agent_class: str) -> None:
    assert choose_parser_profile(Path("rules.md"), agent_class)["name"] == "policy"


def test_a_registry_row_written_as_policy_is_labelled_compliance(tmp_path: Path, monkeypatch) -> None:
    registry = tmp_path / "documents.jsonl"
    registry.write_text(
        json.dumps({"document_id": "d1", "source": "/u/rules.md", "agent_class": "policy"}) + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(domain_labels, "_shared_root", lambda: "")
    monkeypatch.setattr(domain_labels, "_cache", None)

    assert load_domain_labels(registry).label_of("d1", None) == AgentClass.COMPLIANCE


# --- shared-corpus folders --------------------------------------------------------------


def test_a_shared_corpus_folder_names_the_label(tmp_path: Path) -> None:
    root = str(tmp_path.resolve())
    (tmp_path / "compliance").mkdir()

    assert folder_label(str(tmp_path / "compliance" / "pipl.md"), root) == AgentClass.COMPLIANCE
    assert folder_label(str(tmp_path / "compliance" / "gdpr" / "art17.md"), root) == AgentClass.COMPLIANCE
    assert folder_label(str(tmp_path / "policy" / "old.md"), root) == AgentClass.COMPLIANCE


@pytest.mark.parametrize("relative", ["pipl.md", "laws/pipl.md"])
def test_a_file_at_the_root_or_in_an_unnamed_folder_has_no_label(tmp_path: Path, relative: str) -> None:
    assert folder_label(str(tmp_path / relative), str(tmp_path.resolve())) is None


def test_a_file_outside_the_shared_corpus_has_no_folder_label(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    assert folder_label(str(tmp_path / "uploads" / "compliance" / "x.md"), str(root.resolve())) is None


def test_the_folder_label_holds_with_no_registry_and_yields_to_one(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "docs"
    source = str(root / "compliance" / "pipl.md")
    monkeypatch.setattr(domain_labels, "_shared_root", lambda: str(root.resolve()))
    monkeypatch.setattr(domain_labels, "_cache", None)

    assert load_domain_labels(tmp_path / "missing.jsonl").label_of(None, source) == AgentClass.COMPLIANCE

    registry = tmp_path / "documents.jsonl"
    registry.write_text(json.dumps({"source": source, "agent_class": "general"}) + "\n", encoding="utf-8")
    assert load_domain_labels(registry).label_of(None, source) == AgentClass.GENERAL
