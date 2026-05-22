"""Unit tests for production CORS hardening in app.api.main._configure_cors."""
from types import SimpleNamespace

import pytest
from fastapi import FastAPI

from app.api.main import _configure_cors


def _settings(*, app_env: str, cors_origins: list[str], enabled: bool = True) -> SimpleNamespace:
    """Build a minimal settings stub matching the duck-typed interface."""
    return SimpleNamespace(
        cors_enabled=enabled,
        cors_origins=cors_origins,
        cors_allow_credentials=True,
        cors_methods=["*"],
        cors_headers=["*"],
        app_env=app_env,
    )


def test_wildcard_origins_allowed_in_dev():
    """Dev mode tolerates ``*`` (matches existing behavior)."""
    app = FastAPI()
    _configure_cors(app, _settings(app_env="dev", cors_origins=["*"]))


def test_wildcard_origins_rejected_in_production():
    """Production must refuse to start with wildcard origins."""
    app = FastAPI()
    with pytest.raises(RuntimeError, match="CORS_ALLOW_ORIGINS"):
        _configure_cors(app, _settings(app_env="production", cors_origins=["*"]))


def test_wildcard_origins_rejected_with_short_prod_alias():
    """``prod`` alias is also recognized as production."""
    app = FastAPI()
    with pytest.raises(RuntimeError, match="CORS_ALLOW_ORIGINS"):
        _configure_cors(app, _settings(app_env="prod", cors_origins=["*"]))


def test_explicit_origins_allowed_in_production():
    """Production with an explicit origin allowlist is accepted."""
    app = FastAPI()
    _configure_cors(
        app,
        _settings(
            app_env="production",
            cors_origins=["https://app.example.com", "https://admin.example.com"],
        ),
    )


def test_disabled_cors_skips_validation():
    """When CORS is disabled, the prod wildcard guard does not fire."""
    app = FastAPI()
    _configure_cors(app, _settings(app_env="production", cors_origins=["*"], enabled=False))
