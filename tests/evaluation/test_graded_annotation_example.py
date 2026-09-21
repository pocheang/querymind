"""The graded-annotation example has to keep working, or it teaches a format
that no longer loads.

An example file is documentation that can rot silently: it is not imported, not
executed, and a source identifier typed wrong in it scores 0.0 forever -- which
looks exactly like a retrieval failure. So it is loaded here through the same
`load_queries` a real run uses, and every source it names is checked against the
corpus.

The assertion that carries the point is
`test_graded_judgements_raise_the_ceiling_the_shipped_set_cannot`: 0.2 is a fact
about the annotations, and this is the file that demonstrates what changes it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.evaluation.metrics import _grades, precision_ceiling_at_k
from app.evaluation.retrieval_eval import (
    eval_scope,
    load_corpus_sources,
    load_queries,
    measure,
)

TRACKED_CORPUS = Path("config/eval/retrieval_corpus.jsonl")
EXAMPLE = Path("config/eval/retrieval_queries.graded.example.json")

# The scale the file documents. Stated here as well so a grade of 7 appearing in
# the example fails rather than quietly meaning "very relevant" to nDCG and
# nothing to a reader.
DOCUMENTED_GRADES = {0.0, 1.0, 2.0, 3.0}


def example_queries():
    return load_queries(EXAMPLE)


def test_the_example_loads_through_the_same_path_a_real_run_uses():
    """Not `json.load` -- `load_queries`, which is what would actually read it.

    The `_readme` and `_note` keys are the reason this is worth asserting: JSON
    has no comments, so the explanation travels inside the file, and it only
    works while the model ignores keys it does not know.
    """

    queries = example_queries()

    assert [query.id for query in queries] == ["q-ex-01", "q-ex-02", "q-ex-03", "q-ex-04"]


def test_every_source_the_example_names_exists_in_the_corpus():
    """A mistyped source identifier scores 0.0 forever and reads as a broken
    retriever. This is the same check the shipped query set gets, applied to the
    file people will copy."""

    sources = set(load_corpus_sources(TRACKED_CORPUS))
    named = {source for query in example_queries() for source in query.graded_relevance()}

    assert named <= sources, f"named but absent from the corpus: {sorted(named - sources)}"


def test_the_example_only_uses_the_scale_it_documents():
    grades = {grade for query in example_queries() for grade in query.graded_relevance().values()}

    assert grades <= DOCUMENTED_GRADES


def test_graded_judgements_raise_the_ceiling_the_shipped_set_cannot():
    """The whole argument, as an assertion.

    q-ex-01 has three relevant documents, so its P@5 ceiling is 3/5. q-ex-02 is
    the same three documents under a narrower question, two of them judged 0, and
    its ceiling is back to 1/5 -- which is what makes the pair worth shipping:
    the ceiling follows the judgements, and a narrow question having a low one is
    correct rather than a problem to annotate away.
    """

    by_id = {query.id: query for query in example_queries()}

    assert precision_ceiling_at_k(by_id["q-ex-01"].graded_relevance(), 5) == pytest.approx(0.6)
    assert precision_ceiling_at_k(by_id["q-ex-02"].graded_relevance(), 5) == pytest.approx(0.2)


def test_a_zero_grade_is_recorded_and_does_not_count():
    """Both halves, and they are at different layers -- which is the design.

    `graded_relevance()` **keeps** the zero: it is the record of a judgement, and
    a query object that dropped it could not tell a reader that the document was
    considered. `_grades()`, inside the metrics, is what drops anything at or
    below zero, so no metric ever counts it.

    The first version of this test asserted `graded_relevance()` dropped it and
    failed, which was the test being wrong rather than the code. Worth keeping as
    two assertions rather than one: collapsing the layers is a change somebody
    would make while tidying, and it would silently turn every judged-irrelevant
    document into an unjudged one.
    """

    by_id = {query.id: query for query in example_queries()}
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    written = {row["id"]: row.get("relevance", {}) for row in raw["queries"]}

    assert 0 in written["q-ex-02"].values(), "the file should record a judged-irrelevant document"
    assert 0.0 in by_id["q-ex-02"].graded_relevance().values(), "the record survives into the query object"
    assert all(grade > 0 for grade in _grades(by_id["q-ex-02"].graded_relevance()).values())
    # And the consequence that matters: it is not in the ideal ranking either, so
    # it cannot depress nDCG for a retriever that correctly did not return it.
    assert precision_ceiling_at_k(by_id["q-ex-02"].graded_relevance(), 5) == pytest.approx(0.2)


def test_the_ungraded_form_still_works_beside_the_graded_one():
    """q-ex-04 is written the old way on purpose: a query set does not have to be
    migrated all at once, and this is what that claim rests on."""

    by_id = {query.id: query for query in example_queries()}

    assert by_id["q-ex-04"].relevance == {}
    assert by_id["q-ex-04"].graded_relevance() == {"eval://corpus/incident_severity.md": 1.0}


@pytest.mark.asyncio
async def test_the_example_measures_end_to_end(eval_corpus: None):
    """Parsing is not the same as being usable. This runs it through the real
    orchestrator, because the failure worth catching is a query set that loads
    and then produces nothing.

    The aggregates are asserted as bounds rather than values: these queries are
    illustrative, nobody should tune retrieval to them, and pinning their ranks
    would invite exactly that.
    """

    queries = example_queries()
    score = await measure(queries, eval_scope(load_corpus_sources(TRACKED_CORPUS)))

    assert score.precision_ceiling_at_5 > 0.2, "the example exists to show a ceiling above the shipped one"
    assert score.precision_at_5 <= score.precision_ceiling_at_5 + 1e-9
    assert 0.0 <= score.ndcg_at_5 <= 1.0
    assert score.recall_at_5 > 0.0, "a query set that retrieves nothing is not a usable example"
