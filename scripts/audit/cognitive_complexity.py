#!/usr/bin/env python
"""Sonar's cognitive complexity (`python:S3776`), computed locally.

SonarCloud's number is only available after a push and an analysis, which is far
too slow a loop for a refactor: you find out whether a function came under the
threshold minutes later, in a browser. CLAUDE.md already records the consequence
of guessing instead -- a split judged "about 10" by reading measured 16, so a
refactor of the project's worst finding would have shipped a new one.

So this implements the scoring rules, and **its own correctness is the thing to
check first**. `--validate issues.json` scores every `python:S3776` finding in a
SonarCloud issue export and reports how many it reproduces exactly. A scorer
that has not been shown to agree with Sonar is worth nothing: it would send you
to refactor functions that are fine and pass ones that are not.

    python scripts/audit/cognitive_complexity.py app/tools/graph/core.py
    python scripts/audit/cognitive_complexity.py --over 15 app/
    python scripts/audit/cognitive_complexity.py --validate sonar_issues.json

**It reproduces all 75 of the project's open `python:S3776` findings exactly**
(2026-09-09). One looked like a disagreement and was not: `extract_charts_from_pdf`
scored 28 here against Sonar's 29, because an `or` had been deleted from it in
the same session -- scored against the source Sonar actually analysed, it is 29.

Rules, from the Sonar white paper as SonarPython applies them:

* +1, and a nesting increment, for `if`, ternary, `for`, `while`, and each
  `except` handler.
* +1 flat for `elif` and `else` -- they are the same decision continued, so they
  cost one but do not deepen it. `for`/`while`/`try` `else` clauses count the
  same way; `finally` costs nothing, because it is not an outcome of the
  decision, it runs either way.
* +1 for each *sequence* of the same boolean operator, so `a and b and c` costs
  one and `a and b or c` costs two.
* A nesting increment, but no +1, for a nested `def` or `lambda`: the closure's
  own branches pay the enclosing depth. This is why an `async`/`sync` wrapper
  pair reads as one large function.
* +1 for a direct recursive call.
* Comprehensions cost nothing at all -- not their `for`, not their `if`, not even
  a nesting increment.

**Three of those were settled by measurement, not by reading the paper**, and
the numbers are recorded because each looked plausible:

    comprehensions cost nothing          74/75   <- adopted
    comprehensions add nesting only      71/75
    their `if` clauses charge            48/75
    their `for` clauses charge too       29/75

    try/else +1, finally +0              74/75   <- adopted
    try/else +0, finally +0              73/75
    try/else +1, finally +1              71/75
    try/else +0, finally +1              70/75

The fourth was worth 8 points on one function: **`elif x:` and `else:` holding a
nested `if x:` produce the same AST** -- a lone `If` in `orelse` -- and they do
not cost the same, because the first continues a decision and the second opens
one inside a deeper block. Only `col_offset` tells them apart.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

BRANCHING = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.IfExp, ast.ExceptHandler)
NESTING_ONLY = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)


class _Scorer(ast.NodeVisitor):
    """Walk one function body, charging depth as well as branches."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.score = 0
        self.depth = 0
        # `elif` arrives as an `If` inside `orelse`; the parent marks it so the
        # child knows not to charge nesting for a decision already open.
        self._elif: set[int] = set()

    # -- helpers ---------------------------------------------------------

    def _charge(self, *, nesting: bool) -> None:
        self.score += 1 + (self.depth if nesting else 0)

    def _descend(self, nodes) -> None:
        self.depth += 1
        for node in nodes:
            self.visit(node)
        self.depth -= 1

    # -- structures ------------------------------------------------------

    def visit_If(self, node: ast.If) -> None:
        is_elif = id(node) in self._elif
        if is_elif:
            self.score += 1  # continued decision: costs one, deepens nothing
        else:
            self._charge(nesting=True)
        self.visit(node.test)
        self._descend(node.body)

        if not node.orelse:
            return
        # `elif x:` and `else:` + a nested `if x:` produce the SAME AST shape --
        # one `If` alone in `orelse` -- and they do not cost the same: the first
        # continues a decision, the second opens one inside a deeper block. The
        # column tells them apart, because an `elif` is written at the parent's
        # indentation and a nested `if` is not. Getting this wrong is worth 8
        # points on one real function, which is how it was found.
        nested = node.orelse[0]
        if len(node.orelse) == 1 and isinstance(nested, ast.If) and nested.col_offset == node.col_offset:
            self._elif.add(id(nested))
            self.visit(nested)
        else:
            self.score += 1  # `else`
            self._descend(node.orelse)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self._charge(nesting=True)
        self.visit(node.test)
        self.depth += 1
        self.visit(node.body)
        self.visit(node.orelse)
        self.depth -= 1

    def _loop(self, node) -> None:
        self._charge(nesting=True)
        self.visit(node.target)
        self.visit(node.iter)
        self._descend(node.body)
        if node.orelse:
            self.score += 1
            self._descend(node.orelse)

    visit_For = _loop
    visit_AsyncFor = _loop

    def visit_While(self, node: ast.While) -> None:
        self._charge(nesting=True)
        self.visit(node.test)
        self._descend(node.body)
        if node.orelse:
            self.score += 1
            self._descend(node.orelse)

    def visit_Try(self, node: ast.Try) -> None:
        for child in node.body:
            self.visit(child)
        for handler in node.handlers:
            self._charge(nesting=True)
            self._descend(handler.body)
        if node.orelse:
            # `try/else` costs one, like an `if`'s `else`: it is a second
            # outcome of the same decision. `finally` costs nothing, because it
            # is not an outcome at all -- it runs either way. Both halves were
            # measured against the validation set; charging `finally` as well
            # drops agreement from 74/75 to 71/75.
            self.score += 1
            self._descend(node.orelse)
        for child in node.finalbody:
            self.visit(child)

    visit_TryStar = visit_Try

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        # One charge per run of the same operator. Nested BoolOps of a
        # different kind are charged when the walk reaches them.
        self.score += 1
        for value in node.values:
            self.visit(value)

    def _nested_callable(self, node) -> None:
        body = node.body if isinstance(node.body, list) else [node.body]
        self._descend(body)

    visit_FunctionDef = _nested_callable
    visit_AsyncFunctionDef = _nested_callable
    visit_Lambda = _nested_callable

    def visit_Call(self, node: ast.Call) -> None:
        target = node.func
        if isinstance(target, ast.Name) and target.id == self.name:
            self.score += 1  # recursion
        self.generic_visit(node)


