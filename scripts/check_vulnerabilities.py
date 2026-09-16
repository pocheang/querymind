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

**Both exports are audited, and an exemption says which.** `runtime.txt` is what
the image installs and therefore what a user of this system is exposed to;
`ci.txt` adds the dev toolchain, which is a different risk -- a compromised test
dependency reaches the machine that builds a release, not the people using it.
The two were kept apart at first on the argument that mixing them means one
exemption list papering over two risk models. The `scope` key is what keeps them
apart without a second file: an entry exempts an advisory for `runtime`, for `ci`,
or for `both`, and an advisory found in a scope its exemption does not name is
unreviewed there. Measured when this landed, every finding is in both (the four
chromadb advisories), so the distinction costs nothing today and exists for the
day a pytest plugin has an advisory nobody should be waving through for the
image.

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
# The scope name is what an exemption's `scope` key names, so these two strings
# are the vocabulary; `both` is the third value an entry may carry.
REQUIREMENTS = {
    "runtime": ROOT / "requirements" / "runtime.txt",
    "ci": ROOT / "requirements" / "ci.txt",
}
EXEMPTIONS = Path(__file__).resolve().parent / "vulnerability-exemptions.json"


def audit(requirements: Path | None = None, raw: str | None = None) -> list[tuple[str, str, str, tuple[str, ...]]]:
    """(package, version, advisory id, fix versions) for everything pip-audit reports.

    `raw` is the JSON document, for tests; without it pip-audit is run over
    `requirements`. `--no-deps` is correct here and not a shortcut: the file is a
    fully pinned export of `uv.lock`, so resolving it again would only invite a
    different answer than the one the image installs.
    """

    if raw is None:
        assert requirements is not None
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip_audit",
                "--format",
                "json",
                "--no-deps",
                "--requirement",
                str(requirements),
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


SCOPES = tuple(REQUIREMENTS)


def exempted_scopes(entry: dict) -> tuple[str, ...]:
    """Which requirement files this entry speaks for.

    `both` rather than a list, because a list invites `["runtime"]` written as
    `"runtime"` and read as five separate one-character scopes.
    """

    scope = entry.get("scope", "both")
    return SCOPES if scope == "both" else (scope,)


def _finding_problems(scope, finding, exemptions) -> list[str]:
    package, version, identifier, fixes = finding
    exemption = exemptions.get(identifier)
    if exemption is None:
        fix = f", fixed in {', '.join(fixes)}" if fixes else ", no fix published"
        return [f"unreviewed: [{scope}] {package} {version} {identifier}{fix}"]

    problems = []
    if scope not in exempted_scopes(exemption):
        problems.append(
            f"out of scope: {identifier} is exempted for "
            f"{', '.join(exempted_scopes(exemption))} but was found in {scope}. Widen its "
            f'"scope" to "both" only if the risk really is the same in both.'
        )
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
    return problems


def _stale_problems(seen: dict[str, set[str]], exemptions) -> list[str]:
    problems = []
    for identifier, entry in sorted(exemptions.items()):
        for scope in exempted_scopes(entry):
            if scope not in seen.get(identifier, set()):
                problems.append(
                    f"stale: {identifier} ({entry.get('package')}) is exempted for {scope} "
                    f"but nothing there reports it any more -- narrow its scope or delete the entry"
                )
    return problems


def evaluate(found: dict[str, list], exemptions) -> list[str]:
    """Every reason this should fail, so one run reports all of them."""

    problems = []
    seen: dict[str, set[str]] = {}
    for scope, findings in sorted(found.items()):
        for finding in findings:
            seen.setdefault(finding[2], set()).add(scope)
            problems.extend(_finding_problems(scope, finding, exemptions))
    return problems + _stale_problems(seen, exemptions)


def _report(found: dict[str, list], exemptions) -> None:
    for scope, findings in sorted(found.items()):
        print(f"{len(findings)} advisory/advisories across {REQUIREMENTS[scope].relative_to(ROOT)}:")
        for package, version, identifier, fixes in findings:
            mark = "exempt " if identifier in exemptions else "NEW    "
            print(f"  {mark} {package} {version} {identifier} {'fix: ' + ', '.join(fixes) if fixes else ''}")


def main() -> int:
    exemptions = json.loads(EXEMPTIONS.read_text(encoding="utf-8"))
    exemptions.pop("_comment", None)
    found = {scope: audit(path) for scope, path in REQUIREMENTS.items()}

    _report(found, exemptions)
    problems = evaluate(found, exemptions)
    if problems:
        print("\nFAIL:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    total = sum(len(findings) for findings in found.values())
    print(f"\nall {total} accounted for by {EXEMPTIONS.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
