"""The analytics dashboard must be fed by the query path.

`RetrievalLogger.log_retrieval` had **no caller anywhere in `app/`** until
2026-09-09 -- the only occurrence in the whole tree was its own `def`. So
`/app/analytics` reported 0 queries, 0% success and 0ms forever, both export
buttons produced an empty file, and the top bar's metrics strip stayed
permanently hidden behind the "render nothing until there are samples" guard
that CLAUDE.md describes at length as a considered design. Found by running
three real queries and reading the dashboard.

The other half is what the row may contain. `RetrievalLog.question` held the
raw text and `export_logs` writes rows to a downloadable CSV, so wiring it
unchanged would have built exactly the store `question_ref()` exists to prevent
-- and nothing in the dashboard ever read that field.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

APP = Path(__file__).resolve().parents[2] / "app"


@pytest.fixture(autouse=True)
def _fresh_logger():
    """A logger of this test's own: the real one is a process-wide singleton."""

    from app.services.retrieval.logger import RetrievalLogger

    previous = RetrievalLogger._instance
    RetrievalLogger._instance = RetrievalLogger()
    try:
        yield RetrievalLogger.get_instance()
    finally:
        RetrievalLogger._instance = previous


def _result(scores: list[float | None], route: str = "vector", agent_class: str = "general"):
    return SimpleNamespace(
        contexts=tuple(SimpleNamespace(score=score, source=f"doc-{i}.md") for i, score in enumerate(scores)),
        route=SimpleNamespace(route=route, agent_class=agent_class),
        # The key `summarize_workflow_execution` actually emits, with a real
        # `EventStage` name. A fixture that invents either would let the builder
        # read nothing and still pass.
        execution_metadata={"workflow_diagnostics": {"stage_latency_ms": {"knowledge": 120}}},
    )


def test_a_query_reaches_the_dashboard(_fresh_logger):
    from app.api.routes.internal.pipeline_contract import record_query_analytics

    record_query_analytics("反向传播是什么", _result([0.9, 0.6, 0.2]), total_ms=1500.0)

    overview = _fresh_logger.get_overview()
    assert overview.total_queries == 1, "the dashboard's producer did not produce"


def test_the_row_carries_a_digest_and_never_the_question(_fresh_logger):
    from app.api.routes.internal.pipeline_contract import record_query_analytics
    from app.services.retrieval.logger import RetrievalLog

    question = "我的团队在深圳办公"
    record_query_analytics(question, _result([0.9]), total_ms=10.0)

    assert "question" not in RetrievalLog.model_fields, "the raw-text field is back"
    assert "question_ref" in RetrievalLog.model_fields

    exported = _fresh_logger.export_logs("csv")
    assert question not in exported, "the question text reached an exportable row"
    assert "question_ref" in exported


def test_the_measurements_are_the_ones_taken(_fresh_logger):
    """Scores and counts come from the result, not from plausible defaults."""

    from app.api.routes.internal.pipeline_contract import EFFECTIVE_HIT_SCORE, record_query_analytics

    # One context deliberately carries no score: a missing score is not a zero.
    record_query_analytics("q", _result([0.9, 0.55, 0.1, None]), total_ms=2000.0)

    row = _fresh_logger._logs[-1]
    assert row.retrieved_count == 4
    assert row.top_scores == [0.9, 0.55, 0.1]
    assert row.effective_hit_count == sum(1 for s in (0.9, 0.55, 0.1) if s >= EFFECTIVE_HIT_SCORE)
    assert row.total_time_ms == 2000.0
    assert row.retrieval_time_ms == 120.0
    assert row.route == "vector"
    assert row.has_result is True


def test_a_broken_counter_does_not_lose_an_answer(_fresh_logger, monkeypatch):
    """Analytics is a by-product of answering and must never be able to fail it."""

    from app.api.routes.internal import pipeline_contract

    record_query_analytics = pipeline_contract.record_query_analytics

    # A result shaped wrongly enough to raise anywhere inside the builder.
    record_query_analytics("q", SimpleNamespace(contexts=object(), route=None), total_ms=1.0)

    assert _fresh_logger.get_overview().total_queries == 0


def test_the_producer_is_called_from_the_query_path():
    """A builder nothing calls is the defect this whole file is about."""

    source = (APP / "api" / "routes" / "public" / "query.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    called = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}

    assert "record_query_analytics" in called


def test_the_timing_key_is_the_one_the_diagnostics_emit():
    """Pinned against the producer, not against this test's own fixture.

    `stage_latency_ms` is what `summarize_workflow_execution` writes. Reading any
    other name yields 0 forever, which the dashboard displays as a fast
    retrieval -- the same "reports something other than what ran" this file is
    about, one key deep.
    """

    from typing import get_args

    from app.domain.events import EventStage

    diagnostics_source = (APP / "services" / "observability" / "workflow_diagnostics.py").read_text(encoding="utf-8")
    contract_source = (APP / "api" / "routes" / "internal" / "pipeline_contract.py").read_text(encoding="utf-8")

    assert '"stage_latency_ms": dict(stage_latency)' in diagnostics_source
    assert 'diagnostics.get("stage_latency_ms")' in contract_source
    assert "knowledge" in get_args(EventStage)


def test_no_readerless_field_came_back():
    """`filtered_docs_count` had no reader and no honest source to fill it."""

    from app.services.retrieval.logger import RetrievalLog

    assert "filtered_docs_count" not in RetrievalLog.model_fields
