"""The local backend embeds semantically when it can, and says which it did.

Until 2026-09-09 `MODEL_BACKEND=local` -- what a fresh checkout runs -- had
exactly one embedding option: `LocalHashEmbeddings`, blake2b hash buckets whose
own docstring calls them "for offline/dev RAG smoke use". Vector search
therefore matched on little more than exact overlap, which is the single largest
quality ceiling in the system and the reason the console reported `embedding`
as `degraded`.

Meanwhile CLAUDE.md's Technology Stack claimed "Sentence-Transformers BGE-M3
embeddings" and had done for a long time. There was no bi-encoder anywhere:
`sentence_transformers` was imported only for `CrossEncoder`.

Most of what is pinned here is the degradation, not the happy path. The model is
loaded with `local_files_only=True` -- deliberately, so that a machine without it
falls back rather than starting a multi-gigabyte download inside a request --
which means "configured" and "present" are different states and the console must
not confuse them.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clear_caches():
    from app.services.models.runtime import _load_local_embedder

    _load_local_embedder.cache_clear()
    yield
    _load_local_embedder.cache_clear()


def test_a_missing_model_degrades_rather_than_downloading(monkeypatch: pytest.MonkeyPatch):
    """The property that keeps a fresh checkout usable and quiet."""

    from app.services.models import runtime

    monkeypatch.setattr(runtime, "_load_local_embedder", lambda: None)

    kind, name = runtime.local_embedding_backend()

    assert kind == "hash"
    assert name == "local hash embeddings"


def test_the_loader_asks_for_a_local_file_only():
    """Not a style point: without it, the first query on a fresh machine starts
    a multi-gigabyte download inside a request, with no timeout and no breaker --
    the defect this repository already fixed once for the NLI stage."""

    import inspect

    from app.services.models import runtime

    source = inspect.getsource(runtime._load_local_embedder)

    assert "local_files_only=True" in source
    assert "SentenceTransformer" in source


def test_a_present_model_is_used_and_named(monkeypatch: pytest.MonkeyPatch):
    from app.services.models import runtime

    class _Encoder:
        def encode(self, text, **kwargs):
            if isinstance(text, list):
                return [[0.1, 0.2, 0.3] for _ in text]
            return [0.1, 0.2, 0.3]

    monkeypatch.setattr(runtime, "_load_local_embedder", lambda: _Encoder())

    kind, name = runtime.local_embedding_backend()
    assert kind == "semantic"
    assert name == "BAAI/bge-m3"

    embedder = runtime.LocalSemanticEmbeddings(_Encoder(), "BAAI/bge-m3")
    assert embedder.embed_query("反向传播") == [0.1, 0.2, 0.3]
    assert embedder.embed_documents(["a", "b"]) == [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]


def test_the_console_reports_which_embedder_actually_runs(monkeypatch: pytest.MonkeyPatch):
    """A name in the settings proves nothing when the loader is local-only."""

    from app.services.models import effective as effective_module
    from app.services.models import runtime

    monkeypatch.setattr(effective_module, "_local_backend_forced", lambda: False, raising=False)
    import app.services.models.config_store as config_store

    monkeypatch.setattr(config_store, "get_global_model_settings", lambda: {"enabled": False})

    settings = effective_module.get_settings().model_copy(update={"model_backend": "local"})
    monkeypatch.setattr(effective_module, "get_settings", lambda: settings)

    monkeypatch.setattr(runtime, "_load_local_embedder", lambda: None)
    absent = effective_module._embedding()
    assert absent.status == "degraded"
    assert "not present on this machine" in absent.detail

    class _Encoder:
        def encode(self, text, **kwargs):
            return [0.0]

    monkeypatch.setattr(runtime, "_load_local_embedder", lambda: _Encoder())
    present = effective_module._embedding()
    assert present.status == "active"
    assert present.configured == settings.local_embed_model
    # The reindex requirement is the thing an operator most needs to be told.
    assert "reindex" in present.detail.lower()


def test_the_embeddings_are_synchronous():
    """Every caller reaches embeddings from a worker thread, and this repository's
    rule is that nothing reached from `asyncio.to_thread` may drive an event loop."""

    import inspect

    from app.services.models.runtime import LocalSemanticEmbeddings

    for name in ("embed_documents", "embed_query"):
        method = getattr(LocalSemanticEmbeddings, name)
        assert not inspect.iscoroutinefunction(method)


def test_a_dimension_mismatch_says_what_to_do():
    """Switching embedders against an existing store is a reindex, not corruption.

    A Chroma collection is dimension-locked, so moving from the 384-dimension
    hash fallback to a 1024-dimension semantic model makes every query fail.
    Chroma's own message names two integers and no remedy, which reads as a
    broken database -- and the person reading it has just changed a setting.
    """

    from app.retrievers.stores.vector import EmbeddingDimensionMismatch, _as_dimension_mismatch

    chroma_error = ValueError("Collection expecting embedding with dimension of 384, got 1024")
    translated = _as_dimension_mismatch(chroma_error)

    assert isinstance(translated, EmbeddingDimensionMismatch)
    assert "reindex" in str(translated).lower()
    assert "LOCAL_EMBED_MODEL" in str(translated)
    # The original is kept: a message that hides what actually happened is worse
    # than one that is merely unhelpful.
    assert "384" in str(translated) and "1024" in str(translated)


def test_an_unrelated_error_is_left_alone():
    """The translation must not swallow every failure as a dimension problem."""

    from app.retrievers.stores.vector import EmbeddingDimensionMismatch, _as_dimension_mismatch

    original = ValueError("database is locked")

    assert _as_dimension_mismatch(original) is original
    assert not isinstance(_as_dimension_mismatch(original), EmbeddingDimensionMismatch)


def test_a_directory_is_taken_as_given():
    """An explicit location is not second-guessed."""

    import shutil
    import tempfile

    from app.services.models.runtime import _local_model_location

    # Not pytest's tmp fixtures: their basetemp root needs permissions that are
    # not available on every Windows checkout, which this repository has now hit
    # four times.
    directory = tempfile.mkdtemp(prefix="querymind-explicit-model-")
    try:
        assert _local_model_location(directory) == directory
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_a_model_id_falls_back_to_the_modelscope_cache(monkeypatch: pytest.MonkeyPatch):
    """The route that works where Hugging Face's large-file CDN does not.

    `cdn-lfs.huggingface.co` does not resolve on many networks this application
    is deployed to -- and `hf-mirror.com` turns out to 308 back to
    huggingface.co rather than mirroring, so it is no help. ModelScope serves
    the same repository, and looking in its cache costs one `is_dir()` and makes
    the shipped default work whichever tool fetched the model.
    """

    import shutil
    import tempfile
    from pathlib import Path

    from app.services.models import runtime

    # Not pytest's `tmp_path`: its basetemp root needs permissions that are not
    # available on every Windows checkout.
    home = Path(tempfile.mkdtemp(prefix="querymind-modelscope-"))
    try:
        cached = home / ".cache" / "modelscope" / "hub" / "models" / "BAAI" / "bge-m3"
        cached.mkdir(parents=True)
        monkeypatch.setattr(runtime.Path, "home", classmethod(lambda cls: home))

        assert runtime._local_model_location("BAAI/bge-m3") == str(cached)
        # An id with no copy anywhere is returned unchanged, so the loader's own
        # `local_files_only=True` decides -- this must not invent a path.
        assert runtime._local_model_location("BAAI/absent-model") == "BAAI/absent-model"
    finally:
        shutil.rmtree(home, ignore_errors=True)
