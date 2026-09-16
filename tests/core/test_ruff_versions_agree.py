"""One ruff, not two.

`pyproject.toml` pins `ruff==0.16.5` exactly, and its own comment says why:
CI installing whatever ruff was newest that day failed `ruff format --check`
on commits that were clean locally. That pin covers the runtime -- it does not
cover the pre-commit hook, which fetches its own ruff from
`ruff-pre-commit` at whatever `rev` is written there.

They drifted, and the drift is worse than having no hook. On 2026-09-16 the
hook ran v0.12.0 and reformatted a docstring ending in an escaped quote into
the form that version prefers; CI then ran 0.16.5 and rejected exactly that
line. The hook reported success, the commit was allowed through, and the
failure surfaced only after the push -- so the tool meant to catch formatting
problems before they enter history is what put one there.

A lockfile cannot express this: the hook's ruff is installed by pre-commit
into its own environment, from a git rev, with nothing reading
`requirements/`. The only thing that can hold the two together is a check
that reads both files.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

_PYPROJECT_PIN = re.compile(r'"ruff==([0-9]+\.[0-9]+\.[0-9]+)"')
_REQUIREMENTS_PIN = re.compile(r"^ruff==([0-9]+\.[0-9]+\.[0-9]+)", re.MULTILINE)
# The rev belonging to the ruff-pre-commit repo, not to whichever repo block
# happens to come first in the file.
_HOOK_REV = re.compile(
    r"repo:\s*https://github\.com/astral-sh/ruff-pre-commit\s*\n\s*rev:\s*v?([0-9]+\.[0-9]+\.[0-9]+)"
)


def _one(pattern: re.Pattern[str], relative: str) -> str:
    text = (REPO / relative).read_text(encoding="utf-8")
    found = pattern.findall(text)
    assert found, f"no ruff version found in {relative}; the pattern has stopped matching"
    assert len(set(found)) == 1, f"{relative} names more than one ruff version: {sorted(set(found))}"
    return found[0]


def test_the_pre_commit_hook_runs_the_ruff_the_project_pins():
    pinned = _one(_PYPROJECT_PIN, "pyproject.toml")
    hook = _one(_HOOK_REV, ".pre-commit-config.yaml")

    assert hook == pinned, (
        f"pre-commit runs ruff {hook} while the project pins {pinned}. "
        "The hook will reformat files into a shape `ruff format --check .` "
        "rejects, pass its own check, and let the commit through to a red CI."
    )


def test_ci_installs_that_same_ruff():
    """`requirements/ci.txt` is what the backend job actually installs."""
    assert _one(_REQUIREMENTS_PIN, "requirements/ci.txt") == _one(_PYPROJECT_PIN, "pyproject.toml")
