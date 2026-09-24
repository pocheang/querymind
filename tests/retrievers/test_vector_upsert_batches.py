"""Vector writes respect the server's batch limit and undo themselves on failure.

Chroma refuses a batch larger than `get_max_batch_size()` (5461 on 1.5.9), and
nothing split one, so a document of more chunks than that could never be
indexed. Found by ingesting a 6 MB file in the shared-mode stack, where the
refusal also left the corpus holding rows for vectors that were never written.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.retrievers.stores import vector


class _Collection:
    def __init__(self, fail_on_batch: int | None = None) -> None:
        self.batches: list[list[str]] = []
        self.deleted: list[str] = []
        self._fail_on = fail_on_batch

    def upsert(self, *, ids, embeddings, documents, metadatas):
        if self._fail_on is not None and len(self.batches) == self._fail_on:
            raise ValueError("server said no")
        self.batches.append(list(ids))

    def delete(self, *, ids):
        self.deleted.extend(ids)


def _store(collection: _Collection, limit: int = 3):
    return SimpleNamespace(_collection=collection, _client=SimpleNamespace(get_max_batch_size=lambda: limit))


def _write(monkeypatch, collection: _Collection, count: int = 7) -> None:
    monkeypatch.setattr(vector, "_store_for", lambda name: _store(collection))
    ids = [f"c{i}" for i in range(count)]
    vector.upsert_texts(None, ids, [f"t{i}" for i in ids], [{"i": i} for i in ids], [[0.0]] * count)


def test_a_write_larger_than_the_limit_goes_in_batches_the_server_accepts(monkeypatch):
    collection = _Collection()
    _write(monkeypatch, collection)
    assert [len(batch) for batch in collection.batches] == [3, 3, 1]
    assert collection.deleted == []


def test_a_refused_batch_removes_what_this_write_had_already_stored(monkeypatch):
    collection = _Collection(fail_on_batch=1)
    with pytest.raises(ValueError, match="server said no"):
        _write(monkeypatch, collection)
    assert collection.deleted == ["c0", "c1", "c2"]


def test_the_limit_is_the_servers_not_a_constant(monkeypatch):
    collection = _Collection()
    monkeypatch.setattr(vector, "_store_for", lambda name: _store(collection, limit=5))
    vector.upsert_texts(None, list("abcdefg"), list("abcdefg"), [{}] * 7, [[0.0]] * 7)
    assert [len(batch) for batch in collection.batches] == [5, 2]
