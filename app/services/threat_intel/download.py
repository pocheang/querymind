"""Fetching the four feeds: fixed hosts, HTTPS, a size ceiling, and NVD's paging and rate limit.

Every URL here is a constant of this module -- nothing a user, a document or a
model supplies is ever fetched -- so the guard is an allowlist of hosts, checked
again after redirects. A download that exceeds its ceiling is an error, never
a truncation: a truncated JSON document fails to parse at best and parses into
fewer rows at worst, and the sync would then replace a full table with a
partial one.
"""

from __future__ import annotations

import gzip
import io
import json
import os
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

import httpx

__all__ = [
    "FEEDS",
    "NVD_API",
    "DownloadRefused",
    "Feed",
    "decompress_if_gzip",
    "download",
    "nvd_pages",
]

NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_PAGE_SIZE = 2000
# NVD's published limits: 5 requests per rolling 30 s without a key, 50 with one.
NVD_DELAY_SECONDS = 6.5
NVD_DELAY_WITH_KEY_SECONDS = 0.7
# NVD refuses a lastModified window longer than 120 days.
NVD_WINDOW = timedelta(days=120)

_ALLOWED_HOSTS = frozenset(
    {
        "services.nvd.nist.gov",
        "www.cisa.gov",
        "epss.empiricalsecurity.com",
        "epss.cyentia.com",
        "raw.githubusercontent.com",
    }
)


@dataclass(frozen=True)
class Feed:
    url: str
    max_bytes: int
    filename: str  # what --from-dir looks for


FEEDS: dict[str, Feed] = {
    "kev": Feed(
        "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
        30_000_000,
        "known_exploited_vulnerabilities.json",
    ),
    "epss": Feed(
        "https://epss.empiricalsecurity.com/epss_scores-current.csv.gz", 60_000_000, "epss_scores-current.csv.gz"
    ),
    "attack": Feed(
        "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack.json",
        250_000_000,
        "enterprise-attack.json",
    ),
}


class DownloadRefused(RuntimeError):
    """A fetch this module will not complete. The message says which rule."""


def _check(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in _ALLOWED_HOSTS:
        raise DownloadRefused(f"not an allowed feed URL: {parts.scheme}://{parts.hostname}")


def download(
    url: str,
    *,
    max_bytes: int,
    timeout: float = 120.0,
    proxy: str | None = None,
    headers: dict[str, str] | None = None,
    params: dict[str, str | int] | None = None,
) -> bytes:
    _check(url)
    with (
        httpx.Client(timeout=timeout, proxy=proxy, follow_redirects=True, trust_env=False) as client,
        client.stream(
            "GET", url, headers={"User-Agent": "QueryMind threat-intel sync", **(headers or {})}, params=params
        ) as response,
    ):
        _check(str(response.url))
        response.raise_for_status()
        chunks: list[bytes] = []
        size = 0
        for chunk in response.iter_bytes():
            size += len(chunk)
            if size > max_bytes:
                raise DownloadRefused(f"larger than the {max_bytes:,}-byte ceiling for {urlsplit(url).hostname}")
            chunks.append(chunk)
    return b"".join(chunks)


def decompress_if_gzip(data: bytes, *, max_bytes: int) -> bytes:
    """Gunzip when the payload is gzip, with the same ceiling on what it expands to."""

    if data[:2] != b"\x1f\x8b":
        return data
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as handle:
        expanded = handle.read(max_bytes + 1)
    if len(expanded) > max_bytes:
        raise DownloadRefused(f"expands past the {max_bytes:,}-byte ceiling")
    return expanded


def nvd_api_key() -> str:
    """`NVD_API_KEY` from the real environment, like `NACOS_PASSWORD`: never a `Settings` field.

    A field can reach a configuration endpoint, and this is a credential.
    """

    return os.environ.get("NVD_API_KEY", "").strip()


def nvd_windows(since: datetime | None, now: datetime) -> list[tuple[datetime, datetime] | None]:
    """The lastModified windows to page through; `[None]` for a first, full sync."""

    if since is None:
        return [None]
    windows: list[tuple[datetime, datetime] | None] = []
    start = since
    while start < now:
        end = min(start + NVD_WINDOW, now)
        windows.append((start, end))
        start = end
    return windows


def nvd_pages(
    since: datetime | None,
    *,
    proxy: str | None = None,
    now: datetime | None = None,
    fetch: Callable[..., bytes] = download,
    sleep: Callable[[float], None] = time.sleep,
) -> Iterator[bytes]:
    """Every page of CVEs modified since `since` (all of them when None), in order."""

    key = nvd_api_key()
    headers = {"apiKey": key} if key else {}
    delay = NVD_DELAY_WITH_KEY_SECONDS if key else NVD_DELAY_SECONDS
    requests_made = 0

    def get(params: dict[str, str | int]) -> bytes:
        nonlocal requests_made
        if requests_made:
            sleep(delay)
        requests_made += 1
        return fetch(NVD_API, max_bytes=80_000_000, proxy=proxy, headers=headers, params=params)

    for window in nvd_windows(since, now or datetime.now(UTC)):
        yield from _window_pages(window, get)


def _window_pages(window: tuple[datetime, datetime] | None, get: Callable[[dict], bytes]) -> Iterator[bytes]:
    """Every page of one lastModified window, following `startIndex` until NVD's total is reached."""

    base: dict[str, str | int] = {"resultsPerPage": NVD_PAGE_SIZE}
    if window is not None:
        base["lastModStartDate"] = window[0].isoformat(timespec="milliseconds")
        base["lastModEndDate"] = window[1].isoformat(timespec="milliseconds")
    start_index, total = 0, None
    while total is None or start_index < total:
        page = get({**base, "startIndex": start_index})
        payload = json.loads(page)
        total = int(payload.get("totalResults") or 0)
        returned = len(payload.get("vulnerabilities") or ())
        yield page
        if returned == 0:
            return
        start_index += returned
