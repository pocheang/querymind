"""Which validation findings decide an answer, and which only qualify it.

Replayed over thirty real answers on 2026-09-27, validation approved none.
Three decisions came out of it, each pinned here in both directions:

- Pattern heuristics -- a number, a name or a date the sources do not visibly
  contain -- degrade an answer; they never reject it or retry it on their own.
  They used to reject directly, and also indirectly, by lowering the rule
  stage's confidence under the verifier's factuality floor.
- Entailment is not judged across scripts: a Chinese answer against English
  sources (a tool result, an English page) abstains instead of failing.
- Entailment, citations and safety still decide.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.agents.verifier.service import VerifierAgentService
from app.agents.verifier.validation import nli
from app.agents.verifier.validation.models import HEURISTIC_ISSUE_TYPES, RuleBasisIssue, ValidationRequest
from app.agents.verifier.validation.public import _to_answer_issue
from app.agents.verifier.validation.rules import RuleValidator
from app.domain.workflow import CandidateAnswer, ContextBundle
from app.orchestration.request import OrchestrationRequest


def _validator(*issues, action: str = "approve", factuality: float = 0.95):
    async def validate(question, answer, documents, citations):
        return SimpleNamespace(
            is_valid=action != "regenerate",
            action=action,
            issues=tuple(SimpleNamespace(type=t, content=c) for t, c in issues),
            validation_details=SimpleNamespace(factual_consistency=factuality, citation_completeness=1.0),
        )

    return validate


def _verify(validator, retry_count: int = 0):
    from app.agents.synthesizer.service import _references_from_markers
    from app.domain.contracts import EvidenceItem

    item = EvidenceItem(content="The CVSS score is 9.8.", source="a", document_id="a", version=1, retriever="vector")
    context = ContextBundle(evidence=(item,))
    text = "The CVSS score is 9.8 [E1]."
    return asyncio.run(
        VerifierAgentService(validator=validator).verify(
            OrchestrationRequest(question="q"),
            context,
            CandidateAnswer(text=text, citations=_references_from_markers(text, context)),
            retry_count,
        )
    )


# --- heuristics degrade, never reject ------------------------------------------------


def test_a_heuristic_finding_degrades_without_a_retry() -> None:
    """retry_count=0 would allow a retry; a heuristic must not spend it."""

    decision = _verify(_validator(("heuristic", "Number 7.1 not found in sources")), retry_count=0)

    assert decision.status == "degraded"
    assert decision.unsupported_claims == ("Number 7.1 not found in sources",)
    assert decision.retry_query is None


def test_an_entailment_failure_still_retries_and_then_rejects() -> None:
    finding = ("hallucination", "3 sentences not entailed")

    assert _verify(_validator(finding), retry_count=0).status == "retry_retrieval"
    assert _verify(_validator(finding), retry_count=1).status == "rejected"


def test_a_clean_answer_is_still_approved() -> None:
    assert _verify(_validator(), retry_count=0).status == "approved"


@pytest.mark.parametrize("issue_type", sorted(HEURISTIC_ISSUE_TYPES))
def test_every_heuristic_type_maps_to_the_heuristic_public_type(issue_type: str) -> None:
    issue = RuleBasisIssue(issue_type=issue_type, severity="high", content="x")
    assert _to_answer_issue(issue).type == "heuristic"


@pytest.mark.parametrize("issue_type", ["nli_contradiction", "llm_hallucination", "citation_mismatch_x"])
def test_other_findings_keep_their_type(issue_type: str) -> None:
    issue = RuleBasisIssue(issue_type=issue_type, severity="high", content="x")
    assert _to_answer_issue(issue).type != "heuristic"


def test_a_heuristic_finding_does_not_lower_the_rule_stage_confidence() -> None:
    """Each high issue cost 0.4, which pushed factuality under 0.7 and so
    rejected the answer through the back door."""

    request = ValidationRequest.from_compatibility(
        query="q",
        answer="The CVSS score is 7.1.",
        source_docs=[{"id": "d", "content": "The CVSS score is 9.8."}],
        citations=[],
    )
    result = asyncio.run(RuleValidator().validate(request))

    assert any(issue.issue_type in HEURISTIC_ISSUE_TYPES for issue in result.issues)
    assert result.confidence_score == pytest.approx(1.0)


# --- entailment across scripts ------------------------------------------------------------


def _nli(answer: str, source: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(nli, "load_nli_cross_encoder", lambda: None)
    request = ValidationRequest.from_compatibility(
        query="q", answer=answer, source_docs=[{"id": "d", "content": source}], citations=[]
    )
    return asyncio.run(nli.NLIValidator().validate(request))


_ENGLISH_SOURCE = "[CVE-2022-22965] Spring4Shell (CVSS 9.8 CRITICAL): affects Spring Framework before 5.3.18."


def test_a_chinese_answer_against_english_sources_abstains(monkeypatch: pytest.MonkeyPatch) -> None:
    result = _nli(
        "CVE-2022-22965 的 CVSS 评分为 9.8，属于严重级别。受影响版本为 5.3.18 之前。", _ENGLISH_SOURCE, monkeypatch
    )

    assert result.issues == []
    assert (result.backend, result.fallback_reason) == ("none", "cross_lingual")


def test_an_english_answer_against_chinese_sources_abstains(monkeypatch: pytest.MonkeyPatch) -> None:
    result = _nli("The retention window is ninety days for all backups.", "备份保留窗口为九十天。", monkeypatch)
    assert result.fallback_reason == "cross_lingual"


def test_the_same_script_is_still_checked(monkeypatch: pytest.MonkeyPatch) -> None:
    result = _nli(
        "The retention window is ninety days for every backup taken.", "Backups run nightly at two.", monkeypatch
    )

    assert result.backend == "lexical"
    assert result.issues != []


def test_an_unchecked_stage_is_not_reported_as_a_check() -> None:
    from app.agents.verifier.validation.models import CascadeLevel, CascadeResult, ValidationCascadeResult
    from app.agents.verifier.validation.public import _validation_method

    stage = CascadeResult(
        level=CascadeLevel.NLI_BATCH,
        has_issues=False,
        confidence_score=1.0,
        issues=[],
        execution_time_ms=0,
        should_continue=True,
        backend="none",
        fallback_reason="cross_lingual",
    )
    cascade = ValidationCascadeResult(
        has_issues=False,
        confidence_score=1.0,
        highest_level_reached=CascadeLevel.NLI_BATCH,
        all_issues=[],
        total_execution_time_ms=0,
        execution_time_ms=0,
        level_results=[stage],
        citation_completeness=1.0,
        answer_quality=1.0,
        safety_score=1.0,
    )
    assert _validation_method(cascade) == "standard_unchecked"


def test_a_cross_lingual_answer_validates_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    """Through the real `validate_answer`, not the naming helper alone: the
    helper returned `standard_unchecked` while the public result model did not
    accept it, so every such answer came back "verification unavailable"."""

    from app.agents.verifier.validation import deep
    from app.agents.verifier.validation.public import clear_validation_caches, validate_answer

    async def no_deep(self, request):
        from app.agents.verifier.validation.models import CascadeLevel, CascadeResult

        return CascadeResult(
            level=CascadeLevel.DEEP_LLM, has_issues=False, confidence_score=1.0, issues=[], execution_time_ms=0
        )

    monkeypatch.setattr(nli, "load_nli_cross_encoder", lambda: None)
    monkeypatch.setattr(deep.DeepValidator, "validate", no_deep)
    clear_validation_caches()
    try:
        result = asyncio.run(
            validate_answer(
                "q",
                "CVE-2022-22965 的 CVSS 评分为 9.8，属于严重级别。受影响版本为 5.3.18 之前。",
                [{"id": "d", "content": _ENGLISH_SOURCE}],
                [],
            )
        )
    finally:
        clear_validation_caches()

    assert result.validation_method in {"standard_unchecked", "deep"}
    assert not any(issue.type == "hallucination" for issue in result.issues)


def test_the_deep_stage_is_off_by_default() -> None:
    """Measured, not assumed: at 3s it timed out 12 times in 14; at 10s it took
    7-10s and called every answer it saw inconsistent without changing one
    verdict. Turning it back on is an operator's decision (still editable)."""

    from app.core.config import Settings

    assert Settings.model_fields["cascade_enable_deep"].default is False
