"""
Request middleware for the QueryMind API.
"""

import threading
import time
import uuid
from collections import deque
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from fastapi import Request

from app.core.config import get_settings
from app.services.runtime.runtime_metrics import record_request, request_kind

# Global metrics storage.
#
# The deque is built on first use rather than at import: its bound is a Settings
# field now, and Settings is not loaded yet while this module is being imported.
_request_metrics_lock = threading.Lock()
_request_metrics: deque[dict[str, Any]] | None = None


def _metrics() -> deque[dict[str, Any]]:
    """The request-metrics ring, sized from settings on first use.

    Call only while holding `_request_metrics_lock`.
    """

    global _request_metrics
    if _request_metrics is None:
        _request_metrics = deque(maxlen=get_settings().request_metrics_maxlen)
    return _request_metrics


def record_grounding_support(request: Request, execution_metadata: Mapping[str, Any]) -> None:
    """Attach this answer's grounding ratio to the request's own metrics row.

    The row is written in ``request_timing_middleware``'s ``finally``, after the
    endpoint has returned, so the value has to travel on ``request.state`` --
    which is backed by the shared ASGI scope dict that ``call_next`` hands
    downstream and reads back.  A ContextVar cannot carry it: ``call_next`` runs
    the endpoint in its own task, so nothing it sets is visible up here.

    This is where a per-answer quality metric belongs, rather than in the audit
    log: ``build_ops_alerts`` already reads these rows for its p95, so the SLO
    gets one window and one source, and the ring is bounded, where one audit row
    per query would flush every login failure out of the 2000-row window that
    ``list_audit_logs`` hands its readers.
    """

    ratio = (execution_metadata.get("grounding") or {}).get("support_ratio")
    if isinstance(ratio, int | float) and not isinstance(ratio, bool):
        request.state.grounding_support = float(ratio)


async def request_timing_middleware(request: Request, call_next):
    """Middleware to track request timing and add security headers."""
    started = time.perf_counter()
    status_code = 500
    error_text = ""
    trace_id = request.headers.get("x-trace-id", "").strip() or uuid.uuid4().hex
    request.state.trace_id = trace_id
    try:
        response = await call_next(request)
        status_code = response.status_code

        # Add trace ID
        response.headers["X-Trace-Id"] = trace_id

        # Security headers - prevent common attacks
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")  # Changed from DENY to allow same-origin frames
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
        )

        # Content Security Policy - prevent XSS and injection attacks
        # Check if strict CSP is enabled (requires nonce support in frontend)
        use_strict_csp = get_settings().strict_csp

        if use_strict_csp:
            # Stricter CSP without unsafe-inline/unsafe-eval
            # Requires frontend to use nonces for inline scripts/styles
            csp_directives = [
                "default-src 'self'",
                "script-src 'self'",  # No unsafe-inline or unsafe-eval
                "style-src 'self'",  # No unsafe-inline
                "img-src 'self' data: blob: https:",
                "font-src 'self' data:",
                "connect-src 'self' http://localhost:8000 http://127.0.0.1:8000",
                "frame-ancestors 'self'",
                "base-uri 'self'",
                "form-action 'self'",
                "object-src 'none'",
                "upgrade-insecure-requests",
            ]
        else:
            # Relaxed CSP for compatibility with React/Vite
            csp_directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Allow inline scripts for React
                "style-src 'self' 'unsafe-inline'",  # Allow inline styles
                "img-src 'self' data: blob: https:",  # Allow images from self, data URIs, blob, and HTTPS
                "font-src 'self' data:",
                "connect-src 'self' http://localhost:8000 http://127.0.0.1:8000",  # API calls (dev + prod)
                "frame-ancestors 'self'",  # Allow framing from same origin
                "base-uri 'self'",
                "form-action 'self'",
                "object-src 'none'",  # Block plugins
                "upgrade-insecure-requests",  # Upgrade HTTP to HTTPS
            ]

        response.headers.setdefault("Content-Security-Policy", "; ".join(csp_directives))

        # HSTS - force HTTPS (only if using HTTPS)
        if request.url.scheme == "https":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

        return response
    except Exception as e:
        error_text = type(e).__name__
        raise
    finally:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        metric = {
            "ts": datetime.now(UTC).isoformat(),
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": elapsed_ms,
            "error": error_text,
            # None on every request that did not produce an answer, which is what
            # keeps the grounding SLO's denominator honest.
            "grounding_support": getattr(request.state, "grounding_support", None),
        }
        with _request_metrics_lock:
            _metrics().append(metric)
        # Exported by /metrics. It used to go into an instance of its own that
        # /metrics never rendered, so no scrape ever described a request.
        record_request(status_code, elapsed_ms / 1000.0, request_kind(request.method, request.url.path))


def get_request_metrics() -> list[dict[str, Any]]:
    """Get recent request metrics."""
    with _request_metrics_lock:
        return list(_metrics())


# Probes answer about this process and must not depend on Redis answering.
_INVALIDATION_EXEMPT_PREFIXES = ("/health", "/ready", "/metrics", "/api/health", "/api/ready")


async def invalidation_middleware(request, call_next):
    """Bring this worker's caches up to date before the request reads any (ARC-01 phase 6).

    One MGET per request, off the event loop -- and so is any clearing it
    triggers, since a configuration reload rebuilds the query runtime. Redis not
    answering is a 503 like any other shared state: answering from caches that
    may still hold a deleted document is not something to do quietly.
    """
    import asyncio

    from app.services.runtime.invalidation import catch_up
    from app.services.runtime.shared_state import SharedStateUnavailable, is_shared

    if is_shared() and not request.url.path.startswith(_INVALIDATION_EXEMPT_PREFIXES):
        try:
            await asyncio.to_thread(catch_up)
        except SharedStateUnavailable:
            from app.api.transport.errors import shared_state_unavailable_response

            return shared_state_unavailable_response()
    return await call_next(request)
