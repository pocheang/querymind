"""A document labelled with the routed specialist's domain ranks a little higher -- and nothing else changes.

The plan put the preference into RRF as an extra "labelled documents" list. The
reranker then re-scores every candidate and sorts by its own score alone
(`app/retrievers/reranker.py`), so that list would have been erased in
production. The preference is applied after reranking instead: a fixed
`DOMAIN_LABEL_BOOST` (default 0.1) on the 0-1 reranked score, which decides close
calls and never overturns a clear one.

The label comes from the document registry at query time. The previous
implementation (`agent_scope.py`) read `metadata["agent"]`, a key nothing wrote,
and would have used it as a filter -- every specialist's scope would have been
empty. See `tests/security/test_domain_label_never_widens_scope.py` for the
authorization half.
"""

from __future__ import annotations

import asyncio
import json
import os

import pytest

from app.agents.knowledge.service import KnowledgeAgentService
from app.domain.contracts import EvidenceItem
from app.domain.knowledge import AccessScope, KnowledgeSourcePlan, KnowledgeStrategy
from app.domain.workflow import RouterDecision
from app.knowledge import orchestrator as orchestrator_module
from app.knowledge.adapters import CallableKnowledgeAdapter
from app.knowledge.fusion import prefer_domain
from app.knowledge.orchestrator import KnowledgeOrchestrator, discard_trace
from app.orchestration.request import OrchestrationRequest, RequestActor, RequestScope
from app.services.documents import domain_labels
from app.services.documents.domain_labels import DomainLabels, load_domain_labels
from app.services.security.access_scope import DEFAULT_CONTEXT_FIELDS


def _item(name: str, score: float) -> EvidenceItem:
    return EvidenceItem(
        item_id=name,
        content=f"content of {name}",
        source=f"/uploads/alice/{name}.md",
        document_id=f"doc-{name}",
        version=1,
        retriever="vector",
        score=score,
    )


LABELS = {"doc-security": "cybersecurity", "doc-ai": "artificial_intelligence"}


def _label_of(item: EvidenceItem) -> str | None:
    return LABELS.get(item.document_id)


# --- the preference itself ----------------------------------------------------


def test_a_labelled_passage_wins_a_close_call():
    items = (_item("general", 0.70), _item("security", 0.62))

    ordered, boosted = prefer_domain(items, "cybersecurity", label_of=_label_of, boost=0.1)

    assert [item.item_id for item in ordered] == ["security", "general"]
    assert boosted == 1


def test_a_labelled_passage_does_not_overturn_a_clear_one():
    items = (_item("general", 0.90), _item("security", 0.62))

    ordered, _ = prefer_domain(items, "cybersecurity", label_of=_label_of, boost=0.1)

    assert [item.item_id for item in ordered] == ["general", "security"]


def test_another_domains_label_earns_nothing():
    items = (_item("general", 0.70), _item("ai", 0.65))

    ordered, boosted = prefer_domain(items, "cybersecurity", label_of=_label_of, boost=0.1)

    assert [item.item_id for item in ordered] == ["general", "ai"]
    assert boosted == 0


def test_nothing_is_added_or_removed():
    items = tuple(_item(name, score) for name, score in [("a", 0.9), ("security", 0.1), ("b", 0.5), ("ai", 0.3)])

    ordered, _ = prefer_domain(items, "cybersecurity", label_of=_label_of, boost=1.0)

    assert sorted(item.item_id for item in ordered) == sorted(item.item_id for item in items)


def test_equal_scores_keep_the_rerankers_order():
    items = (_item("first", 0.5), _item("second", 0.5), _item("third", 0.5))

    ordered, _ = prefer_domain(items, "cybersecurity", label_of=_label_of, boost=0.1)

    assert [item.item_id for item in ordered] == ["first", "second", "third"]


# --- the orchestrator ------------------------------------------------------------


def _scope() -> AccessScope:
    return AccessScope(
        tenant_id="alice",
        user_id="alice",
        role="viewer",
        allowed_sources=frozenset(f"/uploads/alice/{name}.md" for name in ("a", "b", "c", "security")),
        allowed_fields=DEFAULT_CONTEXT_FIELDS,
    )


RERANK = {"a": 0.80, "b": 0.75, "c": 0.70, "security": 0.66}


