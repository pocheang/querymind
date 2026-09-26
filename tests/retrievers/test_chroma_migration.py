"""Copying the embedded Chroma store into a server keeps every vector as it was (ARC-01 phase 5).

`STATE_BACKEND=shared` requires a Chroma server, so an installation switching
over needs its existing vectors copied. Two local clients stand in for the
embedded store and the server: the copy only ever talks to the client API.
"""

from __future__ import annotations

import chromadb
import pytest
from chromadb.config import Settings

from app.retrievers.stores.chroma_migration import copy_collections


def _client(path) -> chromadb.ClientAPI:
    return chromadb.PersistentClient(path=str(path), settings=Settings(anonymized_telemetry=False))


@pytest.fixture
def clients(tmp_path):
    source = _client(tmp_path / "source")
    docs = source.get_or_create_collection("local_rag_collection", metadata={"hnsw:space": "cosine"})
    docs.upsert(
        ids=[f"chunk-{i}" for i in range(7)],
        embeddings=[[float(i), 1.0, 0.5] for i in range(7)],
        documents=[f"text {i}" for i in range(7)],
        metadatas=[{"source": f"s{i}", "owner_user_id": "alice"} for i in range(7)],
    )
    source.get_or_create_collection("image_descriptions")
    return source, _client(tmp_path / "target")


def test_every_vector_arrives_as_stored(clients):
    source, target = clients

    reports = copy_collections(source, target, batch_size=3)

    assert [(r.name, r.copied, r.verified) for r in reports] == [
        ("image_descriptions", 0, True),
        ("local_rag_collection", 7, True),
    ]
    copied = target.get_collection("local_rag_collection").get(ids=["chunk-5"], include=["embeddings", "metadatas"])
    assert [float(x) for x in copied["embeddings"][0]] == [5.0, 1.0, 0.5]
    assert copied["metadatas"][0] == {"source": "s5", "owner_user_id": "alice"}
    assert target.get_collection("local_rag_collection").metadata == {"hnsw:space": "cosine"}


def test_a_second_run_adds_nothing_and_rewrites_nothing_else(clients):
    source, target = clients
    copy_collections(source, target)
    target.get_collection("local_rag_collection").upsert(ids=["only-on-server"], embeddings=[[0.0, 0.0, 1.0]])

    reports = copy_collections(source, target)

    assert all(r.verified for r in reports)
    assert target.get_collection("local_rag_collection").count() == 8


def test_an_id_the_server_did_not_keep_is_reported(clients, monkeypatch):
    from app.retrievers.stores import chroma_migration

    source, target = clients
    real_missing = chroma_migration._missing
    monkeypatch.setattr(chroma_migration, "_missing", lambda tgt, ids: real_missing(tgt, ids) + ids[:1])

    reports = {r.name: r for r in copy_collections(source, target, batch_size=10)}

    assert reports["local_rag_collection"].verified is False
    assert reports["local_rag_collection"].missing_after == ["chunk-0"]


def test_rows_stored_without_metadata_still_copy(tmp_path):
    source, target = _client(tmp_path / "s"), _client(tmp_path / "t")
    source.get_or_create_collection("bare").upsert(ids=["a", "b"], embeddings=[[1.0, 0.0], [0.0, 1.0]])

    (report,) = copy_collections(source, target)

    assert report.verified
    assert target.get_collection("bare").count() == 2
