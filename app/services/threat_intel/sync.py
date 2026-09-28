"""Bring one source up to date: fetch or read, parse, replace, record.

Three rules decide how this can fail, and each is here because the opposite
failure is the quiet one:

- **Nothing never replaces something.** A feed that parses to zero rows is a
  failed sync, not an empty table: an outage, a changed format or a captive
  portal page would otherwise delete a working database.
- **One sync per source at a time, across processes.** A second request while
  one runs is answered `busy` at once rather than queued behind it.
- **Every attempt is recorded**, succeeded or failed, with the reason; the
  admin page and the tools read status from there.

`from_dir` is the offline path for a machine with no route to the feeds: the
same files, downloaded elsewhere and copied in. It is resolved and contained by
the caller (the CLI), which is where the path is untrusted.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.services.runtime.file_locks import LockBusy, held
from app.services.threat_intel.download import FEEDS, decompress_if_gzip, download, nvd_pages
from app.services.threat_intel.parsers import parse_attack_bundle, parse_epss_csv, parse_kev, parse_nvd_page
from app.services.threat_intel.store import SOURCES, ThreatIntelStore

logger = logging.getLogger(__name__)

__all__ = ["SyncResult", "sync_source"]

_MAX_EXPANDED_EPSS = 120_000_000


@dataclass(frozen=True)
class SyncResult:
    source: str
    status: str  # succeeded | failed | busy
    record_count: int = 0
    rejected_count: int = 0
    detail: str = ""


@dataclass(frozen=True)
class _Outcome:
    records: int
    rejected: int
    sha256: str = ""
    cursor: str = ""
    data_version: str = ""


class EmptyFeed(RuntimeError):
    """A feed that parsed to nothing. Refused, so it cannot replace a working table."""


def sync_source(
    source: str,
    store: ThreatIntelStore,
    *,
    from_dir: Path | None = None,
    proxy: str | None = None,
    fetch: Callable[..., bytes] = download,
    pages: Callable[..., Iterable[bytes]] = nvd_pages,
) -> SyncResult:
    if source not in SOURCES:
        raise ValueError(f"unknown source: {source}")
    lock = store.db_path.with_name(f"{store.db_path.name}.{source}.sync.lock")
    try:
        with held(lock, timeout=0):
            return _run(source, store, from_dir=from_dir, proxy=proxy, fetch=fetch, pages=pages)
    except LockBusy:
        return SyncResult(source, "busy", detail="a sync of this source is already running")


def _run(source, store, *, from_dir, proxy, fetch, pages) -> SyncResult:
    run_id = store.start_run(source)
    try:
        if source == "nvd":
            outcome = _sync_nvd(store, run_id, from_dir=from_dir, proxy=proxy, pages=pages)
        else:
            outcome = _SYNCERS[source](store, _feed_bytes(source, from_dir=from_dir, proxy=proxy, fetch=fetch))
    except Exception as error:  # noqa: BLE001 -- recorded and returned, never swallowed silently
        detail = f"{type(error).__name__}: {error}"[:500]
        store.finish_run(run_id, status="failed", detail=detail)
        logger.warning("threat intel sync failed: source=%s %s", source, detail)
        return SyncResult(source, "failed", detail=detail)
    store.finish_run(
        run_id,
        status="succeeded",
        record_count=outcome.records,
        rejected_count=outcome.rejected,
        sha256=outcome.sha256,
        cursor=outcome.cursor,
        data_version=outcome.data_version,
    )
    logger.info("threat intel sync: source=%s records=%d rejected=%d", source, outcome.records, outcome.rejected)
    return SyncResult(source, "succeeded", outcome.records, outcome.rejected)


def _feed_bytes(source: str, *, from_dir: Path | None, proxy: str | None, fetch) -> bytes:
    feed = FEEDS[source]
    if from_dir is not None:
        path = from_dir / feed.filename
        if not path.is_file():
            raise FileNotFoundError(f"{feed.filename} not found in the import directory")
        if path.stat().st_size > feed.max_bytes:
            raise ValueError(f"{feed.filename} is larger than the {feed.max_bytes:,}-byte ceiling")
        return path.read_bytes()
    return fetch(feed.url, max_bytes=feed.max_bytes, proxy=proxy)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sync_kev(store: ThreatIntelStore, data: bytes) -> _Outcome:
    payload = json.loads(data)
    parsed = parse_kev(payload)
    if not parsed.rows:
        raise EmptyFeed("KEV parsed to no entries")
    return _Outcome(
        store.replace_kev(parsed.rows),
        parsed.rejected,
        _sha(data),
        data_version=str(payload.get("catalogVersion") or "")[:40],
    )


def _sync_epss(store: ThreatIntelStore, data: bytes) -> _Outcome:
    text = decompress_if_gzip(data, max_bytes=_MAX_EXPANDED_EPSS).decode("utf-8")
    as_of, parsed = parse_epss_csv(text)
    if not parsed.rows:
        raise EmptyFeed("EPSS parsed to no scores")
    return _Outcome(store.replace_epss(parsed.rows, as_of), parsed.rejected, _sha(data), data_version=as_of)


def _sync_attack(store: ThreatIntelStore, data: bytes) -> _Outcome:
    bundle = parse_attack_bundle(json.loads(data))
    if not bundle.techniques:
        raise EmptyFeed("ATT&CK bundle holds no techniques")
    return _Outcome(store.replace_attack(bundle), bundle.rejected, _sha(data), data_version=bundle.version)


_SYNCERS: dict[str, Callable[[ThreatIntelStore, bytes], _Outcome]] = {
    "kev": _sync_kev,
    "epss": _sync_epss,
    "attack": _sync_attack,
}


def _sync_nvd(store: ThreatIntelStore, run_id: int, *, from_dir: Path | None, proxy: str | None, pages) -> _Outcome:
    """Page by page, each page committed, the cursor recorded as it advances.

    The cursor is the newest `lastModified` seen, so an interrupted first sync
    (hours without an API key) resumes from where it got to instead of
    starting over; the next sync asks NVD only for what changed since.
    """

    previous = store.last_run("nvd", successful=True)
    since = _parse_cursor(previous.cursor) if previous else None
    source_pages = _local_nvd_pages(from_dir) if from_dir is not None else pages(since, proxy=proxy)
    records = rejected = 0
    cursor = previous.cursor if previous else ""
    digest = hashlib.sha256()
    for page in source_pages:
        digest.update(page)
        parsed = parse_nvd_page(json.loads(page))
        records += store.upsert_cves(parsed.rows)
        rejected += parsed.rejected
        cursor = max([cursor, *(row.last_modified for row in parsed.rows)])
        store.finish_run(run_id, status="running", record_count=records, rejected_count=rejected, cursor=cursor)
    if records == 0 and since is None:
        raise EmptyFeed("NVD returned no CVEs on a full sync")
    return _Outcome(records, rejected, digest.hexdigest(), cursor=cursor)


def _local_nvd_pages(from_dir: Path) -> Iterable[bytes]:
    directory = from_dir / "nvd"
    files = sorted(directory.glob("*.json")) if directory.is_dir() else []
    if not files:
        raise FileNotFoundError("no nvd/*.json pages in the import directory")
    for path in files:
        yield path.read_bytes()


def _parse_cursor(cursor: str) -> datetime | None:
    if not cursor:
        return None
    try:
        parsed = datetime.fromisoformat(cursor)
    except ValueError:
        return None
    from datetime import UTC

    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