def score_function(node) -> int:
    scorer = _Scorer(node.name)
    for statement in node.body:
        scorer.visit(statement)
    return scorer.score


def functions_in(path: Path):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            yield node


def _python_files(target: Path):
    if target.is_file():
        yield target
        return
    for path in sorted(target.rglob("*.py")):
        if "__pycache__" not in path.parts:
            yield path


def report(targets: list[str], threshold: int) -> int:
    rows = []
    for target in targets:
        for path in _python_files(Path(target)):
            for node in functions_in(path):
                value = score_function(node)
                if value > threshold:
                    rows.append((value, str(path).replace("\\", "/"), node.lineno, node.name))
    rows.sort(reverse=True)
    for value, path, line, name in rows:
        print(f"{value:4d}  {path}:{line}  {name}")
    print(f"\n{len(rows)} function(s) over {threshold}; total excess {sum(v - threshold for v, *_ in rows)}")
    return 0


_REPORTED_RE = re.compile(r"from (\d+) to the (\d+) allowed")


def _export_path(raw: str) -> Path:
    """Resolve the export, refusing anything outside the working tree.

    The other half of `pythonsecurity:S8707`: `_repository_file` bounds the
    paths named *inside* the export, and this bounds the export itself. The
    rule frames the risk as an agent running the tool with an argument it did
    not choose, which is exactly how this repository is operated, so it is
    worth honouring rather than waving away as "a developer's own CLI".

    Resolve first, then contain -- a `..` check on the string is defeated by a
    symlink. `.json` because that is the only thing this reads.
    """

    candidate = Path(raw).resolve()
    roots = (Path.cwd().resolve(), REPO_ROOT)
    inside = any(candidate == root or root in candidate.parents for root in roots)
    if candidate.suffix != ".json" or not inside:
        raise SystemExit(f"refusing to read {raw!r}: expected a .json file under the working tree")
    if not candidate.is_file():
        raise SystemExit(f"no such export: {raw!r}")
    return candidate


