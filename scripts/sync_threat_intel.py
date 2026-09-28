"""Sync the offline threat-intelligence store from NVD, CISA KEV, FIRST EPSS and MITRE ATT&CK.

    python scripts/sync_threat_intel.py --source all
    python scripts/sync_threat_intel.py --source kev
    python scripts/sync_threat_intel.py --source all --from-dir data/threat-intel-import

Sync is manual by default. A deployment that may reach the internet can run this
from the host's scheduler, for example daily at 03:00:

    0 3 * * *  cd /opt/querymind && docker compose -f deploy/compose/compose.yaml \
               exec -T backend python scripts/sync_threat_intel.py --source all

NVD's first sync pages through every CVE (hundreds of thousands) at NVD's
unauthenticated rate limit, which takes hours; export NVD_API_KEY (a real
environment variable, never a setting) to go about ten times faster. Later syncs
fetch only what changed since the last successful one.

--from-dir is for a machine with no route to the feeds. Put the files, downloaded
elsewhere, under a directory inside this repository:

    known_exploited_vulnerabilities.json
    epss_scores-current.csv.gz      (or the uncompressed .csv renamed to this name)
    enterprise-attack.json
    nvd/*.json                      (NVD CVE API 2.0 response pages)

Exit status: 0 when every requested source synced, 1 when any failed or was busy.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - non-reconfigurable stream
        pass


def import_dir(raw: str) -> Path:
    """The import directory, resolved and then contained in the repository.

    Resolve first, then contain: a `".." not in raw` test is defeated by a
    symlink inside the repository pointing out of it, and by `a/../b`
    normalising to something the substring test never saw
    (`pythonsecurity:S8707`, the rule `scripts/eval_retrieval.py` follows).
    """

    path = Path(raw)
    resolved = (path if path.is_absolute() else Path.cwd() / path).resolve()
    if not resolved.is_relative_to(REPO_ROOT):
        raise SystemExit(f"--from-dir must be inside the repository ({REPO_ROOT}); got {resolved}")
    if not resolved.is_dir():
        raise SystemExit(f"--from-dir is not a directory: {resolved}")
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", choices=("all", "nvd", "kev", "epss", "attack"), default="all")
    parser.add_argument("--from-dir", help="import files from this directory instead of downloading")
    args = parser.parse_args(argv)

    from app.core.config import get_settings
    from app.services.threat_intel.status import get_threat_intel_store, source_statuses
    from app.services.threat_intel.store import SOURCES
    from app.services.threat_intel.sync import sync_source

    from_dir = import_dir(args.from_dir) if args.from_dir else None
    settings = get_settings()
    store = get_threat_intel_store(settings)
    sources = SOURCES if args.source == "all" else (args.source,)
    failed = 0
    for source in sources:
        print(f"syncing {source} ...", flush=True)
        result = sync_source(source, store, from_dir=from_dir, proxy=settings.web_proxy_url or None)
        print(f"  {result.status}: {result.record_count} records, {result.rejected_count} rejected {result.detail}")
        failed += result.status != "succeeded"
    print("\nstatus:")
    for status in source_statuses(store, settings):
        age = "never" if status.age_days is None else f"{status.age_days} days"
        print(
            f"  {status.source:<7} {status.state:<8} {status.records:>8} records  synced {age}  {status.data_version}"
        )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
