"""
Router confidence calibration system.

Calibrates raw confidence scores to better reflect actual routing accuracy
by tracking historical performance in confidence buckets.

Key features:
- Bucket-based calibration (0.5-0.6, 0.6-0.7, 0.7-0.8, 0.8-0.9, 0.9-1.0)
- Historical accuracy tracking per bucket
- Persistent storage of calibration data
- Minimum sample requirements to prevent overfitting
"""

import json
import logging
import sqlite3
import threading
import time
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Final

from app.services.runtime.background_writer import BackgroundWriter
from app.services.runtime.sqlite_schema import Migration, ensure_schema

logger = logging.getLogger(__name__)

# Configuration constants
CONFIDENCE_BUCKETS: Final[list[tuple[float, float]]] = [
    (0.5, 0.6),
    (0.6, 0.7),
    (0.7, 0.8),
    (0.8, 0.9),
    (0.9, 1.0),
]

MIN_SAMPLES_FOR_CALIBRATION: Final[int] = 5  # Minimum predictions before applying calibration
DEFAULT_ACCURACY: Final[float] = 0.5  # Default accuracy when no history

# Configuration file path - anchored at repository root
REPOSITORY_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
CALIBRATION_CONFIG_PATH: Final[Path] = REPOSITORY_ROOT / "config" / "router_calibration.json"
"""Tracked starter distribution; accumulated outcomes go to ROUTER_CALIBRATION_PATH."""

_FLUSH_EVERY: Final[int] = 20
# How stale another worker's outcomes may be in this process's calibration.
_REFRESH_SECONDS: Final[float] = 10.0


def get_bucket_for_confidence(confidence: float) -> str:
    """
    Get the bucket name for a given confidence score.

    Args:
        confidence: Raw confidence score

    Returns:
        Bucket name (e.g., "0.7-0.8")
    """
    # Clamp to valid range
    confidence = max(CONFIDENCE_BUCKETS[0][0], min(CONFIDENCE_BUCKETS[-1][1], confidence))

    # Each bucket is half-open except the last, whose upper bound has to be
    # inclusive or the clamped maximum belongs to no bucket at all. Saying that
    # positionally rather than as `confidence == 1.0 and high == 1.0` keeps it
    # true if the table ever stops ending at 1.0 -- that spelling sent the top
    # value to the *lowest* bucket via the fallback below the moment it did.
    last = len(CONFIDENCE_BUCKETS) - 1
    for index, (low, high) in enumerate(CONFIDENCE_BUCKETS):
        if low <= confidence < high or (index == last and confidence <= high):
            return f"{low}-{high}"

    # Unreachable while the table is contiguous; kept so a gap in it degrades
    # to a bucket rather than to an exception.
    return f"{CONFIDENCE_BUCKETS[0][0]}-{CONFIDENCE_BUCKETS[0][1]}"


@dataclass
class CalibrationBucket:
    """Calibration data for a confidence bucket."""

    total_predictions: int = 0
    correct_predictions: int = 0
    last_updated: str | None = None
    low: float = 0.5
    high: float = 1.0

    @property
    def historical_accuracy(self) -> float:
        """Calculate historical accuracy for this bucket."""
        if self.total_predictions == 0:
            return DEFAULT_ACCURACY
        return self.correct_predictions / self.total_predictions

    @property
    def midpoint(self) -> float:
        """Calculate the midpoint of this bucket's range."""
        return (self.low + self.high) / 2.0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "total_predictions": self.total_predictions,
            "correct_predictions": self.correct_predictions,
            "last_updated": self.last_updated,
            "low": self.low,
            "high": self.high,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CalibrationBucket":
        """Create from dictionary."""
        return cls(
            total_predictions=data.get("total_predictions", 0),
            correct_predictions=data.get("correct_predictions", 0),
            last_updated=data.get("last_updated"),
            low=data.get("low", 0.5),
            high=data.get("high", 1.0),
        )


