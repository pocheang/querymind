"""An admin must be able to see what the model stack is actually doing.

Every other admin surface answers "what did I save". Three things make that a
different question from "what will the next question use", and all three are
silent:

* `MODEL_BACKEND=local` in the process environment discards the global override,
  so a saved OpenAI configuration can be stored and inert at once.
* The reranker and the NLI cross-encoder are loaded with `local_files_only=True`.
  A model that was never downloaded does not raise -- it returns None, and
  retrieval falls back to lexical scoring while validation falls back to a
  deterministic scorer. Both keep answering. From outside, degraded and healthy
  look the same.
* On the offline backend there is no language model at all, and the quality
  targets in CLAUDE.md describe a path that is not running.

`degraded` is the status worth having, so most of what is asserted here is that
each degraded state is actually reported. A view that could only ever say
"active" would be the same class of defect as a scanner whose checks match
nothing.
"""

from __future__ import annotations

import sys
import types

import pytest

from app.core.config import get_settings
from app.services.models import effective as effective_module
from app.services.models.effective import effective_model_configuration


def _by_component(monkeypatch, **overrides):
    settings = get_settings().model_copy(update=overrides)
    monkeypatch.setattr(effective_module, "get_settings", lambda: settings)
    return {item.component: item for item in effective_model_configuration()}


DISABLED_GLOBAL_CONFIG = {
    "enabled": False,
    "provider": "local",
    "api_key": "",
    "base_url": "",
    "chat_model": "",
    "reasoning_model": "",
    "embedding_model": "",
    "temperature": 0.7,
    "max_tokens": 2048,
}


@pytest.fixture(autouse=True)
def _no_optional_models(monkeypatch):
    """Neither optional model is loaded, which is the fresh-checkout state.

    The stored global configuration is stubbed here too, and that part is not a
    convenience. `_chat()` reads it from `APP_DB_PATH`, so without this the
    environment-branch tests below assert against whatever the developer last
    saved in the admin console -- they passed for months and then failed the
    first time somebody configured a provider on their own machine, which is a
    test reporting the database rather than the code.
    """

    import app.services.models.config_store as config_store
    from app.services.models import runtime

    monkeypatch.setattr("app.retrievers.reranker._load_cross_encoder", lambda: None)
    monkeypatch.setattr("app.agents.validation.nli.load_nli_cross_encoder", lambda: None)
    # The local embedding model is stubbed absent for the same reason the stored
    # configuration is: `_load_local_embedder` looks on the developer's disk, so
    # without this the embedding assertions below report whichever models happen
    # to be cached on the machine running them. That is a test reporting the
    # environment rather than the code, and it went red the day bge-m3 was
    # downloaded here. `tests/services/test_local_semantic_embeddings.py` covers
    # the present case.
    monkeypatch.setattr(runtime, "_load_local_embedder", lambda: None)
    monkeypatch.setattr(config_store, "get_global_model_settings", lambda: dict(DISABLED_GLOBAL_CONFIG))
    monkeypatch.delenv("MODEL_BACKEND", raising=False)


def _with_stored_config(monkeypatch, **overrides):
    """Give `_chat()` an administrator configuration to read."""

    import app.services.models.config_store as config_store

    stored = {**DISABLED_GLOBAL_CONFIG, **overrides}
    monkeypatch.setattr(config_store, "get_global_model_settings", lambda: dict(stored))


def test_every_component_in_the_pipeline_is_reported():
    """The exact set, so a component added without a test here fails, and one
    quietly dropped fails too. Ordered the way a question moves through the
    system: an image is read and described at ingestion, then embedded, then
    retrieved and reranked, then answered and checked."""

    components = [item.component for item in effective_model_configuration()]

    assert components == ["ocr", "image_caption", "embedding", "reranker", "chat", "validation_nli"]


def test_a_reranker_whose_model_is_missing_is_degraded_not_active(monkeypatch):
    """The assertion that matters most: this state returns results and looks
    healthy, because `rerank_with_diagnostics` falls back to lexical scoring."""

    reranker = _by_component(monkeypatch, enable_reranker=True)["reranker"]

    assert reranker.status == "degraded"
    assert "lexical" in reranker.detail


def test_a_reranker_that_is_switched_off_is_disabled_not_degraded(monkeypatch):
    """Off on purpose and broken are different states; collapsing them would
    make the degraded signal meaningless."""

    reranker = _by_component(monkeypatch, enable_reranker=False)["reranker"]

    assert reranker.status == "disabled"


def test_a_present_reranker_is_active(monkeypatch):
    """The positive direction, so the degraded assertions cannot pass by the
    status being stuck."""

    monkeypatch.setattr("app.retrievers.reranker._load_cross_encoder", lambda: object())

    assert _by_component(monkeypatch, enable_reranker=True)["reranker"].status == "active"


def test_nli_without_its_model_is_degraded(monkeypatch):
    nli = _by_component(monkeypatch, cascade_enable_nli=True)["validation_nli"]

    assert nli.status == "degraded"
    assert "token overlap" in nli.detail


