"""`global` statements in app/ only go down (ARC-09).

A `global x` inside a function is a hidden dependency: readers cannot see it and
tests must reach into the module to reset it. Lazily built singletons use
`app.core.singleton.Singleton` instead. The remaining sites are flags, install
guards and caches with arguments, each of which needs a case-by-case answer, so
the count is a ratchet rather than a ban: lowering it is free, raising it fails
with a pointer to the helper.
"""

from __future__ import annotations

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"

# Update only downwards.
MAX_GLOBAL_STATEMENTS = 22


def _count() -> tuple[int, list[str]]:
    sites: list[str] = []
    for path in APP.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Global):
                sites.append(f"{path.relative_to(APP.parent).as_posix()}:{node.lineno}")
    return len(sites), sorted(sites)


def test_global_statements_do_not_grow():
    count, sites = _count()
    assert count <= MAX_GLOBAL_STATEMENTS, (
        f"{count} `global` statements (limit {MAX_GLOBAL_STATEMENTS}). Use app.core.singleton.Singleton for a "
        "lazily built instance. Sites:\n" + "\n".join(sites)
    )


def test_the_ratchet_is_tight():
    count, _ = _count()
    assert count == MAX_GLOBAL_STATEMENTS, f"{count} sites now: lower MAX_GLOBAL_STATEMENTS to {count}"
