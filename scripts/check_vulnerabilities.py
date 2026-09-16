#!/usr/bin/env python
"""Known vulnerabilities in what this project ships, against a list of named exemptions.

`pip-audit` answers "which locked packages have advisories". It cannot answer
"which of those have we looked at", and the usual way that question gets answered
-- `--ignore-vuln ID` on a command line, with a comment -- rots in the two
directions this repository keeps recording: the ignored advisory gets a fix and
nobody notices, and the ignored advisory goes away entirely and the exemption
lives on, pointing at nothing, looking like a real risk somebody accepted.

So the exemptions live in `scripts/vulnerability-exemptions.json`, keyed by
advisory id, each with the package it belongs to and a reason, and all three
failure directions are checked:

* an advisory nobody has exempted  -> fail, this is the point of the scan;
* an exemption whose advisory now has a fix -> fail, take the fix (declare
  `"fix_exists": true` with a rewritten reason if it genuinely cannot be taken);
* an exemption that matches no current finding -> fail, delete it.

The third is the ratchet rule this repository already applies to
`SECRET_BASELINE` in `check_sensitive.py` and `KNOWN_OFFENDERS` in
`tests/security/`: an exemption list may only shrink on its own.

**`requirements/runtime.txt` only**, which is what the image installs and
therefore what a user of this system is exposed to. `ci.txt` adds the dev
toolchain, whose advisories move for reasons that have nothing to do with what
runs in production; auditing it means a second exemption list with a different
risk model, and that is a decision to take deliberately rather than by passing
another path here.

    python scripts/check_vulnerabilities.py

Takes no arguments, for the reason `check_lock_wheels.py` takes none: a path on
the command line is a path this script would then open. It needs the network
(the advisory database is fetched), so it is a CI job rather than a test.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "requirements" / "runtime.txt"
EXEMPTIONS = Path(__file__).resolve().parent / "vulnerability-exemptions.json"


def audit(raw: str | None = None) -> list[tuple[str, str, str, tuple[str, ...]]]:
    """(package, version, advisory id, fix versions) for everything pip-audit reports.

    `raw` is the JSON document, for tests; without it pip-audit is run. `--no-deps`
    is correct here and not a shortcut: the file is a fully pinned export of
    `uv.lock`, so resolving it again would only invite a different answer than the
    one the image installs.
    """

    if raw is None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip_audit",
                "--format",
                "json",
                "--no-deps",
                "--requirement",
                str(REQUIREMENTS),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        # pip-audit exits 1 when it finds anything, which is not an error here --
        # the findings are the output. A missing tool or an unreachable database
        # is, and both leave the document unparseable.
        raw = completed.stdout
        if not raw.strip():
            raise SystemExit(f"pip-audit produced no output; stderr was:\n{completed.stderr}")

    findings = []
    for dependency in json.loads(raw).get("dependencies", []):
        for vulnerability in dependency.get("vulns", []):
            findings.append(
                (
                    dependency["name"],
                    dependency["version"],
                    vulnerability["id"],
                    tuple(vulnerability.get("fix_versions") or ()),
                )
            )
    return sorted(findings)


def evaluate(findings, exemptions) -> list[str]:
    """Every reason this should fail, so one run reports all of them."""

    problems = []
    seen = set()

    for package, version, identifier, fixes in findings:
        seen.add(identifier)
        exemption = exemptions.get(identifier)
        if exemption is None:
            fix = f", fixed in {', '.join(fixes)}" if fixes else ", no fix published"
            problems.append(f"unreviewed: {package} {version} {identifier}{fix}")
            continue
        if exemption.get("package") != package:
            problems.append(
                f"mismatched: {identifier} is exempted for {exemption.get('package')!r} "
                f"but was reported against {package!r}"
            )
        if fixes and not exemption.get("fix_exists"):
            problems.append(
                f"fixable: {package} {version} {identifier} now has a fix "
                f'({", ".join(fixes)}) -- upgrade with `make lock`, or set "fix_exists": true '
                f"with a reason saying why the fix cannot be taken"
            )

    for identifier, exemption in sorted(exemptions.items()):
        if identifier not in seen:
            problems.append(
                f"stale: {identifier} ({exemption.get('package')}) is exempted but nothing "
                f"reports it any more -- delete the entry"
            )
    return problems


def main() -> int:
    exemptions = json.loads(EXEMPTIONS.read_text(encoding="utf-8"))
    exemptions.pop("_comment", None)
    findings = audit()

    print(f"{len(findings)} advisory/advisories across {REQUIREMENTS.relative_to(ROOT)}:")
    for package, version, identifier, fixes in findings:
        mark = "exempt " if identifier in exemptions else "NEW    "
        print(f"  {mark} {package} {version} {identifier} {'fix: ' + ', '.join(fixes) if fixes else ''}")

    problems = evaluate(findings, exemptions)
    if problems:
        print("\nFAIL:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    print(f"\nall {len(findings)} accounted for by {EXEMPTIONS.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
