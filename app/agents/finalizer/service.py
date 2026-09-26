"""Shared grounding, safety, validation, and quality finalization."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.domain.contracts import EvidenceBundle, FinalAnswer, OrchestratedQualityReport, ToolResult, ValidationStatus
from app.orchestration.policies import ExecutionPolicy
from app.orchestration.request import OrchestrationRequest

Validator = Callable[[str, str, list[dict[str, Any]], list[dict[str, Any]]], Awaitable[Any]]


class FinalizationService:
    """Deterministic terminal grounding, safety, and quality boundary."""

    def __init__(self, validator: Validator | None = None) -> None:
        self._validator = validator or _validate

    async def finalize(
        self,
        request: OrchestrationRequest,
        evidence: EvidenceBundle,
        candidate: FinalAnswer,
        policy: ExecutionPolicy,
    ) -> FinalAnswer:
        grounded, grounding = _ground(candidate.answer, evidence, candidate.tool_results)
        safe, safety = _sanitize(grounded)
        # Reasoning is unredacted the moment it leaves the model (see
        # CandidateAnswer.reasoning) and reaches a reader through the live
        # stream before this stage ever runs -- but the *persisted*/reloaded
        # copy must not carry anything the answer itself would not be allowed
        # to. No `_ground` here: reasoning carries no `[E{k}]` markers to
        # hedge the same way the answer's sentences do.
        safe_reasoning = _sanitize(candidate.reasoning)[0] if candidate.reasoning else None
        verified = candidate.validation.method.startswith("verifier")
        validation = candidate.validation if verified else await self._validation_status(request, safe, evidence)
        quality = _quality_report(validation, grounding, policy)

        return candidate.model_copy(
            update={
                "answer": safe,
                "reasoning": safe_reasoning,
                "citations": candidate.citations if verified else candidate.citations or evidence.citations,
                "evidence": evidence,
                "evidence_ids": candidate.evidence_ids if verified else candidate.evidence_ids or evidence.item_ids,
                "grounding": grounding,
                "safety": safety,
                "validation": validation,
                "quality_report": quality,
                "execution_metadata": {
                    **(candidate.execution_metadata or {}),
                    "profile": policy.profile.value,
                    "validation_required": policy.require_answer_validation,
                },
            }
        )

    @staticmethod
    def _issue_text(issue: Any) -> str:
        try:
            if hasattr(issue, "content"):
                return str(issue.content)
            if isinstance(issue, str):
                return issue
            return str(issue)
        except Exception:
            return "[issue conversion failed]"

    @classmethod
    def _extract_validation_fields(cls, result: Any) -> tuple[bool, list[str], str]:
        """Return (approved, issues, method). Raises AttributeError/ValueError/TypeError on a malformed result."""
        is_valid = bool(result.is_valid) if hasattr(result, "is_valid") else False
        action = str(result.action) if hasattr(result, "action") else ""
        approved = is_valid and action == "approve"

        raw_issues = result.issues if hasattr(result, "issues") else ()
        issues = [cls._issue_text(issue) for issue in raw_issues or ()]

        method = str(result.validation_method) if hasattr(result, "validation_method") else "cascade"
        return approved, issues, method

    async def _validation_status(
        self,
        request: OrchestrationRequest,
        answer: str,
        evidence: EvidenceBundle,
    ) -> ValidationStatus:
        documents = [
            {"content": item.content, "source": item.source, "document_id": item.document_id, "page": item.page}
            for item in evidence.items
        ]
        citations = [
            {"document_id": item.document_id, "source": item.source, "page": item.page} for item in evidence.items
        ]
        try:
            result = await self._validator(request.question, answer, documents, citations)
        except Exception as exc:
            return ValidationStatus(
                state="degraded",
                approved=False,
                method="exception",
                issues=(f"validation exception: {type(exc).__name__}",),
            )

        try:
            approved, issues, method = self._extract_validation_fields(result)
        except (AttributeError, ValueError, TypeError) as exc:
            return ValidationStatus(
                state="degraded",
                approved=False,
                method="extraction_error",
                issues=(f"Failed to extract validation result: {exc}",),
            )

        return ValidationStatus(
            state="validated" if approved else "rejected",
            approved=approved,
            method=method,
            issues=tuple(issues),
        )


async def _validate(query: str, answer: str, documents: list[dict[str, Any]], citations: list[dict[str, Any]]) -> Any:
    from app.agents.verifier.validation.public import validate_answer

    return await validate_answer(query, answer, documents, citations)


def _ground(
    answer: str,
    evidence: EvidenceBundle,
    tool_results: tuple[ToolResult, ...] = (),
) -> tuple[str, dict[str, Any]]:
    """Hedge sentences nothing supports -- where support includes a citable tool result.

    Measured before this: "CVE-2021-44228 的 CVSS 评分为 10.0" was hedged as
    "基于当前可用证据，..." because only retrieved evidence counted, and the
    score came from the CVE lookup. And an answer built from tools alone had
    no evidence at all, so grounding switched itself off and checked nothing.
    """
    from app.agents.synthesizer.citations import citable_tool_results
    from app.services.retrieval.citation_grounding import apply_sentence_grounding

    support = [item.content for item in evidence.items]
    support.extend(result.summary for result in citable_tool_results(tool_results))
    return apply_sentence_grounding(answer, support)


def _sanitize(answer: str) -> tuple[str, dict[str, Any]]:
    from app.services.answer_safety import sanitize_answer

    return sanitize_answer(answer)


def _quality_report(
    validation: ValidationStatus,
    grounding: dict[str, Any],
    policy: ExecutionPolicy,
) -> OrchestratedQualityReport | None:
    if not policy.require_quality_report:
        return None
    support = float(grounding.get("support_ratio", 0.0) or 0.0)
    score = support if validation.approved else 0.0
    return OrchestratedQualityReport(
        score=score,
        level="high" if score >= 0.8 else "low",
        details={"validation_state": validation.state, "grounding_support_ratio": support},
    )
