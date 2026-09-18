"""Judgements may be graded, and nDCG has to answer for the ones that were missed.

Two things landed together here, and the second is why the first was worth doing.

**The corpus is single-gold, so Precision@5 cannot exceed 0.2.** That is a
property of `min(|relevant|, k) / k`, not a retrieval result -- measured on the
shipped set, P@5 is exactly 0.2, meaning every one of the sixteen queries found
its document inside the top five. Reported alone the number reads as a failure,
and it was being compared against a `>0.85` target quoted for corpora with
several relevant documents per query. `precision_ceiling_at_k` computes the cap
from the judgements so the comparison cannot be made by accident, and the report
leads with recall@5, MRR and nDCG@5, which have range.

**And nDCG -- the metric with range once judgements are graded -- was wrong in
two independent ways.** Both were measured against hand-computed values before
anything was changed:

    3 relevant, 1 retrieved at rank 1  ->  reported 1.0,    correct 0.4693
    1 relevant, retrieved at rank 2    ->  reported 0.4871, correct 0.6309
    1 relevant, retrieved at rank 1    ->  reported 1.0,    correct 1.0

The ideal ranking was built by sorting the *retrieved* labels, so a relevant
document that was never retrieved did not enter the denominator -- the first row
is a **perfect score reported for a two-thirds miss**. Separately,
`ndcg_score(y_true, y_score)` was handed a sorted copy of the labels as `y_true`
and the labels as `y_score`, which is not what those arguments mean.

Only the third row was right, and it is the shape almost every query in the
shipped corpus has, which is why nothing caught it. It is live: `ndcg_at_k`
reaches `POST /api/evaluation/run` through `calculate_all_metrics` and
`app/evaluation/retrieval.py`.

Values here are hand-computed from the definition rather than captured from the
implementation, because a test that records what the code does cannot report that
the code is wrong -- which is exactly the state this file is correcting.
"""

from __future__ import annotations

from math import log2

import pytest

from app.evaluation.metrics import (
    _dcg,
    calculate_all_metrics,
    ndcg_at_k,
    precision_at_k,
    precision_ceiling_at_k,
    recall_at_k,
)

# Imported under another name because pytest tries to COLLECT a class whose name
# starts with Test and warns when it cannot, which is noise in every run that
# imports it. `tests/api/test_evaluation_baselines.py` already does this.
from app.evaluation.models import TestQuery as EvalQuery

FIVE = ["a", "b", "c", "d", "e"]


# --- the two nDCG defects -------------------------------------------------


def test_a_missed_relevant_document_lowers_ndcg():
    """The defect that mattered: 1.0 was reported for retrieving one of three.

    The ideal ranking is three relevant documents at ranks 1-3; retrieving one of
    them at rank 1 earns the first term of that and none of the rest.
    """

    ideal = 1 / log2(2) + 1 / log2(3) + 1 / log2(4)

    assert ndcg_at_k(["a", "x", "y", "z", "w"], {"a", "b", "c"}) == pytest.approx(1 / log2(2) / ideal)
    assert ndcg_at_k(["a", "x", "y", "z", "w"], {"a", "b", "c"}) == pytest.approx(0.4693, abs=1e-4)


def test_rank_two_scores_the_rank_two_discount():
    """The `y_true`/`y_score` mix-up: 0.4871 was reported where 1/log2(3) is right."""

    assert ndcg_at_k(["x", "a", "y", "z", "w"], {"a"}) == pytest.approx(1 / log2(3))
    assert ndcg_at_k(["x", "a", "y", "z", "w"], {"a"}) == pytest.approx(0.6309, abs=1e-4)


def test_the_one_shape_that_was_already_right_still_is():
    """Almost every query in the shipped corpus is this one, which is why the
    other two rows survived."""

    assert ndcg_at_k(["a", "x"], {"a"}) == pytest.approx(1.0)


def test_nothing_relevant_retrieved_scores_zero():
    assert ndcg_at_k(["x", "y"], {"a"}) == 0.0
    assert ndcg_at_k([], {"a"}) == 0.0
    assert ndcg_at_k(["a"], set()) == 0.0


# --- what grading buys ----------------------------------------------------


def test_ndcg_separates_two_rankings_that_recall_cannot():
    """The whole reason to grade: both orderings retrieve everything relevant.

    Recall and precision are identical for the two, so neither can say which
    ranking is better. nDCG can, and that is the range a single-gold binary
    corpus does not have.
    """

    graded = {"a": 3.0, "b": 1.0}
    good, bad = ["a", "b"], ["b", "a"]

    assert recall_at_k(good, graded) == recall_at_k(bad, graded) == 1.0
    assert precision_at_k(good, graded, k=2) == precision_at_k(bad, graded, k=2)

    assert ndcg_at_k(good, graded) == pytest.approx(1.0)
    assert ndcg_at_k(bad, graded) == pytest.approx(0.7098, abs=1e-4)
    assert ndcg_at_k(bad, graded) < ndcg_at_k(good, graded)


