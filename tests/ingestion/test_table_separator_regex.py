"""The markdown table-separator regex is written in four places and must agree.

It was copied four times with `-+[-:]*` inside a repeated group -- both halves
match a dash, so a long dashed cell that never closes backtracks polynomially,
and SonarCloud raised python:S5852 once per copy (four critical vulnerabilities,
a failed quality gate). The replacement, `-[-:]*`, was checked against the old
pattern over 40,000 generated lines with zero differences before it landed.

Asserted here by property, not by timing (a clock is a poor thing to assert on
in CI): the four sites give the same answer on real and near-miss separators,
and none of them carries the ambiguous form any more.
"""

from __future__ import annotations

import inspect

import pytest

from app.ingestion.chunking import classification, splitter
from app.ingestion.extraction import tables
from app.ingestion.loaders import office_loader

SEPARATORS = ["|---|", "| --- | :---: |", "|:--|--:|", "|-|", "| - |", "|---|---|---|"]
NOT_SEPARATORS = ["| a | b |", "|---", "---|", "|--x--|", "||", "| : |", "|" + "-" * 5000 + "x"]


def _sites():
    return {
        "splitter": lambda line: bool(splitter._TABLE_SEP_PATTERN.match(line)),
        "office_loader": lambda line: bool(office_loader._TABLE_SEPARATOR_PATTERN.match(line)),
        "extraction.tables": tables._is_table_separator,
        # classification only asks the question as the line under a header row.
        "classification": lambda line: classification._is_table(f"| a |\n{line}", {}),
    }


@pytest.mark.parametrize("line", SEPARATORS)
def test_every_site_recognises_a_separator(line: str) -> None:
    assert {name: check(line) for name, check in _sites().items()} == dict.fromkeys(_sites(), True)


@pytest.mark.parametrize("line", NOT_SEPARATORS)
def test_every_site_rejects_a_non_separator(line: str) -> None:
    assert {name: check(line) for name, check in _sites().items()} == dict.fromkeys(_sites(), False)


def test_no_site_carries_the_backtracking_form() -> None:
    sources = {
        "splitter": splitter._TABLE_SEP_PATTERN.pattern,
        "office_loader": office_loader._TABLE_SEPARATOR_PATTERN.pattern,
        "extraction.tables": inspect.getsource(tables._is_table_separator),
        "classification": inspect.getsource(classification._is_table),
    }
    offenders = [name for name, source in sources.items() if "-+[-:]*" in source]
    assert not offenders, f"ambiguous `-+[-:]*` is back in: {offenders}"
