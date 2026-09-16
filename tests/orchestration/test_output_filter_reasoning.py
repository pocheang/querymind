"""The reasoning panel is a second piece of model output reaching the reader,
alongside the answer -- and `output_filter` is the one mandatory DLP boundary
neither may skip (see CLAUDE.md: "skipping output DLP is a hole, not a
degradation"). This is the test that proves that actually holds for
`FinalAnswer.reasoning`, not just that the field compiles and passes through.

Fixture secret ("sk-...") matches tests/security/test_streaming_redaction.py's
own planted shape, so a failure here means the same class of leak that file
already guards for the answer channel, now on the reasoning one.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.domain.contracts import EvidenceBundle, FinalAnswer
from app.domain.knowledge import AccessScope
from app.orchestration.langgraph.nodes import WorkflowNodeRuntime
from app.orchestration.policies import ExecutionPolicy
from app.orchestration.request import OrchestrationRequest
from app.orchestration.timeout_control import ExecutionBudget, TimeoutConfig
from app.privacy.service import PrivacyService
from app.services.security.access_scope import DEFAULT_CONTEXT_FIELDS

_PLANTED_SECRET = "sk-abcdefghijklmnopqrstuvwxyz012345"


def _runtime() -> WorkflowNodeRuntime:
    return WorkflowNodeRuntime(
        services=SimpleNamespace(privacy=PrivacyService()),
        policy=ExecutionPolicy(),
        max_verifier_retries=1,
        context_token_budget=2000,
    )


def _scope() -> AccessScope:
    return AccessScope(
        tenant_id="tenant-1",
        user_id="user-1",
        role="viewer",
        allowed_sources=frozenset(),
        allowed_fields=DEFAULT_CONTEXT_FIELDS,
    )


def _discard(_event: object) -> None:
    return None


async def _run_output_filter(*, answer_text: str, reasoning: str | None) -> FinalAnswer:
    evidence = EvidenceBundle(items=())
    state = {
        "request": OrchestrationRequest(question="what leaked?"),
        "final_answer": FinalAnswer(answer=answer_text, reasoning=reasoning, evidence=evidence, evidence_ids=()),
        "evidence_bundle": evidence,
        "permission_scope": _scope(),
        "budget": ExecutionBudget(TimeoutConfig()),
        "reporter": _discard,
    }
    result = await _runtime().output_filter(state)
    return result["final_answer"]


@pytest.mark.asyncio
async def test_a_secret_in_the_reasoning_is_redacted_the_same_as_in_the_answer():
    answer = await _run_output_filter(
        answer_text=f"For reference the key is {_PLANTED_SECRET}.",
        reasoning=f"Let me check the key {_PLANTED_SECRET} against the docs.",
    )

    assert _PLANTED_SECRET not in answer.answer
    assert _PLANTED_SECRET not in (answer.reasoning or "")


@pytest.mark.asyncio
async def test_reasoning_with_no_secret_survives_the_pass_unredacted_in_content():
    answer = await _run_output_filter(
        answer_text="BM25 ranks documents by term frequency.",
        reasoning="The user is asking about BM25, which is a lexical ranking function.",
    )

    assert answer.reasoning == "The user is asking about BM25, which is a lexical ranking function."


@pytest.mark.asyncio
async def test_no_reasoning_stays_none_rather_than_becoming_an_empty_string():
    """None means "the caller never asked to see reasoning" -- collapsing it
    to "" would make that indistinguishable from "asked, and got nothing.\" """
    answer = await _run_output_filter(answer_text="An answer with no reasoning field at all.", reasoning=None)

    assert answer.reasoning is None


@pytest.mark.asyncio
async def test_the_redaction_count_includes_reasoning_findings():
    """`safety.output_dlp.redactions` is the one number an operator has for
    "how much did this stage redact" -- it must not undercount by ignoring an
    entire channel."""
    baseline = await _run_output_filter(answer_text="Nothing sensitive here.", reasoning=None)
    with_secret = await _run_output_filter(
        answer_text="Nothing sensitive here.",
        reasoning=f"Checking {_PLANTED_SECRET} against the record.",
    )

    baseline_count = baseline.safety.get("output_dlp", {}).get("redactions", 0)
    with_secret_count = with_secret.safety.get("output_dlp", {}).get("redactions", 0)
    assert with_secret_count > baseline_count
