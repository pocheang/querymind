"""A domain label orders what the caller may see. It never decides what they may see.

The code this replaced (`app/services/documents/agent_scope.py`) turned a label
into a source *filter*, with a second, independent answer to "which documents
may this request read" -- and in two of its three copies, a missing
`allowed_sources` became the label's list instead of an error. None of it was
reachable, because nothing passed a class; it was deleted rather than fixed.

What remains is `prefer_domain`, which runs on items retrieval already returned
and before `ContextBuilder` applies `mask_evidence`. These tests pin both ends:
another user's document labelled with exactly the routed domain is still
dropped, and the relabel endpoint is held to the rules of every other
by-id document operation.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.routes.public import documents as documents_route
from app.domain.contracts import EvidenceItem
from app.domain.knowledge import AccessScope, KnowledgeSourcePlan, KnowledgeStrategy
from app.knowledge import orchestrator as orchestrator_module
from app.knowledge.adapters import CallableKnowledgeAdapter
from app.knowledge.orchestrator import KnowledgeOrchestrator, discard_trace
from app.services.documents.domain_labels import DomainLabels
from app.services.security.access_scope import DEFAULT_CONTEXT_FIELDS
from app.services.security.audit_actions import AuditAction


def _item(source: str, document_id: str, score: float) -> EvidenceItem:
    return EvidenceItem(
        item_id=document_id,
        content=f"content of {document_id}",
        source=source,
        document_id=document_id,
        version=1,
        retriever="vector",
        score=score,
    )


def test_another_users_document_with_the_right_label_is_still_dropped(monkeypatch):
    async def fake_rerank(query, items, *, top_n, timeout_ms, enabled):
        return tuple(items[:top_n]), {"reranker_backend": "fake"}

    monkeypatch.setattr(orchestrator_module, "rerank_evidence", fake_rerank)
    monkeypatch.setattr(
        orchestrator_module,
        "load_domain_labels",
        lambda: DomainLabels(by_document_id={"doc-bob": "cybersecurity", "doc-alice": "cybersecurity"}, by_source={}),
    )

    async def vector(plan, scope):
        # A misbehaving source returning something outside the scope: exactly
        # the case in which a label must not help it through.
        return ((_item("/uploads/bob/secret.md", "doc-bob", 0.9), _item("/uploads/alice/own.md", "doc-alice", 0.5)),)

    scope = AccessScope(
        tenant_id="alice",
        user_id="alice",
        role="viewer",
        allowed_sources=frozenset({"/uploads/alice/own.md"}),
        allowed_fields=DEFAULT_CONTEXT_FIELDS,
    )
    strategy = KnowledgeStrategy(
        sources=(KnowledgeSourcePlan(source="vector", queries=("q",), top_k=5, timeout_ms=5_000),),
        rewrite=False,
        rerank=True,
        rationale="test",
        preferred_domain="cybersecurity",
    )
    orchestrator = KnowledgeOrchestrator(adapters={"vector": CallableKnowledgeAdapter("vector", vector)})

    bundle = asyncio.run(orchestrator.retrieve(strategy, scope, discard_trace))

    assert [item.document_id for item in bundle.evidence] == ["doc-alice"]


def test_the_old_filtering_module_is_gone():
    """A second authority over scope, deleted rather than fixed. Keep it that way."""

    import importlib.util

    assert importlib.util.find_spec("app.services.documents.agent_scope") is None
    assert importlib.util.find_spec("app.services.agent_document_filter") is None


# --- the relabel endpoint --------------------------------------------------------------

_ROWS = [
    {
        "filename": "report.pdf",
        "source": "/uploads/alice/report.pdf",
        "document_id": "doc-alice",
        "owner_user_id": "alice",
        "tenant_id": "alice",
        "visibility": "private",
        "agent_class": "general",
    },
    {
        "filename": "report.pdf",
        "source": "/uploads/bob/report.pdf",
        "document_id": "doc-bob",
        "owner_user_id": "bob",
        "tenant_id": "bob",
        "visibility": "private",
        "agent_class": "general",
    },
]


@pytest.fixture
def client(monkeypatch) -> TestClient:
    from app.api import main

    monkeypatch.setattr(documents_route, "_list_visible_documents_for_user", lambda user: [dict(r) for r in _ROWS])
    monkeypatch.setattr(
        documents_route,
        "_is_source_manageable_for_user",
        lambda source, user: str(source or "").startswith(f"/uploads/{user['user_id']}/"),
    )
    monkeypatch.setattr(documents_route, "_require_permission", lambda *a, **k: None)
    updates: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        documents_route, "update_document_record", lambda document_id, fields: updates.append((document_id, fields))
    )
    audits: list[dict[str, Any]] = []
    monkeypatch.setattr(documents_route, "_audit", lambda request, **kwargs: audits.append(kwargs))
    test_client = TestClient(main.app)
    test_client.updates = updates  # type: ignore[attr-defined]
    test_client.audits = audits  # type: ignore[attr-defined]
    return test_client


def _as(user_id: str) -> dict[str, str]:
    return {"X-Test-User": user_id, "X-Test-User-Id": user_id, "X-Test-Role": "viewer"}


def test_an_owner_can_relabel_their_document(client):
    response = client.patch("/documents/by-id/doc-alice", json={"agent_class": "CyberSecurity"}, headers=_as("alice"))

    assert response.status_code == 200, response.text
    assert response.json() == {"document_id": "doc-alice", "agent_class": "cybersecurity"}
    assert client.updates == [("doc-alice", {"agent_class": "cybersecurity"})]
    (audit,) = client.audits
    assert audit["action"] == AuditAction.DOCUMENT_RELABEL
    assert "agent_class=general->cybersecurity" in audit["detail"]


def test_someone_elses_document_is_not_found_not_forbidden(client):
    """'No such document' and 'not yours' answer identically: the difference is a disclosure."""

    response = client.patch("/documents/by-id/doc-bob", json={"agent_class": "cybersecurity"}, headers=_as("alice"))
    missing = client.patch("/documents/by-id/doc-none", json={"agent_class": "cybersecurity"}, headers=_as("alice"))

    assert response.status_code == missing.status_code == 404
    assert response.json() == missing.json()
    assert client.updates == []


def test_an_unknown_class_is_refused_and_nothing_is_written(client):
    response = client.patch("/documents/by-id/doc-alice", json={"agent_class": "astrology"}, headers=_as("alice"))

    assert response.status_code == 400
    assert "unknown agent_class" in response.text
    assert client.updates == []
