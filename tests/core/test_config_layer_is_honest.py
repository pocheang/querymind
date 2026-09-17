"""The "which layer supplied this" column, and the two ways it lied.

That column is the reason `config_schema` exists. `Settings` puts the process
environment above the configuration centre so that a deployment can pin a value
the console cannot move, and the column is how an administrator is told *why*
their edit will not take -- `editable_here=False` is also what
`write_config_values` refuses on. When the column is wrong, the console reports a
change it did not make, which is the failure this repository spends most of its
length on.

**It was wrong in both directions.**

`alias in os.environ` versus a settings source that is case-**in**sensitive by
default. With `top_k=19` exported, `Settings().top_k` was 19 and `"TOP_K" in
os.environ` was False -- so the page called the value a default, offered to edit
it, the write was allowed, the save reported success, and the environment went on
winning. The check is asked of pydantic now, so it cannot disagree with what
`Settings` does.

And `model_config` is evaluated once, when the class body runs, so the `env_file`
path resolved into it was frozen for the life of the process -- while
`_runtime_file_values()` resolved it fresh on every call. `.runtime/` starts
empty and the documented sequence renders it, so on any process that started
before `make config-render`:

    Settings().top_k        -> 4   (the default; the file was never loaded)
    describe(...)["layer"]  -> "runtime-file"

which names a file as the source of a value nothing read. The dotenv source is
built per construction now, so a reload picks the file up and the two agree.
"""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.config_schema import _environment_aliases, describe


def _row(alias: str, settings: Settings | None = None) -> dict:
    return next(row for row in describe(settings if settings is not None else Settings()) if row["alias"] == alias)


@pytest.fixture(autouse=True)
def _no_ambient_config(monkeypatch, tmp_path):
    """Neither a runtime file nor a centre, so each test supplies its own layer."""

    empty = tmp_path / "empty.env"
    empty.write_text("", encoding="utf-8")
    monkeypatch.setenv("RUNTIME_ENV_FILE", str(empty))
    monkeypatch.delenv("TOP_K", raising=False)
    monkeypatch.delenv("top_k", raising=False)
    monkeypatch.setenv("NACOS_ENABLED", "false")
    return empty


# --- the environment layer ------------------------------------------------


def test_an_uppercase_environment_variable_is_reported_as_the_environment():
    """The case that always worked, asserted so the fix is not just "it says environment"."""

    import os

    os.environ["TOP_K"] = "5"
    try:
        row = _row("TOP_K")
    finally:
        del os.environ["TOP_K"]

    assert row["layer"] == "environment"
    assert row["editable_here"] is False


def test_a_lowercase_environment_variable_is_reported_as_the_environment(monkeypatch):
    """The defect. `Settings` honours it; `alias in os.environ` did not see it."""

    monkeypatch.setenv("top_k", "19")

    assert Settings().top_k == 19, "the premise: pydantic matches the environment case-insensitively"

    row = _row("TOP_K")
    assert row["layer"] == "environment"
    assert row["editable_here"] is False, "the console would have offered to change a pinned value"


def test_a_mixed_case_environment_variable_is_caught_too(monkeypatch):
    monkeypatch.setenv("Top_K", "7")

    assert _row("TOP_K")["layer"] == "environment"


def test_nothing_in_the_environment_is_not_the_environment():
    """A detector that answered "environment" always would pass every test above."""

    row = _row("TOP_K")

    assert row["layer"] == "default"
    assert row["editable_here"] is True


def test_the_detector_is_asked_of_pydantic_not_of_os_environ(monkeypatch):
    """One answer to "does the environment supply this", so the two cannot drift.

    A stray variable that is not a Settings alias must not invent a row either.
    """

    monkeypatch.setenv("top_k", "11")
    monkeypatch.setenv("NOT_A_SETTING_AT_ALL", "x")

    aliases = _environment_aliases()

    assert "TOP_K" in aliases
    assert "NOT_A_SETTING_AT_ALL" not in aliases


# --- the runtime-file layer ----------------------------------------------


def test_a_runtime_file_written_after_import_is_actually_read(monkeypatch, tmp_path):
    """`model_config` froze the path at import; `.runtime/` starts empty.

    So the ordinary sequence -- start something, then render -- left `Settings`
    on its defaults with no way back short of a restart, and `reload_settings()`
    could not recover it.
    """

    later = tmp_path / "rendered-later.env"
    monkeypatch.setenv("RUNTIME_ENV_FILE", str(later))
    assert not later.exists()
    assert Settings().top_k == 4

    later.write_text("TOP_K=7\n", encoding="utf-8")

    assert Settings().top_k == 7


def test_the_layer_column_agrees_with_the_value_it_reports(monkeypatch, tmp_path):
    """The two resolved the path differently, so they could name different files.

    A row saying `runtime-file` while carrying the field default is worse than no
    column: it points an operator at a file that is not the reason.
    """

    later = tmp_path / "rendered-later.env"
    monkeypatch.setenv("RUNTIME_ENV_FILE", str(later))
    later.write_text("TOP_K=7\n", encoding="utf-8")

    row = _row("TOP_K")

    assert row["layer"] == "runtime-file"
    assert row["value"] == 7


def test_a_value_not_in_the_runtime_file_is_still_a_default(monkeypatch, tmp_path):
    later = tmp_path / "rendered-later.env"
    monkeypatch.setenv("RUNTIME_ENV_FILE", str(later))
    later.write_text("TOP_K=7\n", encoding="utf-8")

    assert _row("BM25_TOP_K")["layer"] == "default"


def test_the_environment_still_outranks_the_runtime_file(monkeypatch, tmp_path):
    """The precedence the column exists to explain."""

    later = tmp_path / "rendered-later.env"
    monkeypatch.setenv("RUNTIME_ENV_FILE", str(later))
    later.write_text("TOP_K=7\n", encoding="utf-8")
    monkeypatch.setenv("top_k", "11")

    row = _row("TOP_K")

    assert row["layer"] == "environment"
    assert row["value"] == 11
