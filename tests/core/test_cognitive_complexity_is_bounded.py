"""No function in `app/` or `scripts/` scores above Sonar's cognitive-complexity threshold.

`python:S3776` was this project's largest bucket of findings -- 75 open on
2026-09-09, with a total excess of 666 across `app/` -- and the 2026-09-09 and
2026-09-16 passes closed every one of them. Nothing was holding that: the
SonarCloud scanner in CI is dormant until a token exists, the green check on each
commit is Automatic Analysis, and a new 40-point function would have landed with
every check passing.

`scripts/audit/cognitive_complexity.py` already computes the number locally and is
the thing to trust here -- it reproduces all 75 of the findings that existed when
it was written, exactly, which is the property that makes this gate worth having
rather than a second opinion nobody can check.

**Measured when this landed: zero over 15, and fifteen functions sitting exactly
at 15.** So this is a hard gate rather than a ratchet with a baseline -- there is
nothing to freeze -- and it is a tight one: a single added branch in any of those
fifteen turns it red. That is the intended cost. CLAUDE.md recommends refactoring
to 13 rather than 15 for the same reason, and this asserts the rule's own
threshold rather than that advice, because a gate is not the place to enforce a
margin somebody may deliberately spend.

`tests/` is deliberately out of scope: it is `sonar.tests`, not `sonar.sources`,
and eight test functions are over the threshold today -- mostly parametrised
table-driven checks where the branching is the data. `frontend/src` is out of
scope because this scorer reads Python.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "audit" / "cognitive_complexity.py"

_spec = importlib.util.spec_from_file_location("cognitive_complexity", MODULE_PATH)
cc = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(cc)

# `sonar.sources` is `app,frontend/src,scripts`; these are its two Python halves.
SCOPE = ("app", "scripts")
THRESHOLD = 15

# Below the 397 files the scan covers today, and far above zero. This is the vacuity guard:
# a wrong path, a renamed directory or a `rglob` that stops matching all return
# an empty offender list, which is indistinguishable from a clean repository --
# the failure this repository records for the dead-class scanner and the
# false-positive pass that reused known-clean inputs.
MINIMUM_FILES_SCANNED = 300


def _scan() -> tuple[list[str], int]:
    offenders: list[str] = []
    scanned = 0
    for target in SCOPE:
        for path in cc._python_files(ROOT / target):
            scanned += 1
            for node in cc.functions_in(path):
                score = cc.score_function(node)
                if score > THRESHOLD:
                    offenders.append(f"{path.relative_to(ROOT).as_posix()}:{node.lineno} {node.name} scored {score}")
    return offenders, scanned


def test_the_scan_reaches_the_source_tree() -> None:
    _, scanned = _scan()

    assert scanned >= MINIMUM_FILES_SCANNED, (
        f"only {scanned} Python files were scored across {SCOPE}, which is too few to be the "
        f"source tree -- the gate below would pass by looking at nothing."
    )


def test_no_function_is_over_the_cognitive_complexity_threshold() -> None:
    offenders, _ = _scan()

    assert not offenders, (
        f"{len(offenders)} function(s) score above {THRESHOLD} (`python:S3776`):\n  "
        + "\n  ".join(sorted(offenders))
        + f"\n\nSplit along a seam the function already has, and characterize the new version "
        f"against the old one over generated inputs -- this repository's rule for a complexity "
        f"refactor, because the argument from reading the diff is what it exists to avoid. "
        f"Run `python scripts/audit/cognitive_complexity.py --over {THRESHOLD} app/ scripts/` "
        f"to see the numbers while you work."
    )


def test_the_gate_can_fail() -> None:
    """A gate nobody has seen reject anything is a gate nobody should believe.

    Twenty sequential `if`s inside a loop: +1 each for the `if`s, +1 for the
    nesting each one pays inside the loop, +1 for the loop.
    """

    import ast
    import textwrap

    body = "\n".join(f"        if value == {n}:\n            total += {n}" for n in range(20))
    source = textwrap.dedent("def noisy(values):\n    total = 0\n    for value in values:\n") + body
    function = next(
        node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    )

    assert cc.score_function(function) > THRESHOLD
