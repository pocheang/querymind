"""The preflight that decides whether a full-pipeline number is worth taking.

Mostly negative, and deliberately so. A guard that refuses everything is
indistinguishable from a guard that works right up until somebody has a real
stack, and at that point the fix is to delete it. So the assertions come in
pairs: this refuses, and *this* does not.

The one that matters most is
`test_a_component_this_measurement_does_not_use_never_refuses`. Refusing over an
absent Tesseract would be refusing for a reason unrelated to retrieval, and the
remedy anybody would reach for is the flag that switches the check off.
"""

from __future__ import annotations

import pytest

from app.evaluation import preflight
from app.evaluation.preflight import (
    ACCEPTABLE_STATUS,
    REQUIRED_COMPONENTS,
    Refusal,
    model_refusals,
    render_refusals,
    vector_store_refusal,
)
from app.services.models.effective import EffectiveComponent


def component(name: str, status: str = "active") -> EffectiveComponent:
    return EffectiveComponent(
        component=name,
        status=status,  # type: ignore[arg-type]
        configured=f"{name}-model",
        detail=f"{name} is {status}",
        source="test",
    )


def stack(monkeypatch: pytest.MonkeyPatch, *components: EffectiveComponent) -> None:
    """Replace the reporter, not the preflight's reading of it.

    Stubbing `model_refusals` would test a transcription of the rule rather than
    the rule, which is the defect CLAUDE.md records for the regex suite.
    """

    monkeypatch.setattr(
        "app.services.models.effective.effective_model_configuration",
        lambda: list(components),
    )


HEALTHY = ("ocr", "image_caption", "embedding", "reranker", "chat", "validation_nli")


def test_a_healthy_stack_is_measured(monkeypatch: pytest.MonkeyPatch):
    """The direction a guard loses first."""

    stack(monkeypatch, *(component(name) for name in HEALTHY))

    assert model_refusals() == []


def test_a_component_this_measurement_does_not_use_never_refuses(monkeypatch: pytest.MonkeyPatch):
    """OCR, captioning, the chat model and the NLI cross-encoder are all absent
    or degraded on a machine that has the two models retrieval needs, and none of
    them changes a retrieval number.

    This is the assertion that keeps the check usable. A refusal naming
    Tesseract, on a run measuring BM25 and vector fusion, reads as the guard
    being broken -- and is answered by switching the guard off.
    """

    stack(
        monkeypatch,
        component("ocr", "unavailable"),
        component("image_caption", "disabled"),
        component("embedding"),
        component("reranker"),
        component("chat", "degraded"),
        component("validation_nli", "degraded"),
    )

    assert model_refusals() == []


@pytest.mark.parametrize("required", REQUIRED_COMPONENTS)
@pytest.mark.parametrize("status", ["degraded", "disabled", "unavailable"])
def test_every_required_component_refuses_in_every_state_that_is_not_active(
    monkeypatch: pytest.MonkeyPatch, required: str, status: str
):
    """Parametrized over the list rather than spelled out per component, so a
    component added to `REQUIRED_COMPONENTS` is covered the day it is added.

    `disabled` refuses as loudly as `degraded`. Turning the reranker off is a
    legitimate configuration -- it just is not the thing this report names, and a
    number measuring unranked fusion is not comparable with one that is not.
    """

    stack(monkeypatch, *(component(name, status if name == required else ACCEPTABLE_STATUS) for name in HEALTHY))

    refusals = model_refusals()

    assert [refusal.component for refusal in refusals] == [required]
    assert refusals[0].status == status


def test_a_required_component_the_reporter_does_not_know_refuses(monkeypatch: pytest.MonkeyPatch):
    """The two lists can drift, and the drift is silent in the dangerous
    direction: a required name that `effective_model_configuration()` stops
    reporting would otherwise be read as "nothing to refuse about"."""

    stack(monkeypatch, component("chat"))

    refusals = model_refusals()

    assert {refusal.component for refusal in refusals} == set(REQUIRED_COMPONENTS)
    assert all(refusal.status == "unknown" for refusal in refusals)


def test_the_refusal_message_names_the_component_and_the_way_out():
    """A refusal nobody can act on is a failure that gets worked around."""

    rendered = render_refusals([Refusal("reranker", "degraded", "bge-reranker", "not available locally")])

    assert "reranker" in rendered
    assert "degraded" in rendered
    assert "not available locally" in rendered
    # The alternative that still produces a number, so the answer to a refusal is
    # not "give up" or "delete the check".
    assert "eval_retrieval.py" in rendered
    assert "Nothing was measured" in rendered


class _Scope:
    tenant_id = "eval-tenant"
    user_id = "eval-user"
    allowed_sources = frozenset({"eval://corpus/a.md"})


def test_an_empty_vector_store_refuses(monkeypatch: pytest.MonkeyPatch):
    """An empty Chroma is not an error on the request path -- a user with no
    documents is ordinary -- so a hybrid run against one succeeds and reports
    BM25 under a name that says otherwise."""

    monkeypatch.setattr("app.retrievers.stores.vector.similarity_search", lambda *a, **k: [])

    refusal = vector_store_refusal(_Scope(), "probe")

    assert refusal is not None
    assert refusal.status == "empty"


def test_a_vector_store_that_raises_refuses(monkeypatch: pytest.MonkeyPatch):
    """`similarity_search` fails closed on a missing source filter, and a run
    that cannot search the store cannot measure it either."""

    def boom(*_args, **_kwargs):
        raise RuntimeError("collection not found")

    monkeypatch.setattr("app.retrievers.stores.vector.similarity_search", boom)

    refusal = vector_store_refusal(_Scope(), "probe")

    assert refusal is not None
    assert refusal.status == "unavailable"


def test_a_populated_vector_store_does_not_refuse(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.retrievers.stores.vector.similarity_search", lambda *a, **k: [{"source": "a"}])

    assert vector_store_refusal(_Scope(), "probe") is None


def test_the_required_set_is_only_what_changes_a_retrieval_number():
    """Stated as an assertion because the temptation is to add components here
    when one of them breaks something else. Every name added is a new way for
    this command to refuse for a reason unrelated to what it measures."""

    assert set(REQUIRED_COMPONENTS) == {"embedding", "reranker"}
    assert preflight.ACCEPTABLE_STATUS == "active"
