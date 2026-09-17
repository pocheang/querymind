"""A configuration value must not be able to carry a configuration key.

`config_schema.EDITABLE` is the allowlist that decides what console access can
reach, and `tests/core/test_config_schema.py` keeps anything shaped like a
credential out of it by rule -- no KEY, SECRET, PASSWORD, TOKEN, PATH, URL, DSN,
CORS or ORIGIN. Six of the fields that *are* editable are plain strings
(`RERANKER_MODEL_NAME`, `NLI_MODEL_NAME`, `WEB_SEARCH_PROVIDER`,
`IMAGE_CAPTION_BACKEND`, and the two `*_VISION_MODEL`).

`RemoteDocuments.publish` rendered the document as one inline
`f"{key}={values[key]}\\n"`, and `parse_properties` reads it back a line at a
time. So a newline inside one of those six values was not data. Measured on the
shipped code:

    value:   RERANKER_MODEL_NAME = "bge\\nOPENAI_API_KEY=stolen\\nSTRICT_CSP=false"
    written: 'RERANKER_MODEL_NAME=bge\\nOPENAI_API_KEY=stolen\\nSTRICT_CSP=false\\n'
    read:    {'RERANKER_MODEL_NAME': 'bge', 'OPENAI_API_KEY': 'stolen', 'STRICT_CSP': 'false'}

`validate_values` could not see it -- a `str` field accepts a newline, so the
value type-checks -- and the shape rule it walks around is the one that exists
precisely to keep `API_SETTINGS_ENCRYPTION_KEY` and `CORS_ALLOW_ORIGINS` out of
reach. The allowlist decided which keys may be written and this decided which
keys actually were.

Two halves, because either alone leaves the hole open from the other side:

- the write refuses a value that cannot round-trip (`render_properties`), and it
  refuses *before* any document is published, so a two-document change cannot
  land half of itself and then refuse;
- the read refuses a key that is not a configuration key (`parse_properties`),
  which covers a document written by anything other than this process -- an
  operator's hand, an older build, the console's own UI.

Mostly negative assertions, for the reason the sensitive-content gate's suite is:
a rendering that refuses everything would pass "the injection is refused" just as
readily as a correct one, so the accepting cases are asserted too.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.api.application import config_reload
from app.core.config_schema import EDITABLE, validate_values
from app.core.remote_config import CONFIG_KEY_RE, parse_properties, render_properties

INJECTION = "bge-reranker\nOPENAI_API_KEY=stolen\nSTRICT_CSP=false"


# --- the write boundary ---------------------------------------------------


def test_a_value_carrying_a_newline_is_refused():
    with pytest.raises(ValueError, match="line break"):
        render_properties({"RERANKER_MODEL_NAME": INJECTION})


def test_a_carriage_return_is_refused_too():
    """`splitlines` treats it as a line ending, so `\\n` alone is half a check."""

    with pytest.raises(ValueError, match="line break"):
        render_properties({"NLI_MODEL_NAME": "a\rOPENAI_API_KEY=stolen"})


def test_a_null_byte_is_refused():
    with pytest.raises(ValueError, match="null byte"):
        render_properties({"WEB_SEARCH_PROVIDER": "duckduckgo\x00"})


def test_a_key_that_is_not_a_configuration_key_is_refused():
    with pytest.raises(ValueError, match="not a configuration key"):
        render_properties({"TOP K": "4"})


def test_an_ordinary_change_still_renders():
    """The scanner has to be able to pass, or its refusals prove nothing."""

    assert render_properties({"TOP_K": "9", "RERANKER_MODEL_NAME": "BAAI/bge-reranker-v2-m3"}) == (
        "RERANKER_MODEL_NAME=BAAI/bge-reranker-v2-m3\nTOP_K=9\n"
    )


def test_what_is_rendered_reads_back_as_what_was_asked_for():
    """The property, rather than a list of characters somebody thought of."""

    values = {"WEB_SEARCH_PROVIDER": "duckduckgo", "TOP_K": "4", "OPENAI_VISION_MODEL": "gpt-4o"}

    assert parse_properties(render_properties(values)) == values


def test_a_value_the_format_cannot_hold_unchanged_is_refused():
    """Surrounding whitespace and wrapping quotes are stripped on the way back in.

    Storing something other than what was asked for is the same failure as the
    injection, one size down: the page would report a value the document does not
    hold. The round-trip assertion catches both without knowing about either.
    """

    for value in (" spaced ", "'quoted'", '"quoted"'):
        with pytest.raises(ValueError, match="cannot store the value"):
            render_properties({"OPENAI_VISION_MODEL": value})


# --- the read boundary ----------------------------------------------------


def test_the_reader_skips_a_line_whose_key_is_not_a_configuration_key():
    """Covers a document this process did not write."""

    parsed = parse_properties("TOP_K=4\nnot a key=whatever\nRERANKER_TOP_N=5\n")

    assert parsed == {"TOP_K": "4", "RERANKER_TOP_N": "5"}


def test_the_reader_does_not_raise_on_a_bad_key():
    """`get_settings()` is on the path to everything; a typo must not end the process."""

    assert parse_properties("9LIVES=x\n") == {}


def test_the_reader_and_the_render_step_agree_on_what_a_key_is():
    """One rule, at every point the document format travels through.

    `parse_properties`'s docstring claimed it mirrored
    `deploy/scripts/config.py::parse_env_file`, and it did not: that one validated
    each key and this one accepted anything left of the first `=`. Two definitions
    of "a key" is how the gap opened, so the two patterns are compared rather than
    described.
    """

    source = Path("deploy/scripts/config.py").read_text(encoding="utf-8")
    module = ast.parse(source)
    render_step = next(
        node.value.args[0].value
        for node in ast.walk(module)
        if isinstance(node, ast.Assign)
        and any(getattr(target, "id", None) == "KEY_RE" for target in node.targets)
        and isinstance(node.value, ast.Call)
    )

    assert CONFIG_KEY_RE.pattern == render_step


# --- the write path as a whole -------------------------------------------


class _Documents:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict[str, str]]] = []

    def publish(self, data_id: str, values: dict[str, str]) -> bool:
        self.published.append((data_id, dict(values)))
        return True


def test_an_injected_value_is_refused_before_any_document_is_published():
    """The half-landed refusal: document one written, document two rejected.

    Rendering every document before publishing any is what makes the refusal
    total. Ordered so the clean document comes first, because that is the
    ordering under which publishing as it goes would have written it.
    """

    documents = _Documents()
    routed = {"base": {"TOP_K": "9"}, "retrieval": {"RERANKER_MODEL_NAME": INJECTION}}

    with pytest.raises(config_reload.ConfigWriteRefused, match="line break"):
        config_reload._publish_routed_documents(documents, routed, {})

    assert documents.published == []


def test_the_refusal_does_not_blame_the_configuration_centre():
    """It was never asked. Saying it rejected the write sends an operator to the wrong system."""

    documents = _Documents()

    with pytest.raises(config_reload.ConfigWriteRefused) as excinfo:
        config_reload._publish_routed_documents(documents, {"base": {"NLI_MODEL_NAME": INJECTION}}, {})

    assert "configuration centre" not in str(excinfo.value)


def test_the_type_check_alone_would_have_let_it_through():
    """Why the refusal is not in `validate_values`: to that, this is a valid string."""

    assert validate_values({"RERANKER_MODEL_NAME": INJECTION}) == {"RERANKER_MODEL_NAME": INJECTION}


def test_every_editable_string_field_is_covered_by_the_same_refusal():
    """Not just the one that was used to find it.

    Discovered from `EDITABLE` rather than listed, so a string field added to the
    allowlist later is covered the day it is added.
    """

    from app.core.config import Settings

    fields = Settings.model_fields
    string_aliases = [
        field.alias
        for field in EDITABLE
        if (name := next((n for n, f in fields.items() if (f.alias or n) == field.alias), None))
        and fields[name].annotation is str
    ]
    assert string_aliases, "no editable string fields found -- the discovery is broken, not the code"

    for alias in string_aliases:
        with pytest.raises(ValueError, match="line break"):
            render_properties({alias: INJECTION})