@pytest.fixture
def rerank_calls(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """A deterministic reranker that honours `top_n` the way the real one does."""

    calls: list[int] = []

    async def fake_rerank(query, items, *, top_n, timeout_ms, enabled):
        calls.append(top_n)
        rescored = sorted(
            (item.model_copy(update={"score": RERANK[item.item_id]}) for item in items),
            key=lambda item: item.score,
            reverse=True,
        )
        return tuple(rescored[:top_n]), {"reranker_backend": "fake"}

    monkeypatch.setattr(orchestrator_module, "rerank_evidence", fake_rerank)
    monkeypatch.setattr(
        orchestrator_module,
        "load_domain_labels",
        lambda: DomainLabels(by_document_id={"doc-security": "cybersecurity"}, by_source={}),
    )
    return calls


def _run(*, domain: str | None, rerank: bool = True, top_n: int = 3, boost: float = 0.1):
    async def vector(plan, scope):
        return (tuple(_item(name, 0.5) for name in RERANK),)

    orchestrator = KnowledgeOrchestrator(adapters={"vector": CallableKnowledgeAdapter("vector", vector)})
    orchestrator._domain_boost = boost
    strategy = KnowledgeStrategy(
        sources=(KnowledgeSourcePlan(source="vector", queries=("q",), top_k=10, timeout_ms=5_000),),
        rewrite=False,
        rerank=rerank,
        rerank_top_n=top_n,
        rationale="test",
        preferred_domain=domain,
    )
    return asyncio.run(orchestrator.retrieve(strategy, _scope(), discard_trace))


def test_a_labelled_passage_just_below_the_cut_is_kept(rerank_calls):
    """Reranked alone it is fourth of four and a top-3 cut drops it; with the
    preference it scores 0.76 and displaces the 0.70 passage."""

    bundle = _run(domain="cybersecurity")

    assert [item.item_id for item in bundle.evidence] == ["a", "security", "b"]
    assert rerank_calls == [4], "every candidate is kept through reranking and cut after the boost"
    assert bundle.diagnostics["preferred_domain"] == "cybersecurity"
    assert bundle.diagnostics["domain_boosted_count"] == 1


def test_without_a_preference_nothing_changes(rerank_calls):
    bundle = _run(domain=None)

    assert [item.item_id for item in bundle.evidence] == ["a", "b", "c"]
    assert rerank_calls == [3], "the reranker is asked for exactly what it was asked for before"
    assert bundle.diagnostics["preferred_domain"] is None


def test_a_zero_boost_switches_it_off(rerank_calls):
    bundle = _run(domain="cybersecurity", boost=0.0)

    assert [item.item_id for item in bundle.evidence] == ["a", "b", "c"]
    assert rerank_calls == [3]


def test_an_unreranked_list_is_not_boosted(rerank_calls):
    """Its scores are RRF's (about 0.016), where 0.1 would be an override."""

    bundle = _run(domain="cybersecurity", rerank=False)

    assert rerank_calls == []
    assert bundle.diagnostics["preferred_domain"] is None


# --- where the domain comes from --------------------------------------------------


def _route(agent_class: str) -> RouterDecision:
    return RouterDecision(
        intent="knowledge_retrieval",
        complexity="simple",
        completeness="complete",
        next_stage="knowledge",
        confidence=0.9,
        reason="test",
        agent_class=agent_class,
    )


def _request() -> OrchestrationRequest:
    return OrchestrationRequest(
        question="how do I patch log4j",
        actor=RequestActor(user_id="alice", tenant_id="alice", role="viewer"),
        source_scope=RequestScope(),
    )


@pytest.mark.parametrize(
    ("agent_class", "expected"),
    [
        ("cybersecurity", "cybersecurity"),
        ("CyberSecurity", "cybersecurity"),
        ("general", None),
        ("no-such-class", None),
    ],
)
def test_the_strategy_carries_the_routed_specialist(agent_class, expected):
    strategy = asyncio.run(KnowledgeAgentService().decide(_request(), _route(agent_class), None))

    assert strategy.preferred_domain == expected


def test_a_deciders_own_domain_is_replaced_by_the_routes():
    """A decider's strategy is untrusted input; the domain comes from the route."""

    async def decider(request, route, plan, retry_feedback):
        return KnowledgeStrategy(
            sources=(KnowledgeSourcePlan(source="vector", queries=("q",), top_k=4, timeout_ms=5_000),),
            rationale="decider",
            preferred_domain="artificial_intelligence",
        )

    strategy = asyncio.run(KnowledgeAgentService(decider=decider).decide(_request(), _route("general"), None))

    assert strategy.preferred_domain is None


# --- the registry lookup -------------------------------------------------------------


def _write_registry(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_labels_are_read_from_the_registry_by_id_then_by_source(tmp_path, monkeypatch):
    monkeypatch.setattr(domain_labels._cache, "value", None)
    registry = tmp_path / "documents.jsonl"
    _write_registry(
        registry,
        [
            {"document_id": "doc-1", "source": "/uploads/a/one.md", "agent_class": "cybersecurity"},
            {"document_id": "", "source": "/uploads/a/legacy.md", "agent_class": "artificial_intelligence"},
        ],
    )

    labels = load_domain_labels(registry)

    assert labels.label_of("doc-1", "/elsewhere.md") == "cybersecurity"
    assert labels.label_of("/uploads/a/legacy.md", "/uploads/a/legacy.md") == "artificial_intelligence"
    assert labels.label_of("doc-unknown", "/unknown.md") is None


def test_a_relabel_is_seen_on_the_next_read(tmp_path, monkeypatch):
    """No reindex, no cross-process message: the registry file is the signal."""

    monkeypatch.setattr(domain_labels._cache, "value", None)
    registry = tmp_path / "documents.jsonl"
    _write_registry(registry, [{"document_id": "doc-1", "source": "/s", "agent_class": "general"}])
    assert load_domain_labels(registry).label_of("doc-1", None) == "general"

    _write_registry(registry, [{"document_id": "doc-1", "source": "/s", "agent_class": "cybersecurity"}])
    stat = registry.stat()
    os.utime(registry, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))

    assert load_domain_labels(registry).label_of("doc-1", None) == "cybersecurity"


def test_no_registry_means_no_labels(tmp_path):
    assert load_domain_labels(tmp_path / "missing.jsonl").label_of("doc-1", "/s") is None
