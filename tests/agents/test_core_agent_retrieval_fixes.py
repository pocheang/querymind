"""The 2026-09-23 core-agent review: retry query, tokenizer, planner limits, source keywords.

Each was reproduced before it was fixed; the retrieval-metric half of the
tokenizer and retry fixes is in tests/evaluation/test_mixed_script_queries.py.
"""

from __future__ import annotations

import asyncio

import pytest

from app.agents.knowledge.service import KnowledgeAgentService
from app.agents.planner.service import PlannerAgentService
from app.agents.verifier.service import _retry_query
from app.core.config import get_settings
from app.domain.contracts import RouteDecision
from app.domain.workflow import RouterDecision
from app.orchestration.request import OrchestrationRequest
from app.retrievers.bm25_retriever import TOKEN_PATTERN, tokenize_chinese_aware

# --- the tokenizer segments Chinese however much English is beside it ----------


@pytest.mark.parametrize(
    ("text", "word"),
    [
        # 19% and 17% CJK: under the old threshold, so neither word existed.
        ("Kubernetes 的 pod affinity 怎么配置", "配置"),
        ("PostgreSQL connection pool 超时怎么办", "超时"),
    ],
)
def test_a_mixed_question_keeps_its_chinese_words(text: str, word: str):
    assert word in tokenize_chinese_aware(text)


@pytest.mark.parametrize("text", ["how quickly is the on-call engineer paged", "VPN access for remote staff"])
def test_english_text_tokenizes_exactly_as_before(text: str):
    # Text with no CJK takes the path it always took.
    assert tokenize_chinese_aware(text) == TOKEN_PATTERN.findall(text.lower())


# --- the verifier's retry query --------------------------------------------------


def test_a_retry_query_adds_no_language_of_its_own():
    question = "年假有多少天"
    diagnostics = ("3 sentences contradicted", "answer factual support is below threshold")

    # Was: question + "\nRetrieve additional primary evidence for: unsupported claims."
    assert _retry_query(question, "年假一共十五天。", diagnostics) == question


def test_a_claim_from_the_answer_is_what_the_retry_adds():
    answer = "年假一共十五天。结转需经理审批。"
    retry = _retry_query("年假有多少天", answer, ("结转需经理审批", "Citation number 2 not in source"))

    assert retry == "年假有多少天\n结转需经理审批"


def test_the_retry_query_is_bounded():
    claims = tuple(f"claim number {i} " + "x" * 400 for i in range(6))
    answer = " ".join(claims)

    retry = _retry_query("q", answer, claims)
    lines = retry.split("\n")

    assert len(lines) == 1 + 3  # the question and at most three claims
    assert all(len(line) <= 200 for line in lines[1:])
    assert len(retry) <= 1_000


# --- the planner's fallback plan cannot fail the checks it is the fallback for ---

_VECTOR = RouteDecision(
    intent="knowledge_retrieval",
    route="vector",
    confidence=0.9,
    requires_plan=False,
    allowed_capabilities=frozenset({"rag"}),
    reason="test",
)
_REACT = RouteDecision(
    intent="tool_call",
    route="react",
    confidence=0.9,
    requires_plan=True,
    allowed_capabilities=frozenset({"rag", "tool"}),
    reason="test",
)


@pytest.mark.parametrize(
    ("field", "value", "route", "budget_field"),
    [
        # Both values are legal for their settings, and each used to raise
        # PlanLimitError out of plan() -- failing every question, or every tool one.
        ("planner_max_retrieval_budget", 1, _VECTOR, "max_retrievals"),
        ("planner_max_tool_budget", 0, _REACT, "max_tool_calls"),
    ],
)
def test_a_limit_clamps_the_direct_plan_instead_of_failing_it(field, value, route, budget_field):
    settings = get_settings().model_copy(update={field: value})
    request = OrchestrationRequest(question="我们的数据保留政策是什么？")

    plan = asyncio.run(PlannerAgentService(settings=settings).plan(request, route))

    assert len(plan.tasks) == 1
    assert getattr(plan.tasks[0].budget, budget_field) == value


# --- source keywords match as words ---------------------------------------------

_ROUTE = RouterDecision(
    intent="knowledge_retrieval",
    complexity="simple",
    completeness="complete",
    next_stage="knowledge",
    confidence=0.9,
    reason="test",
)


def _sources(question: str) -> list[str]:
    strategy = asyncio.run(KnowledgeAgentService().decide(OrchestrationRequest(question=question), _ROUTE, None))
    return [source.source for source in strategy.sources]


@pytest.mark.parametrize(
    "question",
    [
        "How do I configure SSO?",  # "figure"
        "Is the build stable, and is anything notable?",  # "table"
        "Where is the project charter?",  # "chart"
        "Summarize the second paragraph of the onboarding guide",  # "graph"
        "Is the photograph policy in the handbook?",  # "graph"
    ],
)
def test_a_keyword_inside_another_word_selects_nothing_extra(question: str):
    assert _sources(question) == ["vector", "bm25"]


@pytest.mark.parametrize(
    ("question", "source"),
    [
        ("Show the charts and tables in the Q3 report", "multimodal"),  # plurals still match
        ("这个chart里的数据是什么", "multimodal"),  # a Latin word against CJK: not `\b`
        ("What are the dependencies of the billing service?", "graph"),
        ("结算和开票之间是什么关系", "graph"),  # Chinese stays a substring match
    ],
)
def test_a_real_keyword_still_selects_its_source(question: str, source: str):
    assert source in _sources(question)
