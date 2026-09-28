"""Reference texts that ship with the application, placed into the shared corpus.

`config/corpus/<agent class>/` holds them in the repository -- today the four
regulations the compliance specialist reviews against (网络安全法, 数据安全法,
个人信息保护法, GDPR), all of them texts no copyright covers. `data/docs/` is
the shared corpus every user may read, and a file in its `<agent class>/`
folder is labelled with that class (`domain_labels.folder_label`), so these
texts become compliance material without a registry row.

Two steps, deliberately separate:

- `install` copies a bundled file into the shared corpus when it is missing
  there, and never overwrites one that exists: an administrator who edited or
  replaced a text keeps their version. The init service runs it on every
  deployment, which costs a directory listing.
- `index` embeds what `install` placed. Not on startup: it needs the embedding
  model and takes minutes, and a deployment that never asks a compliance
  question should not pay for it. `scripts/index_bundled_corpus.py` runs it.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

BUNDLED_ROOT = Path(__file__).resolve().parents[3] / "config" / "corpus"

__all__ = ["BUNDLED_ROOT", "BundledCorpusReport", "bundled_files", "index_bundled_corpus", "install_bundled_corpus"]


@dataclass
class BundledCorpusReport:
    copied: list[Path] = field(default_factory=list)
    kept: list[Path] = field(default_factory=list)
    indexed: list[Path] = field(default_factory=list)
    already_indexed: list[Path] = field(default_factory=list)


def bundled_files(root: Path = BUNDLED_ROOT) -> list[tuple[Path, Path]]:
    """Every bundled file, with its path relative to the bundle root, in a stable order."""

    if not root.is_dir():
        return []
    return [(path, path.relative_to(root)) for path in sorted(root.rglob("*")) if path.is_file()]


def install_bundled_corpus(docs_path: Path, root: Path = BUNDLED_ROOT) -> BundledCorpusReport:
    """Copy each bundled file into the shared corpus if it is not there yet."""

    report = BundledCorpusReport()
    for source, relative in bundled_files(root):
        target = docs_path / relative
        if target.exists():
            report.kept.append(target)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        # Copied to a temporary name and renamed, so a reader never sees half a file.
        partial = target.with_name(f".{target.name}.partial")
        shutil.copyfile(source, partial)
        partial.replace(target)
        report.copied.append(target)
    return report


def _indexed_sources() -> set[str]:
    from app.retrievers.stores.corpus import read_corpus_records

    sources: set[str] = set()
    for row in read_corpus_records():
        source = str((row.get("metadata") or {}).get("source") or row.get("source") or "")
        if source:
            sources.add(str(Path(source).resolve()))
    return sources


def index_bundled_corpus(docs_path: Path, *, force: bool = False, root: Path = BUNDLED_ROOT) -> BundledCorpusReport:
    """Install, then index the installed bundled files the corpus does not hold yet (all of them with `force`)."""

    from app.services.documents.ingest import ingest_paths

    report = install_bundled_corpus(docs_path, root)
    installed = [docs_path / relative for _, relative in bundled_files(root)]
    held = set() if force else _indexed_sources()
    todo = [path for path in installed if str(path.resolve()) not in held]
    report.already_indexed = [path for path in installed if path not in todo]
    if todo:
        ingest_paths(todo)
        report.indexed = todo
    return report
