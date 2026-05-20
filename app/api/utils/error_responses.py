"""Common error response helpers for FastAPI routes."""
from fastapi import HTTPException


def not_found(resource: str = "Resource") -> HTTPException:
    """Return a 404 Not Found error."""
    return HTTPException(status_code=404, detail=f"{resource} not found")


def bad_request(detail: str) -> HTTPException:
    """Return a 400 Bad Request error."""
    return HTTPException(status_code=400, detail=detail)


def unauthorized(detail: str = "Unauthorized") -> HTTPException:
    """Return a 403 Forbidden error."""
    return HTTPException(status_code=403, detail=detail)


def forbidden(detail: str = "Forbidden") -> HTTPException:
    """Return a 403 Forbidden error (alias for unauthorized)."""
    return HTTPException(status_code=403, detail=detail)


def internal_error(detail: str = "Internal server error") -> HTTPException:
    """Return a 500 Internal Server Error."""
    return HTTPException(status_code=500, detail=detail)


def conflict(detail: str) -> HTTPException:
    """Return a 409 Conflict error."""
    return HTTPException(status_code=409, detail=detail)
