"""The local threat-intelligence database, and the only code that reads or writes it.

One SQLite file (`THREAT_INTEL_DB_PATH`), versioned like every other store
(`app/services/runtime/sqlite_schema.py`) and listed in `schema_targets`.

**Each source is replaced in one transaction.** The plan asked for staging
tables swapped in atomically; a single `BEGIN IMMEDIATE` in a WAL database gives
the same guarantee with less machinery: a sync that fails part-way rolls back
and the previous data is exactly as it was, and readers keep reading the last
committed snapshot while a sync runs. NVD is the exception by necessity -- it is
synced incrementally by modification date -- and each of its pages is its own
transaction, recorded with a cursor so an interrupted sync resumes rather than
restarts.

Every run, successful or not, is a row in `sync_runs`; `status()` reports from
there, never from a guess.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.services.runtime.sqlite_schema import Migration, ensure_schema
from app.services.threat_intel.parsers import AttackBundle, CveRecord, EpssRecord, KevRecord

__all__ = ["SOURCES", "SyncRun", "THREAT_INTEL_MIGRATIONS", "ThreatIntelStore"]

SOURCES: tuple[str, ...] = ("nvd", "kev", "epss", "attack")


def _baseline(conn: sqlite3.Connection) -> None:
    for statement in (
        """CREATE TABLE IF NOT EXISTS cve (
            cve_id TEXT PRIMARY KEY, published TEXT NOT NULL, last_modified TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT '', cvss_version TEXT NOT NULL DEFAULT '',
            cvss_score REAL, cvss_vector TEXT NOT NULL DEFAULT '', severity TEXT NOT NULL DEFAULT '',
            cvss_source TEXT NOT NULL DEFAULT '', cwe TEXT NOT NULL DEFAULT '')""",
        """CREATE TABLE IF NOT EXISTS cve_cpe (
            cve_id TEXT NOT NULL REFERENCES cve(cve_id) ON DELETE CASCADE,
            vendor TEXT NOT NULL, product TEXT NOT NULL, version TEXT NOT NULL,
            start_including TEXT NOT NULL DEFAULT '', start_excluding TEXT NOT NULL DEFAULT '',
            end_including TEXT NOT NULL DEFAULT '', end_excluding TEXT NOT NULL DEFAULT '')""",
        "CREATE INDEX IF NOT EXISTS idx_cve_cpe_product ON cve_cpe(product, vendor)",
        "CREATE INDEX IF NOT EXISTS idx_cve_cpe_cve ON cve_cpe(cve_id)",
        """CREATE TABLE IF NOT EXISTS kev (
            cve_id TEXT PRIMARY KEY, vendor TEXT NOT NULL, product TEXT NOT NULL, name TEXT NOT NULL,
            date_added TEXT NOT NULL, due_date TEXT NOT NULL, known_ransomware TEXT NOT NULL,
            required_action TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS epss (
            cve_id TEXT PRIMARY KEY, score REAL NOT NULL, percentile REAL NOT NULL, as_of TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS attack_technique (
            technique_id TEXT PRIMARY KEY, name TEXT NOT NULL, tactics TEXT NOT NULL,
            is_subtechnique INTEGER NOT NULL, parent_id TEXT NOT NULL, platforms TEXT NOT NULL,
            url TEXT NOT NULL, summary TEXT NOT NULL, revoked INTEGER NOT NULL, deprecated INTEGER NOT NULL)""",
        "CREATE INDEX IF NOT EXISTS idx_attack_name ON attack_technique(name COLLATE NOCASE)",
        """CREATE TABLE IF NOT EXISTS attack_mitigation (
            technique_id TEXT NOT NULL, mitigation_id TEXT NOT NULL, name TEXT NOT NULL,
            PRIMARY KEY (technique_id, mitigation_id))""",
        """CREATE TABLE IF NOT EXISTS attack_detection (
            technique_id TEXT NOT NULL, strategy_id TEXT NOT NULL, name TEXT NOT NULL,
            PRIMARY KEY (technique_id, strategy_id, name))""",
        """CREATE TABLE IF NOT EXISTS sync_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT NOT NULL, started_at TEXT NOT NULL,
            finished_at TEXT NOT NULL DEFAULT '', status TEXT NOT NULL, record_count INTEGER NOT NULL DEFAULT 0,
            rejected_count INTEGER NOT NULL DEFAULT 0, sha256 TEXT NOT NULL DEFAULT '',
            cursor TEXT NOT NULL DEFAULT '', data_version TEXT NOT NULL DEFAULT '', detail TEXT NOT NULL DEFAULT '')""",
        "CREATE INDEX IF NOT EXISTS idx_sync_runs_source ON sync_runs(source, id)",
    ):
        conn.execute(statement)


THREAT_INTEL_MIGRATIONS = (Migration(1, "baseline: cve, kev, epss, attack, sync_runs", _baseline),)


@dataclass(frozen=True)
class SyncRun:
    source: str
    status: str
    started_at: str
    finished_at: str
    record_count: int
    rejected_count: int
    sha256: str
    cursor: str
    data_version: str
    detail: str


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class ThreatIntelStore:
    """Read and replace threat-intelligence data. One connection per call, as every store here."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        ensure_schema(self.db_path, "threat_intel", THREAT_INTEL_MIGRATIONS, wal=True)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        with closing(conn):
            yield conn

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise

    # --- writes ----------------------------------------------------------------------

    def upsert_cves(self, records: Iterable[CveRecord]) -> int:
        """Insert or replace CVEs and their CPE ranges -- one NVD page, one transaction."""

        count = 0
        with self._transaction() as conn:
            for record in records:
                conn.execute("DELETE FROM cve_cpe WHERE cve_id=?", (record.cve_id,))
                conn.execute(
                    "INSERT OR REPLACE INTO cve VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        record.cve_id,
                        record.published,
                        record.last_modified,
                        record.status,
                        record.cvss_version,
                        record.cvss_score,
                        record.cvss_vector,
                        record.severity,
                        record.cvss_source,
                        ",".join(record.cwe),
                    ),
                )
                conn.executemany(
                    "INSERT INTO cve_cpe VALUES (?,?,?,?,?,?,?,?)",
                    [
                        (
                            record.cve_id,
                            r.vendor,
                            r.product,
                            r.version,
                            r.start_including,
                            r.start_excluding,
                            r.end_including,
                            r.end_excluding,
                        )
                        for r in record.ranges
                    ],
                )
                count += 1
        return count

    def replace_kev(self, records: Iterable[KevRecord]) -> int:
        rows = [tuple(vars(record).values()) for record in records]
        with self._transaction() as conn:
            conn.execute("DELETE FROM kev")
            conn.executemany("INSERT INTO kev VALUES (?,?,?,?,?,?,?,?)", rows)
        return len(rows)

    def replace_epss(self, records: Iterable[EpssRecord], as_of: str) -> int:
        rows = [(record.cve_id, record.score, record.percentile, as_of) for record in records]
        with self._transaction() as conn:
            conn.execute("DELETE FROM epss")
            conn.executemany("INSERT INTO epss VALUES (?,?,?,?)", rows)
        return len(rows)

    def replace_attack(self, bundle: AttackBundle) -> int:
        with self._transaction() as conn:
            for table in ("attack_technique", "attack_mitigation", "attack_detection"):
                conn.execute(f"DELETE FROM {table}")  # noqa: S608 -- a fixed tuple of this module's own tables
            conn.executemany(
                "INSERT INTO attack_technique VALUES (?,?,?,?,?,?,?,?,?,?)",
                [
                    (
                        t.technique_id,
                        t.name,
                        ",".join(t.tactics),
                        int(t.is_subtechnique),
                        t.parent_id,
                        ",".join(t.platforms),
                        t.url,
                        t.summary,
                        int(t.revoked),
                        int(t.deprecated),
                    )
                    for t in bundle.techniques
                ],
            )
            conn.executemany(
                "INSERT OR IGNORE INTO attack_mitigation VALUES (?,?,?)",
                [(m.technique_id, m.mitigation_id, m.name) for m in bundle.mitigations],
            )
            conn.executemany(
                "INSERT OR IGNORE INTO attack_detection VALUES (?,?,?)",
                [(d.technique_id, d.strategy_id, d.name) for d in bundle.detections],
            )
        return len(bundle.techniques)

    def start_run(self, source: str) -> int:
        with self._transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO sync_runs(source, started_at, status) VALUES (?,?,?)", (source, _now(), "running")
            )
            return int(cursor.lastrowid)

    def finish_run(
        self,
        run_id: int,
        *,
        status: str,
        record_count: int = 0,
        rejected_count: int = 0,
        sha256: str = "",
        cursor: str = "",
        data_version: str = "",
        detail: str = "",
    ) -> None:
        with self._transaction() as conn:
            conn.execute(
                """UPDATE sync_runs SET finished_at=?, status=?, record_count=?, rejected_count=?, sha256=?,
                   cursor=?, data_version=?, detail=? WHERE id=?""",
                (_now(), status, record_count, rejected_count, sha256, cursor, data_version, detail[:500], run_id),
            )

    # --- reads -------------------------------------------------------------------------

    def last_run(self, source: str, *, successful: bool = False) -> SyncRun | None:
        query = "SELECT * FROM sync_runs WHERE source=?" + (" AND status='succeeded'" if successful else "")
        with self._connect() as conn:
            row = conn.execute(query + " ORDER BY id DESC LIMIT 1", (source,)).fetchone()
        if row is None:
            return None
        return SyncRun(**{key: row[key] for key in SyncRun.__dataclass_fields__})

    def counts(self) -> dict[str, int]:
        with self._connect() as conn:
            return {
                "nvd": conn.execute("SELECT COUNT(*) FROM cve").fetchone()[0],
                "kev": conn.execute("SELECT COUNT(*) FROM kev").fetchone()[0],
                "epss": conn.execute("SELECT COUNT(*) FROM epss").fetchone()[0],
                "attack": conn.execute("SELECT COUNT(*) FROM attack_technique WHERE revoked=0").fetchone()[0],
            }

    def cve(self, cve_id: str) -> dict | None:
        """One CVE with its KEV and EPSS entries, or None when the store does not hold it."""

        key = cve_id.strip().upper()
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM cve WHERE cve_id=?", (key,)).fetchone()
            kev = conn.execute("SELECT * FROM kev WHERE cve_id=?", (key,)).fetchone()
            epss = conn.execute("SELECT * FROM epss WHERE cve_id=?", (key,)).fetchone()
            ranges = conn.execute("SELECT * FROM cve_cpe WHERE cve_id=? ORDER BY vendor, product", (key,)).fetchall()
        if row is None and kev is None:
            return None
        return {
            "cve": dict(row) if row else None,
            "kev": dict(kev) if kev else None,
            "epss": dict(epss) if epss else None,
            "ranges": [dict(r) for r in ranges],
        }

    def product_ranges(self, product: str, vendor: str | None = None, limit: int = 2000) -> list[dict]:
        """Every vulnerable CPE range naming this product, joined to its CVE, KEV and EPSS rows."""

        query = """SELECT cve_cpe.*, cve.cvss_score, cve.severity, cve.published,
                          kev.date_added AS kev_added, kev.known_ransomware, epss.score AS epss_score,
                          epss.percentile AS epss_percentile
                   FROM cve_cpe JOIN cve USING (cve_id)
                   LEFT JOIN kev USING (cve_id) LEFT JOIN epss USING (cve_id)
                   WHERE cve_cpe.product=?"""
        params: list = [product.strip().lower()]
        if vendor:
            query += " AND cve_cpe.vendor=?"
            params.append(vendor.strip().lower())
        with self._connect() as conn:
            return [dict(r) for r in conn.execute(query + " LIMIT ?", (*params, limit)).fetchall()]

    def technique(self, technique_id: str) -> dict | None:
        key = technique_id.strip().upper()
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM attack_technique WHERE technique_id=?", (key,)).fetchone()
            if row is None:
                return None
            mitigations = conn.execute(
                "SELECT mitigation_id, name FROM attack_mitigation WHERE technique_id=? ORDER BY mitigation_id", (key,)
            ).fetchall()
            detections = conn.execute(
                "SELECT strategy_id, name FROM attack_detection WHERE technique_id=? ORDER BY strategy_id", (key,)
            ).fetchall()
            subtechniques = conn.execute(
                "SELECT technique_id, name FROM attack_technique WHERE parent_id=? AND revoked=0 ORDER BY technique_id",
                (key,),
            ).fetchall()
        return {
            **dict(row),
            "mitigations": [dict(m) for m in mitigations],
            "detections": [dict(d) for d in detections],
            "subtechniques": [dict(s) for s in subtechniques],
        }

    def techniques_in_tactic(self, tactic: str, limit: int = 60) -> list[dict]:
        """Current parent techniques under a tactic, by ATT&CK's phase name ("initial-access")."""

        # Letters and hyphens only: this goes into a LIKE pattern, where % and _ are wildcards.
        phase = "".join(
            ch for ch in "-".join(tactic.strip().lower().replace("_", " ").split()) if ch.isalpha() or ch == "-"
        )
        if not phase:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT technique_id, name FROM attack_technique
                   WHERE revoked=0 AND deprecated=0 AND is_subtechnique=0
                     AND (',' || tactics || ',') LIKE ? ORDER BY technique_id LIMIT ?""",
                (f"%,{phase},%", limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def technique_by_name(self, name: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT technique_id FROM attack_technique WHERE name=? COLLATE NOCASE AND revoked=0",
                (name.strip(),),
            ).fetchone()
        return str(row[0]) if row else None
