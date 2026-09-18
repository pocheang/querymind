"""Evaluation metrics for retrieval systems.

**Relevance may be binary or graded.** Every function here takes `relevant` as
either a `set` of relevant sources -- the original form, still what most callers
pass -- or a `dict` mapping a source to a grade, where 0 means not relevant and a
larger number means more relevant. `_grades` is the one place that reconciles the
two, so a caller upgrading to graded judgements changes nothing else.

Grading exists because the shipped evaluation corpus has exactly one relevant
document per query, which caps `precision_at_k` at `1/k` and leaves it unable to
say anything about *ordering*. See `precision_ceiling_at_k`, which computes that
cap from the annotations rather than leaving a reader to infer it from a low
number.
"""

from math import log2

Relevance = set[str] | dict[str, int | float]


def _grades(relevant: Relevance) -> dict[str, float]:
    """One reading of `relevant`, whether it arrived as a set or a graded map.

    A set means every member has grade 1. A map keeps its grades, dropping any
    entry graded 0 or below so that "annotated as irrelevant" and "not annotated"
    are the same thing to every metric -- which is what lets a corpus record a
    judged-but-unhelpful document without it counting toward recall.
    """

    if isinstance(relevant, dict):
        return {source: float(grade) for source, grade in relevant.items() if float(grade) > 0}
    return dict.fromkeys(relevant, 1.0)


def precision_at_k(retrieved: list[str], relevant: Relevance, k: int = 5) -> float:
    """Calculate Precision@K.

    **The denominator is always k**, which is what Precision@K means -- so a query
    with fewer than k relevant documents cannot reach 1.0. That is a property of
    the metric and of the annotations, not a retrieval result; `precision_ceiling_at_k`
    reports the reachable maximum so the two are never confused.

    Args:
        retrieved: List of retrieved document IDs (ordered by relevance)
        relevant: Relevant document IDs, as a set or a source -> grade map
        k: Number of top results to consider

    Returns:
        Precision@K score (0.0 to 1.0)
    """
    if not retrieved or k == 0:
        return 0.0

    grades = _grades(relevant)
    relevant_retrieved = sum(1 for doc in retrieved[:k] if doc in grades)
    return relevant_retrieved / k


def precision_ceiling_at_k(relevant: Relevance, k: int = 5) -> float:
    """The largest Precision@K these annotations allow: `min(|relevant|, k) / k`.

    Reported beside the score because a corpus with one relevant document per
    query caps P@5 at 0.2, and 0.2 then reads as a failing number to anyone who
    compares it with a target quoted for a multi-gold corpus. Computing the cap
    from the data makes the comparison impossible to get wrong by accident.
    """

    if k == 0:
        return 0.0
    return min(len(_grades(relevant)), k) / k


def recall_at_k(retrieved: list[str], relevant: Relevance, k: int = 5) -> float:
    """Calculate Recall@K.

    On a single-gold corpus this is the metric with range where Precision@K has
    none: the two differ by exactly a factor of k, so reporting P@5 as a headline
    on such a corpus is reporting recall divided by five.

    Args:
        retrieved: List of retrieved document IDs (ordered by relevance)
        relevant: Relevant document IDs, as a set or a source -> grade map
        k: Number of top results to consider

    Returns:
        Recall@K score (0.0 to 1.0)
    """
    grades = _grades(relevant)
    if not grades:
        return 0.0

    relevant_retrieved = sum(1 for doc in retrieved[:k] if doc in grades)
    return relevant_retrieved / len(grades)


def f1_at_k(retrieved: list[str], relevant: set[str], k: int = 5) -> float:
    """Calculate F1@K.

    Args:
        retrieved: List of retrieved document IDs (ordered by relevance)
        relevant: Set of relevant document IDs
        k: Number of top results to consider

    Returns:
        F1@K score (0.0 to 1.0)
    """
    precision = precision_at_k(retrieved, relevant, k)
    recall = recall_at_k(retrieved, relevant, k)

    if precision + recall == 0:
        return 0.0

    return 2 * (precision * recall) / (precision + recall)


def reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float:
    """Calculate Reciprocal Rank.

    Args:
        retrieved: List of retrieved document IDs (ordered by relevance)
        relevant: Set of relevant document IDs

    Returns:
        Reciprocal rank (0.0 to 1.0)
    """
    for i, doc in enumerate(retrieved, 1):
        if doc in relevant:
            return 1.0 / i
    return 0.0


def mean_reciprocal_rank(results: list[tuple[list[str], set[str]]]) -> float:
    """Calculate Mean Reciprocal Rank across multiple queries.

    Args:
        results: List of (retrieved, relevant) tuples

    Returns:
        Mean reciprocal rank (0.0 to 1.0)
    """
    if not results:
        return 0.0

    rr_scores = [reciprocal_rank(retrieved, relevant) for retrieved, relevant in results]
    return sum(rr_scores) / len(rr_scores)


def _dcg(gains: list[float]) -> float:
    """Discounted cumulative gain, exponential form: sum (2^g - 1) / log2(i + 1)."""

    return sum((2.0**gain - 1.0) / log2(position + 1) for position, gain in enumerate(gains, start=1))


def ndcg_at_k(retrieved: list[str], relevant: Relevance, k: int = 5) -> float:
    """Calculate Normalized Discounted Cumulative Gain@K.

    **The ideal ranking comes from the full relevance set, not from what was
    retrieved.** The previous implementation built it by sorting the *retrieved*
    labels, so a relevant document that was missed entirely did not appear in the
    denominator -- retrieving one of three relevant documents at rank 1 scored a
    perfect 1.0. Measured on the shipped code before this change:

        3 relevant, 1 retrieved at rank 1  ->  reported 1.0, correct value 0.4693
        1 relevant, retrieved at rank 2    ->  reported 0.4871, correct value 0.6309
        1 relevant, retrieved at rank 1    ->  reported 1.0, correct value 1.0

    Only the third is right, and it is the shape the shipped 16-query corpus is
    almost entirely made of, which is why nothing caught it. A metric that cannot
    report a miss is the failure this repository keeps recording; this one was
    reporting a *perfect score* for one.

    The second error was separate: `ndcg_score(y_true, y_score)` takes true
    relevance and predicted scores, and it was handed a sorted copy of the labels
    as `y_true` and the labels themselves as `y_score`. sklearn is gone rather than
    re-argued -- the direct formula is four lines and the only thing in this
    repository that imported sklearn at all.

    Args:
        retrieved: List of retrieved document IDs (ordered by relevance)
        relevant: Relevant document IDs, as a set or a source -> grade map
        k: Number of top results to consider

    Returns:
        NDCG@K score (0.0 to 1.0)
    """
    grades = _grades(relevant)
    if not retrieved or not grades or k == 0:
        return 0.0

    actual = [grades.get(doc, 0.0) for doc in retrieved[:k]]
    ideal = sorted(grades.values(), reverse=True)[:k]

    ideal_dcg = _dcg(ideal)
    # `<=` rather than `== 0.0`: testing a float for equality is `python:S1244`,
    # and the branch is a genuine ZeroDivisionError guard rather than dead code.
    # `_grades` keeps only grades above zero, but a grade small enough that
    # `2.0 ** grade` rounds to 1.0 makes every term exactly 0.0 -- measured,
    # a grade of 1e-20 survives `_grades` and gives `_dcg([1e-20]) == 0.0`.
    if ideal_dcg <= 0.0:
        return 0.0
    return _dcg(actual) / ideal_dcg


def calculate_all_metrics(retrieved: list[str], relevant: Relevance, k: int = 5) -> dict:
    """Calculate all evaluation metrics for a single query.

    Args:
        retrieved: List of retrieved document IDs (ordered by relevance)
        relevant: Set of relevant document IDs
        k: Number of top results to consider

    Returns:
        Dictionary with all metric scores
    """
    return {
        "precision": precision_at_k(retrieved, relevant, k),
        "recall": recall_at_k(retrieved, relevant, k),
        "f1": f1_at_k(retrieved, relevant, k),
        "reciprocal_rank": reciprocal_rank(retrieved, relevant),
        "ndcg": ndcg_at_k(retrieved, relevant, k),
        # What P@k could have reached on these annotations. Without it a
        # single-gold corpus reports 0.2 and reads as a failure.
        "precision_ceiling": precision_ceiling_at_k(relevant, k),
    }
