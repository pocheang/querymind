"""Common error response helpers for FastAPI routes.

The helpers below *raise* the errors; `error_responses` *declares* them, so the
OpenAPI document says what a route can return. Those were separate facts until
2026-09-02: a route raising `conflict(...)` documented only its 200, and the
generated document told a client the call could not fail -- `python:S8415`.

One place for the descriptions, because fifty-three route decorators writing
their own would be fifty-three chances to describe the same 400 differently.
"""

from typing import Any

from fastapi import HTTPException

_ERROR_DESCRIPTIONS: dict[int, str] = {
    400: "The request was rejected by validation.",
    401: "Authentication is required.",
    403: "The caller lacks the required permission.",
    404: "No such resource, or none visible to this caller.",
    409: "The request conflicts with the current state of the resource.",
    413: "The payload exceeds the configured limit.",
    422: "The request body did not match the expected schema.",
    429: "Rate limit exceeded; retry after the interval in the Retry-After header.",
    500: "The request failed for a reason the caller cannot act on.",
    501: "Not implemented.",
    503: "A dependency this endpoint needs is unavailable; retry later.",
}


def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    """Declare the failures a route can return, for the OpenAPI document.

    404 and 403 deliberately describe *visibility* rather than existence: the
    document should not promise a caller that a resource it cannot see exists.
    """

    return {code: {"description": _ERROR_DESCRIPTIONS[code]} for code in sorted(set(status_codes))}


def not_found(resource: str = "Resource") -> HTTPException:
    """Return a 404 Not Found error."""
    return HTTPException(status_code=404, detail=f"{resource} not found")


def bad_request(detail: str) -> HTTPException:
    """Return a 400 Bad Request error."""
    return HTTPException(status_code=400, detail=detail)


def unauthorized(detail: str = "Unauthorized") -> HTTPException:
    """Return a 401 Unauthorized error."""
    return HTTPException(status_code=401, detail=detail)


def forbidden(detail: str = "Forbidden") -> HTTPException:
    """Return a 403 Forbidden error (alias for unauthorized)."""
    return HTTPException(status_code=403, detail=detail)


def internal_error(detail: str = "Internal server error") -> HTTPException:
    """Return a 500 Internal Server Error."""
    return HTTPException(status_code=500, detail=detail)


def conflict(detail: str) -> HTTPException:
    """Return a 409 Conflict error."""
    return HTTPException(status_code=409, detail=detail)


def accepted(detail: str = "Request accepted for processing", headers: dict[str, str] | None = None) -> HTTPException:
    """Return a 202 Accepted response (for async operations)."""
    return HTTPException(status_code=202, detail=detail, headers=headers or {})


def rate_limited(detail: str = "Too many requests, retry later") -> HTTPException:
    """Return a 429 Rate Limited error."""
    return HTTPException(status_code=429, detail=detail)


def service_unavailable(detail: str = "Service temporarily overloaded, retry later") -> HTTPException:
    """Return a 503 Service Unavailable error."""
    return HTTPException(status_code=503, detail=detail)


def not_implemented(detail: str = "Not implemented") -> HTTPException:
    """Return a 501 Not Implemented error."""
    return HTTPException(status_code=501, detail=detail)


def index_busy_response():
    """503 for "another writer holds the document index" (ARC-01 phase 5).

    A delete waits `INDEX_LOCK_REQUEST_TIMEOUT_SECONDS` for an ingest's commit
    and then answers this rather than holding a worker thread. Nothing has been
    changed, so retrying is safe.
    """

    from fastapi.responses import JSONResponse

    from app.core.config import get_settings

    retry_after = max(1, int(round(float(get_settings().index_lock_request_timeout_seconds))))
    return JSONResponse(
        status_code=503,
        content={
            "detail": "The document index is being written by another request. Nothing was changed; retry shortly.",
            "error_code": "INDEX_BUSY",
        },
        headers={"Retry-After": str(retry_after)},
    )


def shared_state_unavailable_response():
    """503 for "the shared state store (Redis) is not answering" (ARC-01).

    One builder for both places that produce it: the application's exception
    handler for `SharedStateUnavailable`, and the rate-limit middleware, which
    sits outside the layer that runs exception handlers and so has to answer
    itself. 500 would say "look at this service"; 503 says "look at what it
    depends on", and only the second is true. Retry-After matches the
    connector's cooldown, which is when the next request will try Redis again.
    """

    from fastapi.responses import JSONResponse

    from app.services.runtime.redis_connector import COOLDOWN_SECONDS

    return JSONResponse(
        status_code=503,
        content={
            "detail": "Temporarily unavailable: the shared state store is not reachable. Retry shortly.",
            "error_code": "SHARED_STATE_UNAVAILABLE",
        },
        headers={"Retry-After": str(int(COOLDOWN_SECONDS))},
    )
