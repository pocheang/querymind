"""A field whose allowed values lived in a trailing comment.

Eleven `Settings` fields documented their value set as `# auto|memory|redis` and
enforced it nowhere, so a typo never failed -- every consumer normalised the
string, compared it against a set, and silently fell back:

    HISTORY_BACKEND=sqlight       -> files
    WEB_SEARCH_PROVIDER=tavly     -> DuckDuckGo (with the page still reporting tavly)
    IMAGE_CAPTION_BACKEND=banana  -> the ollama-then-openai order
    AUTH_COOKIE_SAMESITE=strct    -> lax

The last of those is a security setting weakened by a spelling mistake, with
nothing anywhere reporting it. Two of the eleven are reachable from the admin
console, so the typo need not even be in a file somebody edited deliberately.

The set is on the field now, normalised before it is matched so `MODEL_BACKEND=OpenAI`
still works and the stored value is canonical -- which is what lets the `.lower()`
at each call site stop being load-bearing. `describe()` reads the same set back out
of the annotation as `choices`, so the page can offer them and there is one
definition, where the field is.

**`OCR_ENGINE` was deliberately left alone**, and the reason is worth more than a
constraint would have been: nothing reads it. Its two hits in `app/` are
`metadata["ocr_engine"] = ...`, a dictionary key that happens to share the name,
which is also how it satisfies `test_settings_have_readers` -- that guard greps
for the field name anywhere in the tree. Constraining a field nothing consumes
would be configuring a producer with no consumer, which this repository's own rule
says to delete instead. It is recorded here rather than acted on, because deleting
a setting is a decision, not a cleanup.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Literal, get_args, get_origin

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.config_schema import describe

CONSTRAINED = {
    "MODEL_BACKEND": {"openai", "anthropic", "ollama", "local", "custom", "deepseek"},
    "RETRIEVAL_CACHE_BACKEND": {"auto", "memory", "redis", "off", "none", "disabled"},
    "SESSION_METADATA_BACKEND": {"database", "memory"},
    "MULTIMODAL_FUSION_METHOD": {"rrf", "weighted"},
    "WEB_SEARCH_PROVIDER": {"duckduckgo", "tavily", "bing", "searxng"},
    "AUTH_COOKIE_SAMESITE": {"strict", "lax", "none"},
    "QUERY_GUARD_BACKEND": {"auto", "memory", "redis"},
    "HISTORY_BACKEND": {"file", "sqlite"},
    "QUOTA_MODE": {"user", "business_unit"},
    "IMAGE_CAPTION_BACKEND": {"auto", "openai", "ollama"},
    "PDF_LOADER_MODE": {"pypdf", "docling", "docling_enhanced", "docling_advanced", "hybrid"},
}


def _annotation(alias: str):
    return next(f.annotation for n, f in Settings.model_fields.items() if (f.alias or n) == alias)


@pytest.mark.parametrize(("alias", "allowed"), sorted(CONSTRAINED.items()))
def test_the_field_states_its_allowed_values(alias, allowed):
    annotation = _annotation(alias)

    assert get_origin(annotation) is Literal, f"{alias} still accepts any string"
    assert set(get_args(annotation)) == allowed


@pytest.mark.parametrize("alias", sorted(CONSTRAINED))
def test_a_value_outside_the_set_is_refused(alias):
    with pytest.raises(ValidationError, match=alias):
        Settings(**{alias: "definitely-not-a-valid-choice"})


@pytest.mark.parametrize(("alias", "allowed"), sorted(CONSTRAINED.items()))
def test_every_allowed_value_is_accepted(alias, allowed):
    """A set that rejected everything would pass the test above."""

    for value in allowed:
        assert getattr(Settings(**{alias: value}), _field_name(alias)) == value


def _field_name(alias: str) -> str:
    return next(n for n, f in Settings.model_fields.items() if (f.alias or n) == alias)


def test_the_default_is_one_of_the_allowed_values():
    """A default outside its own set makes `Settings()` raise at import time."""

    assert Settings()


@pytest.mark.parametrize(("raw", "expected"), [(" OpenAI ", "openai"), ("LOCAL", "local"), ("Ollama", "ollama")])
def test_case_and_whitespace_are_normalised_rather_than_rejected(raw, expected):
    """Every consumer already did `.strip().lower()`, so these deployments work today.

    Normalising before the set is matched keeps them working *and* makes the
    stored value canonical, which is what lets that `.lower()` stop mattering.
    """

    assert Settings(MODEL_BACKEND=raw).model_backend == expected


def test_the_backends_match_the_set_the_render_step_validates():
    """Two lists of "what a backend may be", compared rather than described.

    `deploy/scripts/config.py` has refused an unknown `MODEL_BACKEND` at render
    time all along. Drift between the two is the shape where a value passes the
    deploy script and fails at startup, or the reverse.
    """

    module = ast.parse(Path("deploy/scripts/config.py").read_text(encoding="utf-8"))
    render_step = next(
        {element.value for element in node.value.elts}
        for node in ast.walk(module)
        if isinstance(node, ast.Assign)
        and any(getattr(target, "id", None) == "VALID_BACKENDS" for target in node.targets)
        and isinstance(node.value, ast.Set)
    )

    assert set(get_args(_annotation("MODEL_BACKEND"))) == render_step


# --- what the console is told ---------------------------------------------


def test_the_schema_offers_the_choices_for_a_constrained_editable_field():
    rows = {row["alias"]: row for row in describe()}

    assert rows["WEB_SEARCH_PROVIDER"]["choices"] == ["duckduckgo", "tavily", "bing", "searxng"]
    assert rows["IMAGE_CAPTION_BACKEND"]["choices"] == ["auto", "openai", "ollama"]


def test_a_constrained_field_still_reports_its_type_as_str():
    """`Literal[...]` has no `__name__`, so the reported type would have become
    `typing.Literal['duckduckgo', ...]` -- in a field the console branches on to
    decide whether to render a checkbox."""

    rows = {row["alias"]: row for row in describe()}

    assert rows["WEB_SEARCH_PROVIDER"]["type"] == "str"
    assert rows["TOP_K"]["type"] == "int"
    assert rows["STRICT_CSP"]["type"] == "bool"


def test_an_unconstrained_field_offers_no_choices():
    """Empty, not absent: the page reads the key either way."""

    rows = {row["alias"]: row for row in describe()}

    assert rows["TOP_K"]["choices"] == []
    assert rows["RERANKER_MODEL_NAME"]["choices"] == []


def test_ocr_engine_has_no_reader_and_so_was_not_constrained():
    """The finding this file declines to paper over.

    Both hits in `app/` are `metadata["ocr_engine"] = "..."`, a dictionary key --
    not a read of the setting. That is also how the field passes
    `test_settings_have_readers`, which greps for the name. If a reader is ever
    added, constrain the field and delete this test; if the decision is that there
    should not be one, the field goes.
    """

    reads: list[str] = []
    for path in sorted(Path("app").rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if ".ocr_engine" in text or 'getattr(settings, "ocr_engine"' in text:
            reads.append(path.as_posix())

    assert reads == [], f"OCR_ENGINE now has a reader ({reads}); give it its value set"
    assert get_origin(_annotation("OCR_ENGINE")) is not Literal
