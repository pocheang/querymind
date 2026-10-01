"""Neither Content-Security-Policy lets a foreign image load, or an inline script run (SEC-09).

Markdown rendered in the browser is model output, the draft stream, retrieved
document text and the model's reasoning; `img-src https:` let an image there
fetch any URL, with whatever its query string carried, on render. The default
backend policy also carried `'unsafe-inline' 'unsafe-eval'` for scripts "for
React", which the production build does not need. Both policies are checked:
the backend's (API responses, and the SPA when the backend serves it) and
nginx's (the SPA in the image).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.transport import middleware as middleware_module

NGINX_HEADERS = Path(__file__).resolve().parents[2] / "nginx-security-headers.conf"


def _directives(policy: str) -> dict[str, str]:
    return {part.split()[0]: part.strip() for part in policy.split(";") if part.strip()}


@pytest.fixture(params=[False, True], ids=["default", "strict"])
def backend_policy(request, monkeypatch) -> dict[str, str]:
    real = middleware_module.get_settings()
    monkeypatch.setattr(
        middleware_module, "get_settings", lambda: real.model_copy(update={"strict_csp": request.param})
    )
    app = FastAPI()
    app.middleware("http")(middleware_module.request_timing_middleware)

    @app.get("/probe")
    def probe() -> dict:
        return {}

    response = TestClient(app).get("/probe")
    return _directives(response.headers["content-security-policy"])


def test_the_backend_policy_loads_images_only_from_here(backend_policy):
    assert backend_policy["img-src"] == "img-src 'self' data: blob:"


def test_the_backend_policy_runs_no_inline_script_and_no_eval(backend_policy):
    assert backend_policy["script-src"] == "script-src 'self'"


def test_the_nginx_policy_loads_images_only_from_here():
    match = re.search(r'add_header Content-Security-Policy "([^"]*)"', NGINX_HEADERS.read_text(encoding="utf-8"))
    assert match
    assert _directives(match.group(1))["img-src"] == "img-src 'self' data: blob:"
