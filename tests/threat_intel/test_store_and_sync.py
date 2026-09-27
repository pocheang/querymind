"""Syncing replaces a source atomically, never with nothing, once at a time, and says how current it is."""

from __future__ import annotations

import gzip
import json
import shutil
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.services.runtime.file_locks import held
from app.services.threat_intel.status import source_statuses
from app.services.threat_intel.store import ThreatIntelStore
from app.services.threat_intel.sync import sync_source

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "threat_intel"


@pytest.fixture
def import_dir(tmp_path: Path) -> Path:
    """The fixtures laid out the way `--from-dir` expects them."""

    directory = tmp_path / "import"
    (directory / "nvd").mkdir(parents=True)
    shutil.copy(FIXTURES / "kev.json", directory / "known_exploited_vulnerabilities.json")
    (directory / "epss_scores-current.csv.gz").write_bytes(gzip.compress((FIXTURES / "epss.csv").read_bytes()))
    shutil.copy(FIXTURES / "enterprise-attack.json", directory / "enterprise-attack.json")
    shutil.copy(FIXTURES / "nvd_page.json", directory / "nvd" / "page-0001.json")
    return directory


@pytest.fixture
def store(tmp_path: Path) -> ThreatIntelStore:
    return ThreatIntelStore(tmp_path / "threat_intel.db")


def test_every_source_syncs_from_an_import_directory(store, import_dir):
    results = {source: sync_source(source, store, from_dir=import_dir) for source in ("nvd", "kev", "epss", "attack")}

    assert {source: result.status for source, result in results.items()} == dict.fromkeys(results, "succeeded")
    cve = store.cve("cve-2021-44228")
    assert cve["cve"]["cvss_score"] == 10.0
    assert cve["kev"]["date_added"] == "2021-12-10"
    assert cve["epss"]["as_of"] == "2026-09-26"
    assert [m["mitigation_id"] for m in store.technique("T1190")["mitigations"]][:2] == ["M1016", "M1026"]


def test_a_feed_that_parses_to_nothing_does_not_replace_a_working_table(store, import_dir):
    """An outage, a format change or a captive-portal page must not delete the database."""

    assert sync_source("kev", store, from_dir=import_dir).status == "succeeded"
    (import_dir / "known_exploited_vulnerabilities.json").write_text(
        json.dumps({"vulnerabilities": []}), encoding="utf-8"
    )

    result = sync_source("kev", store, from_dir=import_dir)

    assert result.status == "failed" and "no entries" in result.detail
    assert store.counts()["kev"] == 12


def test_a_failure_part_way_through_a_write_rolls_the_whole_source_back(store, import_dir):
    assert sync_source("kev", store, from_dir=import_dir).status == "succeeded"
    payload = json.loads((FIXTURES / "kev.json").read_text(encoding="utf-8"))
    payload["vulnerabilities"].append(dict(payload["vulnerabilities"][0]))  # a duplicate primary key, mid-insert
    (import_dir / "known_exploited_vulnerabilities.json").write_text(json.dumps(payload), encoding="utf-8")

    result = sync_source("kev", store, from_dir=import_dir)

    assert result.status == "failed" and "IntegrityError" in result.detail
    assert store.counts()["kev"] == 12, "the previous table is exactly as it was"


def test_a_second_sync_of_the_same_source_is_busy_not_queued(store, import_dir):
    """Held from another thread, the way a second worker would hold it (the lock is re-entrant per thread)."""

    lock = store.db_path.with_name(f"{store.db_path.name}.kev.sync.lock")
    acquired, release = threading.Event(), threading.Event()

    def hold() -> None:
        with held(lock):
            acquired.set()
            release.wait(10)

    holder = threading.Thread(target=hold)
    holder.start()
    try:
        assert acquired.wait(10)
        result = sync_source("kev", store, from_dir=import_dir)
    finally:
        release.set()
        holder.join(10)

    assert result.status == "busy"
    assert store.last_run("kev") is None, "a refused sync starts no run"


def test_every_attempt_is_recorded_with_its_reason(store, import_dir):
    (import_dir / "enterprise-attack.json").unlink()

    sync_source("attack", store, from_dir=import_dir)

    run = store.last_run("attack")
    assert run.status == "failed" and "enterprise-attack.json not found" in run.detail


def test_nvd_resumes_from_its_cursor(store, import_dir):
    """A first sync without an API key takes hours; interrupted, it must not start over."""

    assert sync_source("nvd", store, from_dir=import_dir).status == "succeeded"
    cursor = store.last_run("nvd", successful=True).cursor
    newest = max(
        v["cve"]["lastModified"] for v in json.loads((FIXTURES / "nvd_page.json").read_text())["vulnerabilities"]
    )
    assert cursor == newest, "the cursor is the newest modification seen"

    asked: list[datetime | None] = []

    def pages(since, *, proxy=None):
        asked.append(since)
        return []

    assert sync_source("nvd", store, pages=pages).status == "succeeded"
    assert asked and asked[0] == datetime.fromisoformat(cursor).replace(tzinfo=UTC)


def test_an_interrupted_nvd_sync_keeps_what_it_committed(store, import_dir):
    page = (FIXTURES / "nvd_page.json").read_bytes()

    def pages(since, *, proxy=None):
        yield page
        raise ConnectionError("network went away")

    result = sync_source("nvd", store, pages=pages)

    assert result.status == "failed"
    assert store.counts()["nvd"] == 2, "each page is its own transaction"


def test_status_is_per_source_and_goes_stale_on_its_own_threshold(store, import_dir):
    for source in ("kev", "attack"):
        sync_source(source, store, from_dir=import_dir)
    settings = get_settings()
    later = datetime.now(UTC) + timedelta(days=settings.threat_intel_stale_days_kev + 1)

    statuses = {status.source: status for status in source_statuses(store, settings, now=later)}

    assert statuses["kev"].state == "stale"
    assert statuses["attack"].state == "current", "ATT&CK has a longer threshold of its own"
    assert statuses["nvd"].state == "empty" and statuses["nvd"].last_success == ""
    assert statuses["attack"].data_version == "19.2"


def test_an_unknown_source_is_an_error():
    with pytest.raises(ValueError):
        sync_source("osv", ThreatIntelStore.__new__(ThreatIntelStore))
