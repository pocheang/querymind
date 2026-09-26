"""The frontend nginx forwards what the backend is told to trust, and does not hold back events (ARC-01 phase 9).

Two properties of nginx.conf that nothing else checks. `nginx -t` in CI only
parses the file; the browser smoke test never sends a forged header or reads a
stream.

- **X-Forwarded-For is overwritten.** `$proxy_add_x_forwarded_for` appends the
  peer's address to whatever the client sent, so the client's own value came
  first -- and the backend trusts this header from nginx (SEC-02).
- **The event streams are not buffered.** With proxy buffering on, nginx holds
  a response until its buffer fills, so the draft answer and the stage timeline
  arrive in one burst at the end, which reads as a UI that stopped streaming.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.api.application.factory import _LEGACY_API_PREFIX_SEGMENTS

ROOT = Path(__file__).resolve().parents[2]
NGINX = ROOT / "nginx.conf"
EXECUTION_API = ROOT / "frontend" / "src" / "services" / "execution" / "execution-api.ts"

# Every route that answers text/event-stream, as the browser requests it through
# nginx's /api/ location. test_the_stream_list_is_complete keeps it in step.
SSE_ROUTES = {
    "app/api/routes/public/orchestration.py": "/api/v1/orchestration/executions/{execution_id}/events",
    "app/api/routes/operations/agent_tracking.py": "/api/agent-tracking/stream/{execution_id}",
}


def _config() -> str:
    """nginx.conf without its comments, which explain the directives by naming the ones not used."""

    return re.sub(r"#[^\n]*", "", NGINX.read_text(encoding="utf-8"))


def _locations() -> dict[str, str]:
    """`location <modifier> <pattern>` -> the block's body. nginx.conf nests nothing inside a location."""

    text = _config()
    return {match.group(1).strip(): match.group(2) for match in re.finditer(r"location\s+([^{]+)\{([^}]*)\}", text)}


def _directives(body: str) -> list[list[str]]:
    return [statement.split() for statement in body.split(";") if statement.strip()]


def _proxy_locations() -> dict[str, list[list[str]]]:
    proxied = {key: _directives(body) for key, body in _locations().items()}
    return {key: directives for key, directives in proxied.items() if any(d[0] == "proxy_pass" for d in directives)}


def _header(directives: list[list[str]], name: str) -> str | None:
    values = [d[2] for d in directives if d[0] == "proxy_set_header" and d[1].lower() == name.lower()]
    assert len(values) <= 1, f"{name} is set twice"
    return values[0] if values else None


def _sse_location() -> tuple[str, list[list[str]]]:
    regex = [(key, d) for key, d in _proxy_locations().items() if key.startswith("~") and "events" in key]
    assert len(regex) == 1, f"expected one event-stream location, found {[key for key, _ in regex]}"
    return regex[0]


def _sse_pattern() -> re.Pattern[str]:
    key, _ = _sse_location()
    return re.compile(key.split(None, 1)[1])


def test_there_is_more_than_one_proxy_location():
    """The checks below iterate these; an empty set would pass them all."""

    assert len(_proxy_locations()) >= 2


def test_no_location_appends_to_the_clients_header():
    assert "$proxy_add_x_forwarded_for" not in _config()


@pytest.mark.parametrize("location", sorted(_proxy_locations()))
def test_every_proxy_overwrites_the_forwarded_address(location: str):
    directives = _proxy_locations()[location]

    assert _header(directives, "X-Forwarded-For") == "$remote_addr"
    assert _header(directives, "X-Real-IP") == "$remote_addr"


@pytest.mark.parametrize("module", sorted(SSE_ROUTES))
def test_every_event_stream_the_backend_serves_takes_the_unbuffered_location(module: str):
    path = SSE_ROUTES[module].replace("{execution_id}", "exec-7f3a")

    assert _sse_pattern().search(path), f"{path} would be buffered by the /api/ location"


def test_the_path_the_frontend_builds_takes_the_unbuffered_location():
    """Read from the frontend's own template literal, so a renamed route shows up here."""

    literal = re.search(r"`(/api/v1/orchestration/executions/)\$\{[^}]+\}(/events)`", EXECUTION_API.read_text("utf-8"))
    assert literal, "execution-api.ts no longer builds the events path this test expects"

    assert _sse_pattern().search(f"{literal.group(1)}exec-7f3a{literal.group(2)}")


@pytest.mark.parametrize(
    "path",
    ["/api/v1/orchestration/executions/exec-7f3a", "/api/advanced-rag/query", "/api/agent-tracking/trace/exec-7f3a"],
)
def test_ordinary_requests_keep_the_buffered_location(path: str):
    """An unbuffered location costs a worker connection per slow client; it is for streams only."""

    assert not _sse_pattern().search(path)


def test_the_stream_location_does_not_buffer_or_cut_a_long_stream():
    _, directives = _sse_location()
    settings = {d[0]: d[1:] for d in directives}

    assert settings["proxy_buffering"] == ["off"]
    assert settings["proxy_cache"] == ["off"]
    assert int(settings["proxy_read_timeout"][0].rstrip("s")) >= 3600
    # No URI after the host: the path goes through unchanged, and the backend
    # strips /api for bare routers like /agent-tracking.
    assert settings["proxy_pass"] == ["http://backend:8000"]
    assert "agent-tracking" in _LEGACY_API_PREFIX_SEGMENTS


def test_the_api_prefix_does_not_outrank_the_stream_location():
    """`^~` on a prefix location stops nginx from consulting regex locations at all."""

    assert "/api/" in _locations()
    assert not any(key.startswith("^~") for key in _locations())


def test_the_stream_list_is_complete():
    producers = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "app").rglob("*.py")
        if "text/event-stream" in path.read_text(encoding="utf-8")
    }

    assert producers == set(SSE_ROUTES), "a module started or stopped serving event streams; update SSE_ROUTES"


def test_the_frontend_probes_ask_the_address_nginx_listens_on():
    """busybox wget resolves `localhost` to ::1 first and does not fall back to IPv4.

    nginx.conf listens on IPv4 only, so a probe of `localhost` was refused and
    the frontend never once reported healthy -- found in the phase 9 container
    run, with the site serving normally the whole time.
    """

    import yaml

    listens = re.findall(r"^\s*listen\s+([^;]+);", _config(), re.MULTILINE)
    assert listens == ["8080"], "nginx listens somewhere new; re-check which address the probes may use"
    compose = yaml.safe_load((ROOT / "deploy" / "compose" / "compose.yaml").read_text(encoding="utf-8"))
    probes = {
        "compose.yaml": " ".join(compose["services"]["frontend"]["healthcheck"]["test"]),
        "Dockerfile.frontend": (ROOT / "Dockerfile.frontend").read_text(encoding="utf-8").split("HEALTHCHECK", 1)[1],
    }
    for where, probe in probes.items():
        assert "http://127.0.0.1:8080/" in probe, f"{where} does not probe nginx's IPv4 listener"
        assert "localhost" not in probe.split("||")[0], f"{where} probes localhost"