@dataclass
class CalibrationData:
    """Complete calibration data for all buckets."""

    buckets: dict[str, CalibrationBucket] = field(default_factory=dict)
    version: str = "1.0"

    def __post_init__(self):
        """Initialize all buckets if not provided."""
        if not self.buckets:
            self.buckets = {f"{low}-{high}": CalibrationBucket(low=low, high=high) for low, high in CONFIDENCE_BUCKETS}

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {"version": self.version, "buckets": {name: bucket.to_dict() for name, bucket in self.buckets.items()}}

    @classmethod
    def from_dict(cls, data: dict) -> "CalibrationData":
        """Create from dictionary."""
        buckets = {
            name: CalibrationBucket.from_dict(bucket_data) for name, bucket_data in data.get("buckets", {}).items()
        }

        # Boundaries belong to the bucketing scheme, not to the accumulated
        # data: the bucket's own name encodes them, so a persisted pair can only
        # ever agree with the table or be wrong. Taking them from the table
        # unconditionally replaces a guess -- "these are still 0.5/1.0, so the
        # file must predate storing them" -- which could not tell an absent
        # boundary from a genuine one, and needed a special case for the first
        # bucket to paper over that.
        for low, high in CONFIDENCE_BUCKETS:
            bucket_name = f"{low}-{high}"
            bucket = buckets.get(bucket_name)
            if bucket is None:
                buckets[bucket_name] = CalibrationBucket(low=low, high=high)
            else:
                bucket.low = low
                bucket.high = high

        return cls(buckets=buckets, version=data.get("version", "1.0"))


def load_calibration_data(config_path: Path | None = None) -> CalibrationData:
    """
    Load calibration data from file.

    Args:
        config_path: Path to calibration config file (defaults to config/router_calibration.json)

    Returns:
        CalibrationData instance (new if file doesn't exist)
    """
    if config_path is None:
        config_path = CALIBRATION_CONFIG_PATH

    try:
        if config_path.exists():
            with open(config_path) as f:
                data_dict = json.load(f)
                return CalibrationData.from_dict(data_dict)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to load calibration data from {config_path}: {e}")

    # Return fresh data if load failed
    return CalibrationData()


def update_calibration_data(data: CalibrationData, raw_confidence: float, was_correct: bool) -> None:
    """
    Update calibration data with feedback from a routing decision.

    Args:
        data: CalibrationData to update
        raw_confidence: Raw confidence score that was used
        was_correct: Whether the routing decision was correct
    """
    bucket_name = get_bucket_for_confidence(raw_confidence)
    bucket = data.buckets[bucket_name]

    bucket.total_predictions += 1
    if was_correct:
        bucket.correct_predictions += 1
    bucket.last_updated = datetime.now().isoformat()

    logger.debug(
        f"Updated calibration bucket {bucket_name}: "
        f"{bucket.correct_predictions}/{bucket.total_predictions} "
        f"(accuracy={bucket.historical_accuracy:.2f})"
    )


def apply_calibration(raw_confidence: float, data: CalibrationData) -> float:
    """
    Apply calibration to a raw confidence score.

    Calibration formula:
        calibrated = raw_confidence * (historical_accuracy / bucket_midpoint)

    This adjusts the confidence to match the historical accuracy observed
    for similar confidence levels while preserving within-bucket variation.

    Example:
        - Bucket 0.7-0.8 (midpoint=0.75) with historical_accuracy=0.8
        - raw_confidence=0.79 → calibrated = 0.79 * (0.8/0.75) = 0.843
        - raw_confidence=0.71 → calibrated = 0.71 * (0.8/0.75) = 0.757

    Args:
        raw_confidence: Raw confidence score from router
        data: Calibration data with historical accuracy

    Returns:
        Calibrated confidence score clamped to [0.0, 1.0]
    """
    bucket_name = get_bucket_for_confidence(raw_confidence)
    bucket = data.buckets[bucket_name]

    # Require minimum samples before calibrating
    if bucket.total_predictions < MIN_SAMPLES_FOR_CALIBRATION:
        logger.debug(
            f"Not enough samples for calibration in bucket {bucket_name} "
            f"({bucket.total_predictions} < {MIN_SAMPLES_FOR_CALIBRATION})"
        )
        return raw_confidence

    # Apply calibration: scale by ratio of historical accuracy to bucket midpoint
    historical_accuracy = bucket.historical_accuracy
    bucket_midpoint = bucket.midpoint
    calibrated = raw_confidence * (historical_accuracy / bucket_midpoint)

    # Clamp to valid range
    calibrated = max(0.0, min(1.0, calibrated))

    logger.debug(
        f"Calibrated confidence {raw_confidence:.2f} -> {calibrated:.2f} "
        f"(bucket={bucket_name}, history={historical_accuracy:.2f}, midpoint={bucket_midpoint:.2f})"
    )

    return calibrated