def reported_complexities(export: Path) -> dict[tuple[str, int], int]:
    """The value Sonar reported for each S3776 finding, keyed by file and line."""

    issues = json.loads(export.read_text(encoding="utf-8"))["issues"]
    found = {}
    for issue in issues:
        if issue["rule"] != "python:S3776":
            continue
        parsed = _REPORTED_RE.search(issue["message"])
        if parsed:
            found[(issue["component"].split(":", 1)[1], issue["line"])] = int(parsed.group(1))
    return found


REPO_ROOT = Path(__file__).resolve().parents[2]


def _repository_file(rel: str) -> Path | None:
    """Resolve a path NAMED BY THE EXPORT, inside this repository, or refuse it.

    The component paths come out of a SonarCloud API response -- a network
    document -- and are then opened. Nothing stops one containing `../..` or an
    absolute path somewhere else, so this is a real traversal and not a
    hypothetical one (`pythonsecurity:S8707`, raised against this file the day
    it landed).

    Resolving first and then requiring the result to sit under the repository is
    the check that actually holds: testing the string for `..` before resolving
    is defeated by a symlink, and by `a/../../b` normalising to something the
    substring test never saw.
    """

    candidate = (REPO_ROOT / rel).resolve()
    if candidate.suffix != ".py":
        return None
    try:
        candidate.relative_to(REPO_ROOT)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def _score_at(rel: str, line: int) -> tuple[str, int] | None:
    """This scorer's answer for the function Sonar named, or None if it is gone."""

    path = _repository_file(rel)
    if path is None:
        return None
    node = next((n for n in functions_in(path) if n.lineno == line), None)
    return None if node is None else (node.name, score_function(node))


def validate(raw_export: str) -> int:
    """Score every S3776 finding Sonar reported and compare, exactly.

    The path is contained here, at the boundary, rather than inside
     -- that one parses a document it is handed, and
    putting the check in it made the parser untestable without writing into
    the working tree.
    """

    expected = reported_complexities(_export_path(raw_export))
    agree, disagree, missing = 0, [], []
    for (rel, line), want in sorted(expected.items()):
        scored = _score_at(rel, line)
        if scored is None:
            missing.append(f"{rel}:{line}")
        elif scored[1] == want:
            agree += 1
        else:
            disagree.append((rel, line, scored[0], want, scored[1]))

    for rel, line, name, want, got in disagree:
        print(f"  DISAGREE {rel}:{line} {name}: sonar {want}, here {got}")
    for item in missing:
        print(f"  MISSING  {item}")
    print(f"\nreproduced {agree}/{len(expected)} exactly ({len(disagree)} disagree, {len(missing)} not found)")
    return 0 if agree == len(expected) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("targets", nargs="*", default=["app"])
    parser.add_argument("--over", type=int, default=15, help="report functions above this (default: Sonar's 15)")
    parser.add_argument("--validate", metavar="ISSUES_JSON", help="check this scorer against a SonarCloud export")
    args = parser.parse_args()

    if args.validate:
        return validate(args.validate)
    return report(args.targets or ["app"], args.over)


if __name__ == "__main__":
    sys.exit(main())
