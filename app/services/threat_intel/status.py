"""How current each source is, read from the sync record -- the one thing tools and the admin page both show."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from functools import lru_cache

from app.core.config import Settings, get_settings
from app.services.threat_intel.store import SOURCES, ThreatIntelStore

__all__ = ["SourceStatus", "get_threat_intel_store", "source_statuses"]


@dataclass(frozen=True)
class SourceStatus:
    source: str
    records: int
    last_success: str  # ISO timestamp, "" when never synced
    age_days: float | None
    stale_after_days: int
    state: str  # empty | stale | current
    data_version: str
    last_attempt_status: str
    last_attempt_detail: str

    def as_dict(self) -> dict:
        return asdict(self)


@lru_cache(maxsize=4)
def _store_for(path: str) -> ThreatIntelStore:
    return ThreatIntelStore(path)


def get_threat_intel_store(settings: Settings | None = None) -> ThreatIntelStore:
    """The store at the configured path, opened (and migrated) once per path per process."""

    return _store_for(str((settings or get_settings()).threat_intel_db_path))


def source_statuses(
    store: ThreatIntelStore, settings: Settings | None = None, *, now: datetime | None = None
) -> list[SourceStatus]:
    active = settings or get_settings()
    moment = now or datetime.now(UTC)
    counts = store.counts()
    return [
        _status(store, source, counts[source], active.threat_intel_stale_days(source), moment) for source in SOURCES
    ]


def _status(store: ThreatIntelStore, source: str, records: int, threshold: int, now: datetime) -> SourceStatus:
    success = store.last_run(source, successful=True)
    attempt = store.last_run(source)
    age = _age_days(success.finished_at, now) if success else None
    if not records:
        state = "empty"
    elif age is None or age > threshold:
        state = "stale"
    else:
        state = "current"
    return SourceStatus(
        source=source,
        records=records,
        last_success=success.finished_at if success else "",
        age_days=None if age is None else round(age, 1),
        stale_after_days=threshold,
        state=state,
        data_version=success.data_version if success else "",
        last_attempt_status=attempt.status if attempt else "",
        last_attempt_detail=attempt.detail if attempt else "",
    )


def _age_days(timestamp: str, now: datetime) -> float | None:
    try:
        moment = datetime.fromisoformat(timestamp)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return (now - moment).total_seconds() / 86400
