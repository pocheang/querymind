"""The fetch layer: fixed hosts, HTTPS, ceilings that fail rather than truncate, and NVD's windows and pages."""

from __future__ import annotations

import functools
import gzip
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.services.threat_intel import download
from app.services.threat_intel.download import (
    NVD_WINDOW,
    DownloadRefused,
    decompress_if_gzip,
    nvd_pages,
    nvd_windows,
)


@pytest.fixture
def serve(monkeypatch: pytest.MonkeyPatch):
    def install(handler):
        monkeypatch.setattr(
            download.httpx, "Client", functools.partial(httpx.Client, transport=httpx.MockTransport(handler))
        )

    return install


@pytest.mark.parametrize(
    "url",
    [
        "http://www.cisa.gov/feed.json",
        "https://evil.example.com/feed.json",
        "https://www.cisa.gov.evil.com/feed.json",
        "file:///etc/passwd",
    ],
)
def test_only_https_to_the_feed_hosts(url):
    with pytest.raises(DownloadRefused, match="not an allowed feed URL"):
        download.download(url, max_bytes=100)


def test_a_redirect_off_the_feed_hosts_is_refused(serve):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "www.cisa.gov":
            return httpx.Response(302, headers={"location": "https://evil.example.com/feed.json"})
        return httpx.Response(200, content=b"{}")

    serve(handler)

    with pytest.raises(DownloadRefused, match="not an allowed feed URL"):
        download.download("https://www.cisa.gov/feed.json", max_bytes=100)


def test_a_download_past_its_ceiling_fails_rather_than_truncates(serve):
    """A truncated feed parses into fewer rows at worst -- and would then replace a full table."""

    serve(lambda request: httpx.Response(200, content=b"x" * 5_000))

    with pytest.raises(DownloadRefused, match="ceiling"):
        download.download("https://www.cisa.gov/feed.json", max_bytes=1_000)


def test_a_download_within_its_ceiling_is_returned_whole(serve):
    serve(lambda request: httpx.Response(200, content=b"y" * 999))

    assert download.download("https://www.cisa.gov/feed.json", max_bytes=1_000) == b"y" * 999


def test_an_http_error_is_an_error(serve):
    serve(lambda request: httpx.Response(503))

    with pytest.raises(httpx.HTTPStatusError):
        download.download("https://www.cisa.gov/feed.json", max_bytes=1_000)


def test_gzip_is_expanded_under_the_same_kind_of_ceiling():
    """A small compressed file can expand to anything; that is a refusal, not an allocation."""

    bomb = gzip.compress(b"\0" * 2_000_000)

    assert len(bomb) < 10_000
    with pytest.raises(DownloadRefused, match="expands past"):
        decompress_if_gzip(bomb, max_bytes=1_000_000)
    assert decompress_if_gzip(gzip.compress(b"ok"), max_bytes=10) == b"ok"
    assert decompress_if_gzip(b"plain", max_bytes=10) == b"plain"


def test_nvd_windows_are_at_most_120_days_and_cover_the_whole_span():
    since = datetime(2026, 1, 1, tzinfo=UTC)
    now = since + timedelta(days=300)

    windows = nvd_windows(since, now)

    assert all(end - start <= NVD_WINDOW for start, end in windows)
    assert windows[0][0] == since and windows[-1][1] == now
    assert all(windows[i][1] == windows[i + 1][0] for i in range(len(windows) - 1))
    assert nvd_windows(None, now) == [None], "a first sync is one unfiltered pass"


def _page(total: int, count: int) -> bytes:
    return json.dumps({"totalResults": total, "vulnerabilities": [{}] * count}).encode()


def test_nvd_pages_until_every_result_is_fetched_and_rests_between_requests(monkeypatch):
    monkeypatch.delenv("NVD_API_KEY", raising=False)
    calls: list[dict] = []
    served = iter([_page(5, 2), _page(5, 2), _page(5, 1)])

    def fetch(url, **kwargs):
        calls.append(kwargs)
        return next(served)

    slept: list[float] = []
    pages = list(nvd_pages(None, fetch=fetch, sleep=slept.append))

    assert len(pages) == 3
    assert [call["params"]["startIndex"] for call in calls] == [0, 2, 4]
    assert "lastModStartDate" not in calls[0]["params"]
    assert slept == [download.NVD_DELAY_SECONDS] * 2, "the unauthenticated rate limit, between requests only"
    assert calls[0]["headers"] == {}


def test_the_api_key_comes_from_the_environment_and_shortens_the_wait(monkeypatch):
    monkeypatch.setenv("NVD_API_KEY", "test-key-value")
    calls: list[dict] = []
    served = iter([_page(3, 2), _page(3, 1)])

    def fetch(url, **kwargs):
        calls.append(kwargs)
        return next(served)

    slept: list[float] = []
    list(nvd_pages(None, fetch=fetch, sleep=slept.append))

    assert calls[0]["headers"] == {"apiKey": "test-key-value"}
    assert slept == [download.NVD_DELAY_WITH_KEY_SECONDS]


def test_an_incremental_sync_asks_only_for_what_changed(monkeypatch):
    monkeypatch.delenv("NVD_API_KEY", raising=False)
    calls: list[dict] = []

    def fetch(url, **kwargs):
        calls.append(kwargs)
        return _page(0, 0)

    since = datetime(2026, 9, 1, tzinfo=UTC)
    list(nvd_pages(since, now=since + timedelta(days=3), fetch=fetch, sleep=lambda s: None))

    assert calls[0]["params"]["lastModStartDate"].startswith("2026-09-01T00:00:00.000")
    assert calls[0]["params"]["lastModEndDate"].startswith("2026-09-04")


def test_the_api_key_is_not_a_setting():
    """A Settings field can reach a configuration endpoint; this is a credential."""

    from app.core.config import Settings

    assert not [
        name for name, field in Settings.model_fields.items() if "nvd" in name.lower() and "key" in name.lower()
    ]