def _calibration_baseline(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS router_calibration (
          bucket TEXT PRIMARY KEY,
          total_predictions INTEGER NOT NULL DEFAULT 0,
          correct_predictions INTEGER NOT NULL DEFAULT 0,
          last_updated TEXT
        )
        """
    )


CALIBRATION_MIGRATIONS = (Migration(1, "baseline: router_calibration", _calibration_baseline),)

# One writer thread for the process: flushes leave the request path (the
# verifier node records feedback, and it is async).
_WRITER = BackgroundWriter("router_calibration")


class ConfidenceCalibrator:
    """
    Manages confidence calibration for router decisions, shared by every worker.

    Usage:
        calibrator = ConfidenceCalibrator()

        # Apply calibration
        calibrated = calibrator.calibrate(raw_confidence=0.85)

        # Record feedback
        calibrator.record_feedback(raw_confidence=0.85, was_correct=True)

    The counts live in `router_calibration` in the application database, and a
    worker adds its outcomes to them as *increments* (ARC-01 audit, 2026-09-25).
    They used to live in each process and be written out every 20 records as a
    whole file, so with several workers each rewrote the file with its own
    counts, erasing the others', and each calibrated from different data. The
    write was not atomic either: a worker starting mid-write read a truncated
    file and quietly began from nothing.

    Each process re-reads the shared counts at most every `_REFRESH_SECONDS`,
    with its own not-yet-flushed outcomes applied on top, so its answers include
    what it has just seen as well as what every other worker flushed.
    """

    def __init__(self, db_path: Path | None = None, seed_path: Path | None = None):
        """
        Initialize calibrator.

        Args:
            db_path: The application database. Defaults to APP_DB_PATH.
            seed_path: Where a table with no rows is seeded from, once: the
                accumulated outcomes of an installation that predates the table
                (ROUTER_CALIBRATION_PATH), else the tracked starter
                config/router_calibration.json, so a fresh deployment does not
                begin with an empty distribution.
        """
        from app.core.config import get_settings

        settings = get_settings()
        self.db_path = Path(db_path or settings.app_db_path)
        self.seed_path = Path(seed_path or settings.router_calibration_path)
        ensure_schema(self.db_path, "router_calibration", CALIBRATION_MIGRATIONS, wal=True)
        self._lock = threading.Lock()
        self._pending: dict[str, list[int]] = {}
        self._unsaved = 0
        self._shared = CalibrationData()
        self._read_at = 0.0
        self._seed_if_empty()
        self._refresh()

    # ---- storage ----------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.isolation_level = None
        return conn

    def _seed_if_empty(self) -> None:
        """Seed once. The emptiness check and the insert are one transaction, so two workers seed once."""

        source = self.seed_path if self.seed_path.exists() else CALIBRATION_CONFIG_PATH
        seed = load_calibration_data(source)
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute("SELECT COUNT(*) FROM router_calibration").fetchone()[0] == 0:
                conn.executemany(
                    "INSERT INTO router_calibration VALUES (?, ?, ?, ?)",
                    [
                        (name, bucket.total_predictions, bucket.correct_predictions, bucket.last_updated)
                        for name, bucket in seed.buckets.items()
                    ],
                )
            conn.execute("COMMIT")

    def _refresh(self) -> None:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT bucket, total_predictions, correct_predictions, last_updated FROM router_calibration"
            ).fetchall()
        data = CalibrationData.from_dict(
            {
                "buckets": {
                    name: {"total_predictions": total, "correct_predictions": correct, "last_updated": updated}
                    for name, total, correct, updated in rows
                }
            }
        )
        with self._lock:
            self._shared = data
            self._read_at = time.monotonic()

    def _write(self, deltas: dict[str, list[int]]) -> None:
        """Add this process's outcomes to the shared counts; never overwrite them."""

        stamp = datetime.now().isoformat()
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.executemany(
                """
                INSERT INTO router_calibration (bucket, total_predictions, correct_predictions, last_updated)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(bucket) DO UPDATE SET
                  total_predictions = total_predictions + excluded.total_predictions,
                  correct_predictions = correct_predictions + excluded.correct_predictions,
                  last_updated = excluded.last_updated
                """,
                [(name, total, correct, stamp) for name, (total, correct) in deltas.items()],
            )
            conn.execute("COMMIT")
        with self._lock:
            self._read_at = 0.0  # the next read includes what was just added

    def _take_pending(self) -> dict[str, list[int]]:
        with self._lock:
            deltas, self._pending, self._unsaved = self._pending, {}, 0
        return deltas

    # ---- the calibrator's surface -------------------------------------------------

    @property
    def calibration_data(self) -> CalibrationData:
        """Every worker's flushed outcomes, re-read at most every `_REFRESH_SECONDS`, plus this process's pending ones."""

        if time.monotonic() - self._read_at >= _REFRESH_SECONDS:
            self._refresh()
        with self._lock:
            data = CalibrationData.from_dict(self._shared.to_dict())
            for name, (total, correct) in self._pending.items():
                data.buckets[name].total_predictions += total
                data.buckets[name].correct_predictions += correct
        return data

    def calibrate(self, raw_confidence: float) -> float:
        """
        Apply calibration to a raw confidence score.

        Args:
            raw_confidence: Raw confidence from router

        Returns:
            Calibrated confidence score
        """
        return apply_calibration(raw_confidence, self.calibration_data)

    def record_feedback(self, raw_confidence: float, was_correct: bool) -> None:
        """
        Record feedback about a routing decision.

        Args:
            raw_confidence: Raw confidence that was used
            was_correct: Whether the decision was correct

        Counted in memory at once and added to the shared counts every
        `_FLUSH_EVERY` records, on the writer thread: a database write per
        request -- on the event loop, since the verifier node is async -- for a
        statistic that moves slowly would be the wrong trade.
        """
        name = get_bucket_for_confidence(raw_confidence)
        with self._lock:
            pending = self._pending.setdefault(name, [0, 0])
            pending[0] += 1
            pending[1] += 1 if was_correct else 0
            self._unsaved += 1
            due = self._unsaved >= _FLUSH_EVERY
        if due:
            deltas = self._take_pending()
            _WRITER.submit(lambda: self._write(deltas), label="router_calibration")

    def flush(self) -> None:
        """Add the pending outcomes to the shared counts now (shutdown, tests)."""
        _WRITER.flush()
        deltas = self._take_pending()
        if deltas:
            self._write(deltas)

    def get_stats(self) -> dict[str, dict]:
        """
        Get calibration statistics for all buckets.

        Returns:
            Dictionary mapping bucket names to stats
        """
        return {
            name: {
                "total_predictions": bucket.total_predictions,
                "correct_predictions": bucket.correct_predictions,
                "historical_accuracy": bucket.historical_accuracy,
                "last_updated": bucket.last_updated,
            }
            for name, bucket in self.calibration_data.buckets.items()
        }
