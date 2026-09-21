"""Decide whether a full-pipeline retrieval measurement is worth taking.

`scripts/eval_retrieval.py` measures BM25 alone and runs anywhere, which is what
lets it be asserted in CI. The parts of retrieval that decide *precision* --
vector fusion and the cross-encoder reranker -- are deliberately not in it,
because both fail silently:

* `_load_cross_encoder` opens the reranker with `local_files_only=True`, so a
  machine without it downloaded gets `None` and reranking degrades to
  `lexical_rerank`.
* The local embedding model loads the same way, and the fallback is
  `LocalHashEmbeddings` -- deterministic blake2b buckets, not a semantic model,
  so vector search matches on little more than exact overlap.

Neither raises. From outside, a degraded stack answers every query and publishes
a number, and that number describes the fallback rather than the thing whose
name is on the report. CLAUDE.md's standing rule is that a green metric
measuring the wrong thing is worse than no metric, so this module exists to
**refuse** rather than to warn: a run that cannot measure what it claims to
measure does not produce a number at all.

**It asks `effective_model_configuration()` rather than deciding for itself.**
That function is already the one place that knows the difference between "a
model is configured" and "a model is on this machine", and it is what the admin
console reports. A second implementation here would be a second answer to the
same question, and the two would disagree on exactly the day it mattered.

**Only the components that change a retrieval number are required.** A refusal
for a missing chat model or an absent Tesseract would be a refusal for a reason
that has nothing to do with the measurement, which teaches people to pass
whatever flag switches the check off. `tests/evaluation/test_full_pipeline_preflight.py`
pins both directions -- that a degraded reranker refuses, and that an
unavailable OCR does not.
"""

from __future__ import annotations

from dataclasses import dataclass

# The components whose degradation changes a retrieval number, and nothing else.
# `chat`, `nli`, `ocr` and `vision` are all absent on purpose.
REQUIRED_COMPONENTS: tuple[str, ...] = ("embedding", "reranker")

# `active` is the only status that measures what the report will claim.
# `degraded` is the dangerous one -- configured, running, and not doing what its
# name implies -- and `disabled` is a deliberate choice that still makes the
# number mean something other than it says.
ACCEPTABLE_STATUS = "active"


@dataclass(frozen=True)
class Refusal:
    """One reason this measurement would not have measured what it claims."""

    component: str
    status: str
    configured: str
    detail: str

    def render(self) -> str:
        return f"  {self.component}: {self.status} ({self.configured})\n    {self.detail}"


def model_refusals() -> list[Refusal]:
    """Every required component that is not doing its job, in pipeline order."""

    from app.services.models.effective import effective_model_configuration

    by_name = {component.component: component for component in effective_model_configuration()}
    refusals: list[Refusal] = []
    for name in REQUIRED_COMPONENTS:
        component = by_name.get(name)
        if component is None:
            # A required component the reporter does not know about is a bug in
            # one of the two lists, and guessing which is how a guard quietly
            # stops guarding. Refusing names it.
            refusals.append(
                Refusal(
                    component=name,
                    status="unknown",
                    configured="",
                    detail=(
                        f"'{name}' is required here but effective_model_configuration() does not "
                        "report it. One of the two lists is stale; this run cannot say what ran."
                    ),
                )
            )
            continue
        if component.status != ACCEPTABLE_STATUS:
            refusals.append(
                Refusal(
                    component=component.component,
                    status=component.status,
                    configured=component.configured,
                    detail=component.detail,
                )
            )
    return refusals


def vector_store_refusal(scope, probe_query: str) -> Refusal | None:
    """Refuse when the vector half of a hybrid search would contribute nothing.

    An empty Chroma directory is not an error anywhere on the request path -- a
    user with no documents is an ordinary state -- so a hybrid run against one
    succeeds and reports BM25 with extra steps under a name that says otherwise.
    That is the same silent-fallback shape as the two models above, reached
    through the data rather than through a loader.

    The probe is a real `similarity_search` through the scope the measurement
    will use, not a collection count: a store holding another tenant's chunks is
    empty *for this run*, and a count cannot tell the two apart.
    """

    from app.retrievers.stores.vector import OwnerScope, similarity_search

    owner = OwnerScope.from_access_scope(scope)
    try:
        hits = similarity_search(
            probe_query,
            k=1,
            allowed_sources=list(scope.allowed_sources),
            owner=owner,
        )
    except Exception as exc:  # noqa: BLE001 - any failure here means no measurement
        return Refusal(
            component="vector store",
            status="unavailable",
            configured=str(getattr(exc, "args", [""])[0] if getattr(exc, "args", None) else exc),
            detail=(
                "The vector store could not be searched, so a hybrid measurement would be "
                "BM25 alone reported under another name."
            ),
        )
    if not hits:
        return Refusal(
            component="vector store",
            status="empty",
            configured="0 chunks in scope",
            detail=(
                "No chunk in this evaluation's scope is in the vector store, so vector search "
                "contributes nothing and the result would be BM25 with extra steps. Ingest the "
                "corpus for this tenant before measuring; note that switching the embedding "
                "model dimension-locks a Chroma collection and needs a reindex."
            ),
        )
    return None


def render_refusals(refusals: list[Refusal]) -> str:
    """The message a refusing run prints, phrased so the remedy is the next line."""

    lines = [
        "REFUSING to measure: this stack would not measure what this report names.",
        "",
    ]
    lines.extend(refusal.render() for refusal in refusals)
    lines.extend(
        [
            "",
            "Nothing was measured, on purpose. A degraded stack answers every query and",
            "publishes a number describing the fallback rather than the reranker or the",
            "embedding model, and that number is indistinguishable from a healthy one.",
            "Fix the components above, or use `scripts/eval_retrieval.py`, which measures",
            "BM25 only and says so.",
        ]
    )
    return "\n".join(lines)


__all__ = [
    "ACCEPTABLE_STATUS",
    "REQUIRED_COMPONENTS",
    "Refusal",
    "model_refusals",
    "render_refusals",
    "vector_store_refusal",
]
