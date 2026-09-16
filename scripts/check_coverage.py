#!/usr/bin/env python
"""The coverage reports CI writes must be real, and must not get worse.

Two checks, because they are the two halves of one claim -- "this project's
coverage is measured" -- and both halves were false.

`reports` answers *where*. `sonar-project.properties` names a Python report and a
JavaScript one; until 2026-09-16 the JavaScript one was written by the frontend
job and read by a scanner step in the backend job, which is a different runner
with a different workspace, and nothing copied it across. SonarCloud does not
fail on a report path that does not exist -- it logs a warning and analyses the
code with no coverage at all -- so switching the scanner on would have published
a real Python number beside a silent zero for TypeScript, which is worse than
publishing neither. This reads the paths back out of the properties file rather
than repeating them, so a rename on either side fails here instead of degrading
to that warning.

`ratchet` answers *how much*. The suite has always written `coverage.xml` and CI
has always printed a percentage from it, and nothing anywhere could turn a drop
red: the SonarCloud scanner is dormant until a token exists, and its quality gate
carries no coverage condition in any case. A number that is printed and never
compared is a number nobody reads.

Both directions fail, which is what makes it a ratchet rather than a floor set
once and forgotten. Falling more than SLACK_DOWN below the baseline is a
regression; rising more than SLACK_UP above it means the baseline is stale and
says so, naming the one-line fix. Same shape as
`frontend/scripts/design-scale-baseline.json`, and the same reason the retrieval
metric asserts its ranks exactly rather than as a floor.

    python scripts/check_coverage.py ratchet            # compare against the baseline
    python scripts/check_coverage.py ratchet --write    # re-freeze it after a real move
    python scripts/check_coverage.py reports            # every report the scanner reads exists
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = Path(__file__).resolve().parent / "coverage-baseline.json"
SONAR_PROPERTIES = ROOT / "sonar-project.properties"

# Percentage points. Down is tight because a drop is the thing being caught; up
# is looser because ordinary work moves coverage a little in both directions and
# a re-freeze on every commit would be noise rather than a signal.
SLACK_DOWN = 0.5
SLACK_UP = 1.5


def _line_percent(report: Path) -> float:
    """coverage.py writes `line-rate` on the root element as a 0..1 fraction."""

    if not report.exists():
        raise SystemExit(f"{report} does not exist -- run pytest with --cov-report=xml:{report.name} first")
    root = ET.parse(report).getroot()
    rate = root.get("line-rate")
    if rate is None:
        raise SystemExit(f"{report} has no line-rate attribute; is it a coverage.py report?")
    return float(rate) * 100.0


def _ratchet(write: bool) -> int:
    report = ROOT / "coverage.xml"
    measured = _line_percent(report)
    print(f"line coverage: {measured:.1f}%")

    if write:
        BASELINE.write_text(json.dumps({"line_percent": round(measured, 1)}, indent=2) + "\n", encoding="utf-8")
        print(f"baseline written: {measured:.1f}%")
        return 0

    baseline = float(json.loads(BASELINE.read_text(encoding="utf-8"))["line_percent"])
    if measured < baseline - SLACK_DOWN:
        print(
            f"FAIL: coverage fell to {measured:.1f}% from a baseline of {baseline:.1f}% "
            f"(tolerance {SLACK_DOWN}pp). Cover the new code, or -- if the drop is deliberate -- "
            f"lower {BASELINE.name} in the same commit, where a reviewer can see it.",
            file=sys.stderr,
        )
        return 1
    if measured > baseline + SLACK_UP:
        print(
            f"FAIL: coverage rose to {measured:.1f}% against a baseline of {baseline:.1f}%. "
            f"Re-freeze it with `python scripts/check_coverage.py ratchet --write` so the gain "
            f"is what the next change has to keep. A ratchet nobody tightens is a floor.",
            file=sys.stderr,
        )
        return 1
    print(f"within tolerance of the {baseline:.1f}% baseline")
    return 0


def _report_paths() -> dict[str, list[Path]]:
    """Every `sonar.*.reportPaths` in sonar-project.properties, by key."""

    found: dict[str, list[Path]] = {}
    for line in SONAR_PROPERTIES.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        if not key.startswith("sonar.") or not key.endswith(".reportPaths"):
            continue
        found[key] = [ROOT / part.strip() for part in value.split(",") if part.strip()]
    return found


def _describe(report: Path) -> str | None:
    """None when the file is a usable report, otherwise why it is not.

    Existence is not the question on its own. An lcov file with no `SF:` records
    and a Cobertura report covering no files are both the silent zero this whole
    script exists to stop, and both are files that exist and are not empty.
    """

    if not report.exists():
        return "does not exist"
    if report.stat().st_size == 0:
        return "is empty"

    if report.suffix == ".xml":
        try:
            root = ET.parse(report).getroot()
        except ET.ParseError as error:
            return f"is not parseable XML ({error})"
        if root.tag != "coverage":
            return f"has root element <{root.tag}>, not <coverage>"
        if not root.findall(".//class"):
            return "records no files"
        return None

    text = report.read_text(encoding="utf-8", errors="replace")
    if "SF:" not in text:
        return "carries no SF: records, so it measures no files"
    return None


def _reports() -> int:
    paths = _report_paths()
    if not paths:
        # Otherwise this passes by having nothing to check, which is the same
        # failure as the missing report it is here to catch.
        print(
            f"FAIL: {SONAR_PROPERTIES.name} declares no *.reportPaths, so this check "
            f"would pass without looking at anything.",
            file=sys.stderr,
        )
        return 1

    problems = []
    for key, reports in sorted(paths.items()):
        for report in reports:
            complaint = _describe(report)
            relative = report.relative_to(ROOT)
            if complaint:
                problems.append(f"{key} -> {relative} {complaint}")
            else:
                print(f"ok: {key} -> {relative}")

    if problems:
        print(
            "FAIL: the scanner would read these paths and find nothing, and SonarCloud "
            "reports that as a warning rather than a failure:",
            file=sys.stderr,
        )
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subcommands = parser.add_subparsers(dest="command", required=True)
    ratchet = subcommands.add_parser("ratchet", help="compare coverage.xml against the tracked baseline")
    ratchet.add_argument("--write", action="store_true", help="re-freeze the baseline at the measured value")
    subcommands.add_parser("reports", help="check every report sonar-project.properties names")

    # No path arguments, for the reason check_lock_wheels.py takes none: a path
    # off the command line is a path this script would then open, which is what
    # pythonsecurity:S8707 is about. Both files it reads are fixed.
    arguments = parser.parse_args(argv)
    return _ratchet(write=arguments.write) if arguments.command == "ratchet" else _reports()


if __name__ == "__main__":
    raise SystemExit(main())
