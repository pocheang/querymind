"""``scripts/check_coverage.py`` has to be able to fail, in both of its jobs.

The defect it exists for is a coverage report that is configured and absent, and
the way that defect survives is that everything *looks* fine: SonarCloud logs a
warning for a report path it cannot read and analyses the code anyway, so the
project gets a coverage number for one language and a silent zero for the other.
A checker for that which itself passes vacuously -- because the properties file
declares nothing, or because "the file exists" is the whole test -- reproduces
the failure one layer up.

So most of what is asserted here is the red direction: a missing report, an empty
one, an XML file that is not a coverage report, a coverage report covering no
files, an lcov with no records, and a properties file naming no reports at all.
The last one is the vacuity guard, and there is a matching assertion that the
repository's own properties file really does name two, so the check cannot be
satisfied by having nothing to check.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "check_coverage.py"

_spec = importlib.util.spec_from_file_location("check_coverage", MODULE_PATH)
check_coverage = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(check_coverage)


COVERAGE_XML = """<?xml version="1.0" ?>
<coverage line-rate="0.6123" version="7.6.1">
  <packages><package name="app"><classes>
    <class filename="app/thing.py" line-rate="0.6123"><lines><line number="1" hits="1"/></lines></class>
  </classes></package></packages>
</coverage>
"""

LCOV = "TN:\nSF:/repo/frontend/src/lib/thing.ts\nDA:1,1\nLF:1\nLH:1\nend_of_record\n"


@pytest.fixture
def tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway repository root, so nothing here reads the real reports."""

    monkeypatch.setattr(check_coverage, "ROOT", tmp_path)
    monkeypatch.setattr(check_coverage, "SONAR_PROPERTIES", tmp_path / "sonar-project.properties")
    monkeypatch.setattr(check_coverage, "BASELINE", tmp_path / "coverage-baseline.json")
    return tmp_path


def _properties(tree: Path, body: str) -> None:
    (tree / "sonar-project.properties").write_text(body, encoding="utf-8")


# --- reports -------------------------------------------------------------


def test_a_report_that_exists_and_measures_something_passes(tree: Path) -> None:
    _properties(
        tree,
        "# a comment = not a setting\nsonar.python.coverage.reportPaths=coverage.xml\n"
        "sonar.javascript.lcov.reportPaths=frontend/coverage/lcov.info\n",
    )
    (tree / "coverage.xml").write_text(COVERAGE_XML, encoding="utf-8")
    (tree / "frontend" / "coverage").mkdir(parents=True)
    (tree / "frontend" / "coverage" / "lcov.info").write_text(LCOV, encoding="utf-8")

    assert check_coverage._reports() == 0


def test_a_missing_report_fails(tree: Path) -> None:
    """The defect itself: the frontend's lcov was never copied into the job that read it."""

    _properties(tree, "sonar.javascript.lcov.reportPaths=frontend/coverage/lcov.info\n")

    assert check_coverage._reports() == 1


def test_a_properties_file_naming_no_reports_fails(tree: Path) -> None:
    """Otherwise the check passes by having nothing to look at."""

    _properties(tree, "sonar.projectKey=pocheang_querymind\nsonar.sources=app\n")

    assert check_coverage._reports() == 1


@pytest.mark.parametrize(
    ("name", "body", "complaint"),
    [
        ("coverage.xml", "", "is empty"),
        ("coverage.xml", "<not-coverage/>", "root element"),
        ("coverage.xml", "<coverage line-rate='0'></coverage>", "records no files"),
        ("coverage.xml", "<coverage", "not parseable"),
        ("lcov.info", "TN:\n", "no SF: records"),
    ],
)
def test_a_report_that_measures_nothing_is_not_a_report(tree: Path, name: str, body: str, complaint: str) -> None:
    """Existence is not the question: a zero-record report is the silent zero itself."""

    report = tree / name
    report.write_text(body, encoding="utf-8")

    described = check_coverage._describe(report)
    assert described is not None
    assert complaint in described


def test_the_real_properties_file_names_reports_for_both_languages() -> None:
    """The vacuity guard above is only worth having if the real file is not empty."""

    keys = set(check_coverage._report_paths())

    assert "sonar.python.coverage.reportPaths" in keys
    assert "sonar.javascript.lcov.reportPaths" in keys


# --- ratchet -------------------------------------------------------------


def _with_coverage(tree: Path, line_rate: float, baseline: float) -> None:
    (tree / "coverage.xml").write_text(COVERAGE_XML.replace("0.6123", f"{line_rate}"), encoding="utf-8")
    (tree / "coverage-baseline.json").write_text(json.dumps({"line_percent": baseline}), encoding="utf-8")


def test_coverage_at_the_baseline_passes(tree: Path) -> None:
    _with_coverage(tree, 0.61, baseline=61.0)

    assert check_coverage._ratchet(write=False) == 0


def test_a_drop_beyond_the_tolerance_fails(tree: Path) -> None:
    _with_coverage(tree, 0.55, baseline=61.0)

    assert check_coverage._ratchet(write=False) == 1


def test_a_drop_inside_the_tolerance_passes(tree: Path) -> None:
    """Ordinary work moves the number a little; only a real regression is red."""

    _with_coverage(tree, 0.607, baseline=61.0)

    assert check_coverage._ratchet(write=False) == 0


def test_a_stale_baseline_fails_too(tree: Path) -> None:
    """A ratchet nobody tightens is a floor, and a floor is what this replaced."""

    _with_coverage(tree, 0.70, baseline=61.0)

    assert check_coverage._ratchet(write=False) == 1


def test_write_refreezes_the_baseline(tree: Path) -> None:
    _with_coverage(tree, 0.70, baseline=61.0)

    assert check_coverage._ratchet(write=True) == 0
    assert json.loads((tree / "coverage-baseline.json").read_text(encoding="utf-8"))["line_percent"] == 70.0
    assert check_coverage._ratchet(write=False) == 0


def test_a_missing_coverage_report_is_an_error_not_a_pass(tree: Path) -> None:
    (tree / "coverage-baseline.json").write_text(json.dumps({"line_percent": 61.0}), encoding="utf-8")

    with pytest.raises(SystemExit):
        check_coverage._ratchet(write=False)
