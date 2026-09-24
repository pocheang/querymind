"""Canonical FastAPI application construction."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.application.lifespan import lifespan
from app.api.application.router_registry import register_routers
from app.api.application.static_files import StaticFilePaths, configure_static_files
from app.api.middleware.rate_limit import RateLimitMiddleware
from app.api.transport.errors import index_busy_response, shared_state_unavailable_response
from app.api.transport.middleware import request_timing_middleware
from app.core.config import normalise_environment_name
from app.services.runtime.file_locks import LockBusy
from app.services.runtime.shared_state import SharedStateUnavailable

_APP_BASE_API_SEGMENTS = {
    "admin",
    "api",
    "auth",
    "documents",
    "prompts",
    "query",
    "sessions",
    "upload",
    "user",
}

_LEGACY_API_PREFIX_SEGMENTS = {
    "agent-tracking",
    "auth",
    "documents",
    "prompts",
    "query",
    "sessions",
    "upload",
}


async def rewrite_app_prefixed_api_paths(request, call_next):
    """Support public /app prefixes and legacy /api prefixes for bare routers."""
    path = str(request.scope.get("path", "") or "")
    if path.startswith("/app/"):
        remainder = path[len("/app/") :]
        first_segment = remainder.split("/", 1)[0]
        if first_segment in _APP_BASE_API_SEGMENTS:
            request.scope["path"] = f"/{remainder}"
    elif path.startswith("/api/"):
        remainder = path[len("/api/") :]
        first_segment = remainder.split("/", 1)[0]
        if first_segment in _LEGACY_API_PREFIX_SEGMENTS:
            request.scope["path"] = f"/{remainder}"
    return await call_next(request)


def _configure_cors(app_obj: FastAPI, settings_obj) -> None:
    """Attach CORS middleware using the existing production safety policy."""
    from fastapi.middleware.cors import CORSMiddleware

    if not bool(getattr(settings_obj, "cors_enabled", True)):
        return

    cors_origins = settings_obj.cors_origins or []
    allow_all = "*" in cors_origins
    # `Settings.app_env` normalises `prod` to `production`, so one comparison is
    # enough -- and `getattr` keeps working for a stand-in object that has not.
    is_production = normalise_environment_name(getattr(settings_obj, "app_env", None)) == "production"
    if allow_all and is_production:
        raise RuntimeError(
            "Refusing to start: CORS_ALLOW_ORIGINS=='*' is not allowed when APP_ENV is "
            "'prod' or 'production'. Set CORS_ALLOW_ORIGINS to an explicit comma-separated "
            "list of trusted frontend origins (https URLs)."
        )

    app_obj.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if allow_all else cors_origins,
        allow_credentials=bool(getattr(settings_obj, "cors_allow_credentials", True)) and (not allow_all),
        allow_methods=settings_obj.cors_methods,
        allow_headers=settings_obj.cors_headers,
    )


async def shared_state_unavailable(_request: Request, exc: SharedStateUnavailable) -> JSONResponse:
    """Redis holds state every worker must agree on and is not answering: 503, not 500."""

    return shared_state_unavailable_response()


async def index_busy(_request: Request, exc: LockBusy) -> JSONResponse:
    """Another writer holds the document index past the request's wait: 503, retry."""

    return index_busy_response()


def create_app(settings_obj, static_paths: StaticFilePaths | None = None, static_handlers=None) -> FastAPI:
    """Build the public application while preserving the historical order."""
    app = FastAPI(title="QueryMind（智询）", lifespan=lifespan)
    app.add_exception_handler(SharedStateUnavailable, shared_state_unavailable)
    app.add_exception_handler(LockBusy, index_busy)
    app.middleware("http")(rewrite_app_prefixed_api_paths)
    _configure_cors(app, settings_obj)

    # Add security middleware with Redis support
    # No CSRF middleware here on purpose: CSRF is enforced in the auth
    # dependency (_enforce_cookie_csrf), which is the only place that knows
    # whether the request authenticated by cookie -- the one mode that is
    # vulnerable to it. A middleware cannot know that before auth runs, which
    # is why the one that used to sit here checked a cookie nothing set and
    # waved every request through.

    # Rate limiting (prevents brute-force attacks on sensitive endpoints)
    # Now supports Redis for distributed deployments
    rate_limit_enabled = getattr(settings_obj, "rate_limit_enabled", True)
    redis_url = getattr(settings_obj, "redis_url", None)
    if rate_limit_enabled:
        app.add_middleware(
            RateLimitMiddleware,
            redis_url=redis_url,
            shared=getattr(settings_obj, "state_backend", "memory") == "shared",
        )

    app.middleware("http")(request_timing_middleware)
    register_routers(app)
    configure_static_files(app, static_paths, static_handlers)
    return app


__all__ = ["create_app", "lifespan", "rewrite_app_prefixed_api_paths", "shared_state_unavailable", "_configure_cors"]
