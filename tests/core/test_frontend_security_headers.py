"""What nginx serves itself carries the security headers (SEC-03).

Two defects, and each one passes `nginx -t`:

- The image shipped no Content-Security-Policy at all. The policy lived in
  `frontend/nginx-security.conf`, which nothing included or copied, and in
  `frontend/public/_headers`, a Netlify/Cloudflare format nginx does not read.
- nginx drops every server-level ``add_header`` from a location that declares
  one of its own. The entry page and the hashed assets set ``Cache-Control``, so
  both went out without X-Frame-Options and nosniff.

So the rule checked here is structural: every location that serves a file
includes the one header file, the server block declares none (a server-level
header would reach the API responses too, beside the backend's own), and the
image puts that file where the include looks for it. CI's images job asserts
the same on real responses.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
NGINX_CONF = ROOT / "nginx.conf"
HEADERS_CONF = ROOT / "nginx-security-headers.conf"
DOCKERFILE = ROOT / "Dockerfile.frontend"
INCLUDE_PATH = "/etc/nginx/snippets/security-headers.conf"


def _strip_comments(text: str) -> str:
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def _locations(text: str) -> list[tuple[str, str]]:
    """(matcher, body) for each top-level location in the server block."""

    found: list[tuple[str, str]] = []
    for match in re.finditer(r"location\s+([^{]+)\{", text):
        depth, index = 1, match.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(text[index], 0)
            index += 1
        found.append((match.group(1).strip(), text[match.end() : index - 1]))
    return found


def _server_level(text: str) -> str:
    """The server block with every location body removed."""

    return re.sub(r"location\s+[^{]+\{[^{}]*\}", "", text)


CONF = _strip_comments(NGINX_CONF.read_text(encoding="utf-8"))
LOCATIONS = _locations(CONF)


def test_the_configuration_has_locations_to_check():
    # A parser that silently finds nothing would make every test below vacuous.
    assert len(LOCATIONS) >= 5
    assert any(body for _, body in LOCATIONS if "proxy_pass" in body)


@pytest.mark.parametrize(
    ("matcher", "body"), [loc for loc in LOCATIONS if "proxy_pass" not in loc[1]], ids=lambda value: value[:24]
)
def test_every_location_that_serves_a_file_includes_the_headers(matcher: str, body: str):
    assert f"include {INCLUDE_PATH};" in body, f"location {matcher} serves files without the security headers"


@pytest.mark.parametrize(
    ("matcher", "body"), [loc for loc in LOCATIONS if "proxy_pass" in loc[1]], ids=lambda value: value[:24]
)
def test_a_proxied_location_leaves_the_headers_to_the_backend(matcher: str, body: str):
    # Two CSP headers on one response are enforced as their intersection; the
    # backend sets its own on what it serves (app/api/transport/middleware.py).
    assert "security-headers.conf" not in body
    assert "add_header" not in body


def test_the_server_block_declares_no_header_a_location_would_drop():
    assert "add_header" not in _server_level(CONF)


def test_the_image_puts_the_header_file_where_the_include_looks():
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert f"COPY nginx-security-headers.conf {INCLUDE_PATH}" in dockerfile


def _header(name: str) -> str:
    match = re.search(rf'^add_header\s+{name}\s+"([^"]*)"\s+always;', HEADERS_CONF.read_text(encoding="utf-8"), re.M)
    assert match, f"{name} is not set (with `always`) in {HEADERS_CONF.name}"
    return match.group(1)


def _directives() -> dict[str, str]:
    policy = _header("Content-Security-Policy")
    return {part.split()[0]: part.strip() for part in policy.split(";") if part.strip()}


def test_the_policy_allows_no_inline_script_and_no_eval():
    script_src = _directives()["script-src"]

    assert script_src == "script-src 'self'"


@pytest.mark.parametrize(
    "directive",
    ["default-src 'self'", "object-src 'none'", "frame-ancestors 'self'", "base-uri 'self'", "connect-src 'self'"],
)
def test_the_policy_carries_the_baseline_directives(directive: str):
    assert directive in _directives().values()


def test_the_policy_allows_the_self_hosted_fonts():
    # frontend/src/styles/main.css self-hosts the fonts because of this directive.
    assert _directives()["font-src"] == "font-src 'self' data:"


@pytest.mark.parametrize(("name", "value"), [("X-Frame-Options", "SAMEORIGIN"), ("X-Content-Type-Options", "nosniff")])
def test_the_anti_framing_and_nosniff_headers_are_set(name: str, value: str):
    assert _header(name) == value


def test_there_is_one_copy_of_the_frontend_policy():
    # The two copies nothing read are what let the shipped image have no policy
    # while the documentation said "all three copies agree".
    assert not (ROOT / "frontend" / "nginx-security.conf").exists()
    assert not (ROOT / "frontend" / "public" / "_headers").exists()