def test_a_present_nli_model_reports_the_language_limit(monkeypatch):
    """Active is not unqualified here: the configured model is English, so
    Chinese answers take the deterministic path even when it loads."""

    monkeypatch.setattr("app.agents.validation.nli.load_nli_cross_encoder", lambda: object())

    nli = _by_component(monkeypatch, cascade_enable_nli=True)["validation_nli"]

    assert nli.status == "active"
    assert "Chinese" in nli.detail


def test_the_offline_backend_is_degraded_for_chat_and_embedding(monkeypatch):
    """What a fresh checkout runs. Answers are assembled by a stand-in and
    embeddings are deterministic hashes -- neither is what the quality targets
    describe."""

    components = _by_component(monkeypatch, model_backend="local")

    assert components["chat"].status == "degraded"
    assert components["embedding"].status == "degraded"
    assert "offline" in components["chat"].detail


def test_a_configured_provider_is_active(monkeypatch):
    components = _by_component(monkeypatch, model_backend="openai", openai_chat_model="gpt-5.5")

    assert components["chat"].status == "active"
    assert components["chat"].configured == "gpt-5.5"


def test_an_enabled_administrator_configuration_is_what_chat_reports(monkeypatch):
    """The branch a configured deployment actually takes, and it had no test.

    Its `detail` also promised a per-user configuration -- "including those with
    personal settings" -- for a day after that surface was deleted, which nothing
    here would have caught.
    """

    _with_stored_config(monkeypatch, enabled=True, provider="anthropic", chat_model="claude-sonnet-5")

    chat = _by_component(monkeypatch, model_backend="local")["chat"]

    # The stored configuration wins over the environment, which is the whole
    # point of the switch: `model_backend="local"` is what a fresh checkout has.
    assert chat.status == "active"
    assert chat.configured == "claude-sonnet-5"
    assert chat.metadata["provider"] == "anthropic"
    assert "personal" not in chat.detail.lower()


def test_an_environment_pin_is_reported_as_degraded_chat(monkeypatch):
    """The pin discards a saved provider config outright, so reporting the saved
    value alone would describe something that is not running."""

    monkeypatch.setenv("MODEL_BACKEND", "local")

    chat = _by_component(monkeypatch, model_backend="openai")["chat"]

    assert chat.status == "degraded"
    assert chat.source == "environment"


# --- the image path: OCR and captioning read together ------------------------


def test_captioning_off_says_what_that_costs(monkeypatch):
    """Off is a valid choice, but the consequence is not obvious: an image with
    no readable text is then not indexed at all."""

    caption = _by_component(monkeypatch, image_caption_enabled=False)["image_caption"]

    assert caption.status == "disabled"
    assert "not indexed" in caption.detail


def test_captioning_without_a_key_for_its_first_backend_is_degraded(monkeypatch):
    caption = _by_component(
        monkeypatch,
        image_caption_enabled=True,
        image_caption_backend="openai",
        openai_api_key="",
    )["image_caption"]

    assert caption.status == "degraded"
    assert "no API key" in caption.detail


def test_captioning_with_its_backend_configured_is_active(monkeypatch):
    caption = _by_component(
        monkeypatch,
        image_caption_enabled=True,
        image_caption_backend="ollama",
        ollama_vision_model="llava:7b",
    )["image_caption"]

    assert caption.status == "active"
    assert caption.configured == "llava:7b"


def test_the_backend_order_is_reported(monkeypatch):
    """`auto` follows MODEL_BACKEND and falls back, so which one is tried first
    is not something an operator can read off a single setting."""

    caption = _by_component(
        monkeypatch,
        image_caption_enabled=True,
        image_caption_backend="auto",
        model_backend="openai",
        openai_api_key="present",
    )["image_caption"]

    assert caption.metadata["order"] == "openai, ollama"


def _pytesseract(monkeypatch, *, installed: bool):
    """Control whether the package is importable, instead of inheriting it.

    `_ocr` probes two independent things -- `import pytesseract`, then the binary
    on PATH -- and a test that patches only the second inherits the first from
    whatever machine it runs on. That is how `test_present_tesseract_is_active`
    came to pass locally and fail in CI, which installs no pytesseract: the
    import failed first and the status was `unavailable` before `shutil.which`
    was ever consulted.
    """

    if installed:
        monkeypatch.setitem(sys.modules, "pytesseract", types.ModuleType("pytesseract"))
    else:
        monkeypatch.delitem(sys.modules, "pytesseract", raising=False)
        monkeypatch.setattr(sys, "meta_path", [_Uninstalled("pytesseract"), *sys.meta_path])


class _Uninstalled:
    """A finder that makes one package look absent, whatever is on disk."""

    def __init__(self, name: str) -> None:
        self._name = name

    def find_spec(self, fullname, path=None, target=None):
        if fullname == self._name:
            raise ModuleNotFoundError(f"No module named {fullname!r}", name=fullname)
        return None


