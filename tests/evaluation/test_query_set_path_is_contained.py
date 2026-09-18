"""`--queries` is a command-line value that gets opened, so it is bounded.

`pythonsecurity:S8707`, raised against `load_queries` the day `--queries` landed.
The rule frames the risk as an agent running the tool with an argument it did not
choose, and that is how this repository is operated -- the same reasoning already
recorded for `scripts/audit/cognitive_complexity.py`, which carries the same
shape for the same rule.

The test that matters is `test_a_symlink_out_of_the_tree_is_refused`: it is the
case a `".." not in raw` check passes and this one does not, and it is the reason
the containment resolves before it compares.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "eval_retrieval.py"

# Loaded by path for the reason `test_cognitive_complexity_is_bounded.py` does
# it: `scripts/` is not a package, and the alternative is a transcription of the
# function, which is the defect this repository records for the regex suite.
_spec = importlib.util.spec_from_file_location("eval_retrieval_cli", MODULE_PATH)
assert _spec and _spec.loader
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

query_set_path = _module.query_set_path


def test_a_query_set_in_the_repository_is_accepted():
    """The direction a containment loses first: refusing everything is not a
    fix, it is the tool being deleted a week later."""

    resolved = query_set_path("config/eval/retrieval_queries_crossdoc.json")

    assert resolved.is_file()
    assert resolved.name == "retrieval_queries_crossdoc.json"


def test_an_absolute_path_outside_the_tree_is_refused():
    with pytest.raises(SystemExit) as refusal:
        query_set_path("/etc/passwd")

    assert "refusing to read" in str(refusal.value)


def test_a_relative_traversal_is_refused():
    with pytest.raises(SystemExit):
        query_set_path("../../../etc/hosts")


def test_a_traversal_that_normalises_back_inside_is_accepted():
    """`a/../b` is not an attack, and refusing it would be a string check
    pretending to be a path check. Resolving first is what tells them apart."""

    resolved = query_set_path("config/eval/../eval/retrieval_queries.json")

    assert resolved == (ROOT / "config/eval/retrieval_queries.json").resolve()


def test_a_symlink_out_of_the_tree_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """The case that decides whether the check is real.

    A symlink inside the repository pointing at a file outside it contains no
    `..` and no leading `/`, so every string-level check passes it. Resolving
    before comparing is what refuses it, and this is the only test here that can
    tell the two implementations apart.
    """

    outside = tmp_path / "secret.json"
    outside.write_text("{}", encoding="utf-8")

    link = ROOT / "config" / "eval" / "_symlink_probe.json"
    link.symlink_to(outside)
    try:
        assert ".." not in str(link.relative_to(ROOT)), "the string-level check this defeats"
        with pytest.raises(SystemExit) as refusal:
            query_set_path(str(link.relative_to(ROOT)))
        assert "refusing to read" in str(refusal.value)
    finally:
        link.unlink()


def test_a_non_json_file_inside_the_tree_is_refused():
    """A query set is JSON. Accepting anything readable widens the sink for no
    benefit -- there is no other format this can parse."""

    with pytest.raises(SystemExit):
        query_set_path("README.md")


def test_a_missing_json_file_is_refused_with_a_different_message():
    """ "Not allowed" and "not there" are different answers, and collapsing them
    sends somebody to check permissions over a typo."""

    with pytest.raises(SystemExit) as refusal:
        query_set_path("config/eval/no_such_set.json")

    assert "no such query set" in str(refusal.value)
    assert "refusing to read" not in str(refusal.value)


def test_the_command_line_actually_uses_it(monkeypatch: pytest.MonkeyPatch):
    """A containment the CLI does not call is a control that is written, tested
    and unreachable -- this repository's most expensive recurring failure.

    Added because a mutation removing the call from `main()` reddened **nothing**:
    every test above drives `query_set_path` directly, so all seven passed while
    the argument went to `Path()` raw. Driving `main()` is what closes it, and a
    refused path exits before any retrieval runs, so this costs nothing.
    """

    monkeypatch.setattr(_module.sys, "argv", ["eval_retrieval.py", "--queries", "/etc/passwd"])

    with pytest.raises(SystemExit) as refusal:
        _module.main()

    assert "refusing to read" in str(refusal.value)