def test_a_grade_of_zero_means_judged_and_not_relevant():
    """Different from unjudged only in that it is written down -- and it must not
    count toward recall, or a corpus could raise its own score by annotating
    near-misses."""

    assert recall_at_k(["a", "b"], {"a": 1.0, "b": 0.0}) == 1.0
    assert precision_ceiling_at_k({"a": 1.0, "b": 0.0}) == pytest.approx(0.2)


def test_a_set_still_means_grade_one_everywhere():
    """Every existing caller passes a set; none of them changes."""

    for k in (1, 3, 5):
        assert recall_at_k(FIVE, {"a", "b"}, k) == recall_at_k(FIVE, {"a": 1, "b": 1}, k)
        assert precision_at_k(FIVE, {"a", "b"}, k) == precision_at_k(FIVE, {"a": 1, "b": 1}, k)
        assert ndcg_at_k(FIVE, {"a", "b"}, k) == pytest.approx(ndcg_at_k(FIVE, {"a": 1, "b": 1}, k))


# --- the ceiling ----------------------------------------------------------


@pytest.mark.parametrize(("relevant", "ceiling"), [(1, 0.2), (2, 0.4), (3, 0.6), (5, 1.0), (9, 1.0)])
def test_the_precision_ceiling_is_min_relevant_over_k(relevant, ceiling):
    judgements = {chr(ord("a") + index): 1.0 for index in range(relevant)}

    assert precision_ceiling_at_k(judgements) == pytest.approx(ceiling)


def test_precision_at_five_equals_recall_over_five_on_a_single_gold_query():
    """Why P@5 is not the headline: on this corpus it carries nothing recall does not.

    Asserted rather than described, because the identity is the argument for the
    report's ordering.
    """

    for retrieved in (["a", "x", "y", "z", "w"], ["x", "y", "a", "z", "w"], ["x", "y", "z", "w", "v"]):
        assert precision_at_k(retrieved, {"a"}) == pytest.approx(recall_at_k(retrieved, {"a"}) / 5)


def test_calculate_all_metrics_reports_the_ceiling_beside_the_score():
    """A caller reading `precision` alone has no way to know 0.2 was the maximum."""

    metrics = calculate_all_metrics(["a", "x", "y", "z", "w"], {"a"})

    assert metrics["precision"] == pytest.approx(0.2)
    assert metrics["precision_ceiling"] == pytest.approx(0.2)
    assert metrics["recall"] == pytest.approx(1.0)


# --- the query schema -----------------------------------------------------


def test_expected_docs_alone_still_describes_a_query():
    """Every shipped query is written this way and must keep working untouched."""

    query = EvalQuery(id="q-01", query="x", category="c", expected_docs=["a", "b"])

    assert query.graded_relevance() == {"a": 1.0, "b": 1.0}


def test_grades_win_over_the_list_and_the_list_fills_the_gaps():
    query = EvalQuery(
        id="q-01",
        query="x",
        category="c",
        expected_docs=["a", "b"],
        relevance={"a": 3, "c": 0},
    )

    assert query.graded_relevance() == {"a": 3.0, "b": 1.0, "c": 0.0}


def test_a_query_with_no_judgements_at_all_scores_zero_rather_than_raising():
    """A corpus row that forgot its annotations is a data bug; it must not look
    like a retrieval failure *and* must not crash the run."""

    query = EvalQuery(id="q-01", query="x", category="c")

    assert query.graded_relevance() == {}
    assert ndcg_at_k(FIVE, query.graded_relevance()) == 0.0
    assert recall_at_k(FIVE, query.graded_relevance()) == 0.0


def test_a_grade_too_small_to_survive_the_gain_function_scores_zero_rather_than_dividing_by_it():
    """`ndcg_at_k`'s zero-denominator guard is reachable, which is why it is a
    `<= 0.0` test and not dead code that could be deleted.

    `_grades` keeps only grades above zero, so the obvious reading is that the
    ideal DCG is always positive. It is not: the gain is `2 ** grade - 1`, and a
    grade small enough that `2 ** grade` rounds to 1.0 makes every term exactly
    0.0. Measured, 1e-20 is such a grade. Without the guard this is a
    ZeroDivisionError on what is, in the corpus, a typo in an annotation.
    """

    assert _dcg([1e-20]) == 0.0  # the precondition the guard exists for
    assert ndcg_at_k(["a"], {"a": 1e-20}) == 0.0
