"""Place the bundled reference texts in the shared corpus and index them.

    python scripts/index_bundled_corpus.py            # index what is not indexed yet
    python scripts/index_bundled_corpus.py --force    # re-index every bundled file
    docker compose exec backend python scripts/index_bundled_corpus.py

The texts live in `config/corpus/<agent class>/` (today: the four regulations the
compliance specialist reviews against). The init service already copies them
into `data/docs/`; this embeds them, which needs the embedding model and takes a
few minutes, so it runs when an administrator asks rather than on every start.
A file an administrator edited in `data/docs/` is never overwritten.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="re-index every bundled file, not only new ones")
    arguments = parser.parse_args(argv)

    from app.core.config import get_settings
    from app.services.documents.bundled_corpus import index_bundled_corpus

    report = index_bundled_corpus(get_settings().docs_path, force=arguments.force)
    for label, paths in (
        ("copied", report.copied),
        ("indexed", report.indexed),
        ("already indexed", report.already_indexed),
    ):
        for path in paths:
            print(f"{label}: {path}")
    print(f"{len(report.indexed)} indexed, {len(report.already_indexed)} already indexed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
