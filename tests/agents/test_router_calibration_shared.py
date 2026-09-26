"""Router calibration is one set of counts for every worker (ARC-01 audit, 2026-09-25).

A category-A state in the phase 0 inventory that the plan's table never picked
up. Each process kept its own counts and wrote them out every 20 records as a
whole file, so with two workers each rewrote the file with its own numbers --
erasing the other's -- and each calibrated from different data. The counts are
rows in the application database now, and a worker only ever *adds* to them.

Two `ConfidenceCalibrator` instances over one database are two workers: neither
holds anything of the other's in memory.
"""

from __future__ import annotations

import json
import sqlite3
import threading

import pytest

from app.agents.router import calibration
from app.agents.router.calibration import CALIBRATION_CONFIG_PATH, ConfidenceCalibrator


@pytest.fixture
def db(tmp_path):
    return tmp_path / "app.db"


def _worker(db, tmp_path) -> ConfidenceCalibrator:
    return ConfidenceCalibrator(db_path=db, seed_path=tmp_path / "no-earlier-file.json")


def _stored(db, bucket: str = "0.8-0.9") -> tuple[int, int]:
    with sqlite3.connect(db) as conn:
        return conn.execute(
            "SELECT total_predictions, correct_predictions FROM router_calibration WHERE bucket = ?", (bucket,)
        ).fetchone()


def test_two_workers_add_to_the_counts_rather_than_overwrite_them(db, tmp_path):
    a, b = _worker(db, tmp_path), _worker(db, tmp_path)
    seeded_total, seeded_correct = _stored(db)

    for _ in range(20):
        a.record_feedback(0.85, was_correct=True)
    for _ in range(20):
        b.record_feedback(0.85, was_correct=False)
    a.flush()
    b.flush()

    assert _stored(db) == (seeded_total + 40, seeded_correct + 20)


def test_concurrent_flushes_lose_nothing(db, tmp_path):
    workers = [_worker(db, tmp_path) for _ in range(4)]
    seeded_total, _ = _stored(db)

    def feed(worker):
        for _ in range(50):
            worker.record_feedback(0.85, was_correct=True)
        worker.flush()

    threads = [threading.Thread(target=feed, args=(worker,)) for worker in workers]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert _stored(db)[0] == seeded_total + 200


def test_a_worker_calibrates_from_what_another_worker_learned(db, tmp_path, monkeypatch):
    monkeypatch.setattr(calibration, "_REFRESH_SECONDS", 0.0)
    a, b = _worker(db, tmp_path), _worker(db, tmp_path)
    before = b.get_stats()["0.6-0.7"]["total_predictions"]

    for _ in range(10):
        a.record_feedback(0.65, was_correct=False)
    a.flush()

    assert b.get_stats()["0.6-0.7"]["total_predictions"] == before + 10
    assert b.calibrate(0.65) == a.calibrate(0.65)


def test_the_table_is_seeded_once_however_many_workers_start(db, tmp_path):
    starter = json.loads(CALIBRATION_CONFIG_PATH.read_text(encoding="utf-8"))["buckets"]

    for _ in range(3):
        _worker(db, tmp_path)

    with sqlite3.connect(db) as conn:
        rows = dict(conn.execute("SELECT bucket, total_predictions FROM router_calibration").fetchall())
    assert rows == {name: bucket.get("total_predictions", 0) for name, bucket in starter.items()} | {
        name: 0 for name in rows if name not in starter
    }


def test_an_earlier_installations_outcomes_are_carried_over(db, tmp_path):
    """Upgrade path: the accumulated file an older version wrote seeds the table once."""

    earlier = tmp_path / "router_calibration.json"
    earlier.write_text(
        json.dumps({"buckets": {"0.9-1.0": {"total_predictions": 40, "correct_predictions": 30}}}), encoding="utf-8"
    )

    ConfidenceCalibrator(db_path=db, seed_path=earlier)

    assert _stored(db, "0.9-1.0") == (40, 30)


def test_the_twentieth_record_reaches_the_shared_counts_without_a_flush(db, tmp_path):
    """Handed to the writer thread rather than waiting for shutdown -- or it would never be shared."""

    worker = _worker(db, tmp_path)
    seeded_total, _ = _stored(db)
    for _ in range(calibration._FLUSH_EVERY):
        worker.record_feedback(0.85, was_correct=True)

    calibration._WRITER.flush()

    assert _stored(db)[0] == seeded_total + calibration._FLUSH_EVERY