def test_a_missing_pytesseract_is_unavailable_and_says_which_half(monkeypatch):
    """Two things can be missing and they need different remedies: install the
    package, or put the binary on PATH. `source` is what tells them apart, and
    asserting only `status` cannot -- both branches mention captioning."""

    _pytesseract(monkeypatch, installed=False)

    ocr = _by_component(monkeypatch)["ocr"]

    assert ocr.status == "unavailable"
    assert ocr.source == "pytesseract"


def _no_tesseract_anywhere(monkeypatch):
    """A machine that genuinely has none.

    Stubbing `shutil.which` alone stopped being enough once the resolver started
    probing standard install locations -- on a developer machine with Tesseract
    installed, this test then asserted `unavailable` against a resolver that
    correctly found it. Both halves have to be absent to mean what the test says.
    """

    import app.ingestion.extraction.ocr as ocr_module

    monkeypatch.setattr("shutil.which", lambda _cmd: None)
    monkeypatch.setattr(ocr_module, "_TESSERACT_FALLBACK_PATHS", ())


def test_a_missing_binary_is_unavailable_and_says_so(monkeypatch):
    """The half that fails on a fresh machine, and the reason captioning matters."""

    _pytesseract(monkeypatch, installed=True)
    _no_tesseract_anywhere(monkeypatch)

    ocr = _by_component(monkeypatch)["ocr"]

    assert ocr.status == "unavailable"
    assert ocr.source == "TESSERACT_CMD"
    assert "captioning" in ocr.detail


def test_present_tesseract_is_active(monkeypatch):
    """The positive direction, so the assertions above cannot pass by the probe
    always failing -- which is exactly what happened in CI."""

    _pytesseract(monkeypatch, installed=True)
    monkeypatch.setattr("shutil.which", lambda _cmd: "/usr/bin/tesseract")

    assert _by_component(monkeypatch)["ocr"].status == "active"


def test_tesseract_installed_but_not_on_path_is_found(monkeypatch):
    """The state a Windows machine is in the moment Tesseract is installed.

    Its installer does not add itself to PATH, so `shutil.which` says no while
    the binary sits at a standard location -- and this panel reported
    `unavailable` over an OCR that would have worked the moment anything looked
    one directory further.
    """

    import shutil as shutil_module
    import tempfile
    from pathlib import Path

    import app.ingestion.extraction.ocr as ocr_module

    # Not pytest's `tmp_path`: its basetemp root needs permissions that are not
    # available on every Windows checkout, which this repository has hit three
    # times now -- most recently on the first run of this very test.
    root = Path(tempfile.mkdtemp(prefix="querymind-tesseract-"))
    binary = root / "tesseract.exe"
    binary.write_text("", encoding="utf-8")

    _pytesseract(monkeypatch, installed=True)
    monkeypatch.setattr("shutil.which", lambda _cmd: None)
    monkeypatch.setattr(ocr_module, "_TESSERACT_FALLBACK_PATHS", (str(binary),))

    ocr = _by_component(monkeypatch)["ocr"]

    assert ocr.status == "active"
    assert ocr.configured == str(binary)
    # Says where it came from, because "found on this machine" and "an operator
    # set TESSERACT_CMD" are different facts for anyone reproducing a report.
    assert ocr.source == "found on this machine"

    shutil_module.rmtree(root, ignore_errors=True)


def test_an_explicit_tesseract_cmd_is_not_second_guessed(monkeypatch):
    """An operator's explicit choice wins, and its absence is reported.

    Falling back to a standard location when TESSERACT_CMD points at something
    missing would silently run a different binary than the one configured.
    """

    import app.ingestion.extraction.ocr as ocr_module

    _pytesseract(monkeypatch, installed=True)
    monkeypatch.setattr("shutil.which", lambda cmd: None)
    monkeypatch.setattr(ocr_module, "_TESSERACT_FALLBACK_PATHS", ("/usr/bin/tesseract",))

    ocr = _by_component(monkeypatch, tesseract_cmd="/nowhere/tesseract")["ocr"]

    assert ocr.status == "unavailable"
    assert ocr.configured == "/nowhere/tesseract"


def test_an_external_caption_backend_needs_the_masking_detector(monkeypatch):
    """Captioning through an external backend masks the image first, and the
    detector is Tesseract -- so the two image components now share a dependency.
    Reported rather than discovered when an image fails to be described."""

    _pytesseract(monkeypatch, installed=False)

    caption = _by_component(
        monkeypatch,
        image_caption_enabled=True,
        image_caption_backend="openai",
        openai_api_key="present",
    )["image_caption"]

    assert caption.status == "degraded"
    assert caption.source == "TESSERACT_CMD"
    assert "masked" in caption.detail


def test_a_local_caption_backend_does_not_need_it(monkeypatch):
    """The negative direction: masking is an egress control, and ollama is local,
    so a missing detector must not degrade it."""

    _pytesseract(monkeypatch, installed=False)

    caption = _by_component(
        monkeypatch,
        image_caption_enabled=True,
        image_caption_backend="ollama",
        ollama_vision_model="llava:7b",
    )["image_caption"]

    assert caption.status == "active"
