"""Backward-compatible FastAPI app entrypoint."""

from app.api.main import app

__all__ = ["app"]
