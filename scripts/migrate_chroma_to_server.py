#!/usr/bin/env python
"""Copy the embedded Chroma store into the Chroma server.

    conda run -n rag-local python scripts/migrate_chroma_to_server.py --dry-run
    conda run -n rag-local python scripts/migrate_chroma_to_server.py

Run it before setting `CHROMA_SERVER_URL` on an installation that already has
vectors in `CHROMA_PERSIST_DIR` (which `STATE_BACKEND=shared` requires, ARC-01
phase 5). Both come from the configuration the server uses; `--server` overrides
the URL, for copying into a server the running application does not point at yet.

Safe to repeat: vectors are upserted by id, nothing is re-embedded, and the
embedded directory is never modified. Exit 0 only when every id in every source
collection reads back from the server. See `app/retrievers/stores/chroma_migration.py`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--server", default="", help="Chroma server URL; defaults to CHROMA_SERVER_URL")
    parser.add_argument("--dry-run", action="store_true", help="list the source collections and counts, copy nothing")
    args = parser.parse_args(argv)

    import chromadb

    from app.core.config import get_settings
    from app.retrievers.stores.chroma_migration import copy_collections, describe_collections
    from app.retrievers.stores.vector import chroma_http_client

    settings = get_settings()
    source = chromadb.PersistentClient(path=str(settings.chroma_path))
    if args.dry_run:
        for name, count in describe_collections(source).items():
            print(f"{name:<40} {count:>8}")
        return 0

    server_url = (args.server or settings.chroma_server_url or "").strip()
    if not server_url:
        print("No server: set CHROMA_SERVER_URL or pass --server.", file=sys.stderr)
        return 2
    reports = copy_collections(source, chroma_http_client(server_url))
    for report in reports:
        state = "ok" if report.verified else "INCOMPLETE"
        print(f"{report.name:<40} {report.copied:>8}/{report.source_count:<8} {state}")
        for identifier in report.missing_after[:20]:
            print(f"    NOT FOUND AFTER COPY  {identifier}")
    return 0 if all(report.verified for report in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
