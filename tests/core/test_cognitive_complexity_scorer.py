"""The local cognitive-complexity scorer has to agree with Sonar, or it is noise.

`scripts/audit/cognitive_complexity.py` exists because SonarCloud's number
arrives only after a push and an analysis, which is far too slow a loop to
refactor against -- and CLAUDE.md already records what guessing costs: a split
judged "about 10" by reading measured 16, so a refactor of the project's worst
finding would have shipped a new one.

A scorer nobody has checked is worse than no scorer, because it sends you to
refactor functions that are fine and passes ones that are not. It was calibrated
against all 75 of the project's open `python:S3776` findings and reproduces every
one exactly. That export is not committed (it is a live API response), so what is
pinned here is one case per rule, including the three that were settled by
measurement rather than by reading the specification.
"""

from __future__ import annotations

import ast
import importlib.util
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "audit" / "cognitive_complexity.py"

_spec = importlib.util.spec_from_file_location("cognitive_complexity", MODULE_PATH)
cc = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(cc)


def score(source: str) -> int:
    tree = ast.parse(textwrap.dedent(source))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef))
    return cc.score_function(function)


# --- the increments -------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "source", "expected"),
    [
        ("a plain if", "def f(x):\n    if x:\n        pass\n", 1),
        ("nesting is charged", "def f(x):\n    if x:\n        if x:\n            pass\n", 3),
        ("a loop", "def f(xs):\n    for x in xs:\n        pass\n", 1),
        ("an except handler", "def f():\n    try:\n        pass\n    except ValueError:\n        pass\n", 1),
        ("a ternary", "def f(x):\n    return 1 if x else 2\n", 1),
        ("one boolean run", "def f(a, b, c):\n    return a and b and c\n", 1),
        ("two boolean runs", "def f(a, b, c):\n    return a and b or c\n", 2),
        ("recursion", "def f(n):\n    return f(n - 1)\n", 1),
    ],
)
def test_each_increment(label, source, expected):
    assert score(source) == expected, label


# --- the three settled by measurement -------------------------------------


def test_elif_costs_one_and_does_not_deepen():
    """`elif` continues a decision rather than opening one."""

    assert score("def f(x):\n    if x:\n        pass\n    elif x:\n        pass\n") == 2


def test_else_holding_an_if_costs_more_than_an_elif():
    """The same AST shape, and not the same cost.

    `elif x:` and `else:` + `if x:` both put one lone `If` in `orelse`. Only the
    column separates them, and getting it wrong was worth 8 points on one real
    function -- which is how the bug in this scorer was found.
    """

    as_elif = score("def f(x):\n    if x:\n        pass\n    elif x:\n        pass\n")
    as_else = score("def f(x):\n    if x:\n        pass\n    else:\n        if x:\n            pass\n")

    assert as_elif == 2
    assert as_else == 4, "the nested if must pay the else's depth"
    assert as_else > as_elif


def test_try_else_costs_one_and_finally_costs_nothing():
    """`else` is a second outcome of the decision; `finally` runs either way.

    Measured: charging `finally` too drops agreement with Sonar from 74/75 to
    71/75.
    """

    base = "def f():\n    try:\n        pass\n    except ValueError:\n        pass\n"
    with_else = base + "    else:\n        pass\n"
    with_finally = base + "    finally:\n        pass\n"

    assert score(base) == 1
    assert score(with_else) == 2
    assert score(with_finally) == 1


@pytest.mark.parametrize(
    "source",
    [
        "def f(xs):\n    return [x for x in xs]\n",
        "def f(xs):\n    return [x for x in xs if x]\n",
        "def f(xs):\n    return {x: y for x, y in xs if x if y}\n",
        "def f(xs):\n    return any(x for x in xs if x)\n",
    ],
)
def test_comprehensions_cost_nothing(source):
    """Not their `for`, not their `if`, not even a nesting increment.

    This is not in the white paper. Charging their `if` clauses agrees with
    Sonar on 48 of 75 findings and charging the `for` as well on 29, against
    74 for costing nothing.
    """

    assert score(source) == 0


def test_a_nested_function_deepens_without_charging():
    """A closure's own branches pay the enclosing depth, which is why an
    async/sync wrapper pair reads as one large function."""

    assert score("def f():\n    def g():\n        pass\n") == 0
    assert score("def f(x):\n    def g():\n        if x:\n            pass\n") == 2


# --- the tool must not become the backlog it exists to shrink -------------


def test_the_scorer_does_not_trip_its_own_rule():
    """SonarCloud analyses `scripts/` too. The last audit tool added three
    `python:S3776` findings on the day it landed."""

    over = [
        (node.name, cc.score_function(node)) for node in cc.functions_in(MODULE_PATH) if cc.score_function(node) > 15
    ]

    assert over == [], f"the complexity tool is itself too complex: {over}"


@pytest.mark.parametrize(
    ("label", "candidate"),
    [
        ("climbs out with ..", "../../../../etc/passwd"),
        ("climbs out mid-path", "app/../../etc/passwd"),
        ("an absolute path elsewhere", "/etc/passwd"),
        ("a windows absolute path", "C:/Windows/win.ini"),
        ("not python at all", "CLAUDE.md"),
        ("inside the repo but absent", "app/does/not/exist.py"),
    ],
)
def test_a_path_from_the_export_cannot_escape_the_repository(label, candidate):
    """The component paths come out of a network response and are then opened.

    `pythonsecurity:S8707` raised this against the file the day it landed, and
    it is a real traversal rather than a hypothetical one: nothing stops a
    SonarCloud export -- or a hand-edited copy of one -- naming `../../` or an
    absolute path somewhere else.

    Resolving first and then requiring the result to sit under the repository is
    what actually holds. Checking the string for `..` before resolving is
    defeated by a symlink, and by `a/../../b` normalising to something the
    substring test never saw -- which is why the second case above is here.
    """

    assert cc._repository_file(candidate) is None, label


def test_a_real_repository_file_still_resolves():
    """The guard has to refuse without also refusing everything."""

    resolved = cc._repository_file("app/core/config.py")

    assert resolved is not None
    assert resolved.name == "config.py"
    assert resolved.is_file()


def test_it_reads_a_sonar_export_the_way_the_api_returns_one():
    """`reported_complexities` parses the live response shape, so a change to
    it fails here rather than silently validating against nothing."""

    import json
    import tempfile

    export = {
        "issues": [
            {
                "rule": "python:S3776",
                "component": "pocheang_querymind:app/x.py",
                "line": 12,
                "message": "Refactor this function to reduce its Cognitive Complexity from 19 to the 15 allowed.",
            },
            {"rule": "python:S1481", "component": "pocheang_querymind:app/y.py", "line": 3, "message": "unrelated"},
        ]
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
        json.dump(export, handle)
        path = Path(handle.name)

    try:
        assert cc.reported_complexities(path) == {("app/x.py", 12): 19}
    finally:
        path.unlink(missing_ok=True)
