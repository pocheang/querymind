"""Models are configured by an administrator, and that configuration applies to
every user. An ordinary user has no model configuration of their own.

This was already how answers were produced before 2026-09-08, but only by
accident. Three `/user/api-settings` endpoints let any signed-in user save a
provider, a base URL, a model and an API key; the key was encrypted into their
row; a Test button reported a green success because it probed the posted values
directly; and the drawer echoed everything back as saved. Nothing on the answer
path ever loaded any of it: `_REQUEST_API_SETTINGS` was set with content only by
the probe, so `_request_chat_override()` returned an empty dict for every
question ever asked.

A credential collected under a promise nobody keeps is worse than a missing
feature, so most of this file is negative -- it pins the ways the surface could
come back rather than the one way it now behaves.
"""

from __future__ import annotations

import ast
import inspect
import json
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[2] / "app"


def _openapi_paths() -> dict:
    import app.api.main as main

    return main.app.openapi()["paths"]


def test_no_endpoint_lets_a_user_save_a_model_configuration():
    """The three retired paths must not come back under any method."""

    paths = _openapi_paths()
    assert not [p for p in paths if "api-settings" in p], (
        "A per-user model configuration endpoint is back. Model configuration is "
        "an administrator's, and applies to everyone."
    )


def test_the_only_model_configuration_a_user_can_reach_is_read_only():
    """`/user/active-model` reports; it must never accept."""

    operations = _openapi_paths()["/user/active-model"]
    assert set(operations) == {"get"}, f"expected a read-only report, got {sorted(operations)}"


def test_every_model_configuration_write_is_an_admin_path():
    """A body shaped like a model configuration may only be posted to `/admin/`."""

    paths = _openapi_paths()
    offenders = [
        f"{method.upper()} {path}"
        for path, operations in paths.items()
        for method, operation in operations.items()
        if method in {"post", "put", "patch"}
        and "AdminModelSettings" in json.dumps(operation.get("requestBody", {}))
        and not path.startswith("/admin/")
    ]
    assert not offenders, f"model configuration accepted outside /admin/: {offenders}"


def test_the_request_context_cannot_carry_a_model_configuration():
    """The seam the retired feature used has to be gone, not merely unused.

    It was unused for the whole life of that feature, and that is exactly why
    nobody noticed the feature did nothing. A parameter here is an invitation to
    wire a per-user model back in one call site at a time.
    """

    from app.services.runtime.request_context import request_context

    parameters = set(inspect.signature(request_context).parameters)
    assert parameters == {"timeout_ms", "overload_mode"}, (
        f"request_context grew a parameter: {sorted(parameters)}. It carries a deadline "
        "and an overload flag; a model configuration is not per-request state."
    )


def test_no_module_resolves_a_model_from_a_per_user_override():
    """`get_chat_model` must consult one source, not fall back to a second."""

    source = (APP / "services" / "models" / "runtime.py").read_text(encoding="utf-8")
    assert "user_override" not in source, (
        "`get_chat_model` used to read the global override or a per-user one. The second "
        "operand is what made a per-user configuration look supported."
    )
    assert "get_request_api_settings" not in source


def test_the_probe_tests_the_configuration_it_is_given(monkeypatch: pytest.MonkeyPatch):
    """Test is pressed *before* Save, so it must not answer from what is saved.

    It did until 2026-09-08: it published its payload into a ContextVar and let
    `get_chat_model` pick it up, and `get_chat_model` reads the saved global
    configuration first. So testing a new provider while a global configuration
    was already enabled probed the old one and reported its success as the new
    one's -- an administrator would have saved a configuration they believed
    they had checked.
    """

    from app.services.models import runtime

    saved = {
        "enabled": True,
        "provider": "openai",
        # Deliberately not shaped like a real key: this needs a non-empty
        # string, not a credential shape, and scripts/check_sensitive.py
        # correctly refuses one that has the shape.
        "api_key": "placeholder-credential-value",
        "base_url": "",
        "chat_model": "the-saved-model",
        "reasoning_model": "",
        "embedding_model": "",
        "temperature": 0.7,
        "max_tokens": 2048,
    }
    monkeypatch.setattr(runtime, "get_global_model_settings", lambda: saved)
    monkeypatch.setattr(runtime, "_local_backend_forced", lambda: False)

    built: list[str] = []

    class _Reply:
        content = "OK"

    class _Model:
        def invoke(self, messages):
            return _Reply()

    def _fake_build(**kwargs):
        built.append(kwargs["openai_model"])
        return _Model()

    monkeypatch.setattr(runtime, "_build_chat_model_cached", _fake_build)

    result = runtime.probe_chat_model_configuration(
        {
            "provider": "openai",
            "api_key": "placeholder-credential-value",
            "base_url": "https://api.example.invalid/v1",
            "model": "the-typed-model",
            "temperature": 0.7,
            "max_tokens": 2048,
        },
        success_message="ok",
    )

    assert result["ok"] is True, result["message"]
    assert built == ["the-typed-model"], f"the probe built {built}; it must test what was typed"
    assert result["model"] == "the-typed-model"


def test_the_active_model_report_obeys_the_environment_pin(monkeypatch: pytest.MonkeyPatch):
    """With `MODEL_BACKEND=local` pinned, the saved configuration is discarded.

    Reporting it as active would tell a reader the opposite of what answers
    their question -- the same failure `/admin/model-settings` was fixed for.
    """

    from app.services.models import runtime

    saved = {"enabled": True, "provider": "openai", "chat_model": "gpt-5.5"}
    monkeypatch.setattr(runtime, "get_global_model_settings", lambda: saved)

    monkeypatch.setattr(runtime, "_local_backend_forced", lambda: False)
    assert runtime.active_admin_chat_model() == {
        "managed_by_admin": True,
        "provider": "openai",
        "model": "gpt-5.5",
    }

    monkeypatch.setattr(runtime, "_local_backend_forced", lambda: True)
    assert runtime.active_admin_chat_model() == {
        "managed_by_admin": False,
        "provider": "",
        "model": "",
    }


@pytest.fixture
def auth_service(monkeypatch: pytest.MonkeyPatch) -> Iterator[object]:
    """An `AuthDBService` over a database of this test's own.

    Deliberately not pytest's temporary-path fixture, for the reason
    `tests/services/test_admin_bootstrap.py` gives: its basetemp root needs
    permissions that are not available on every Windows checkout.

    **It supplies its own encryption key, and that is not incidental.**
    `set_user_metadata` encrypts the api-settings payload, and
    `_api_settings_data_key` refuses to invent a key -- auto-generation is
    disabled on purpose. A developer machine has one in `.runtime/`, so
    omitting it here passed locally and failed on every fresh clone and in CI,
    which is exactly the trap CLAUDE.md records for `test_dev_compose_is_usable`.
    The three suites under `tests/mcp/` already did this; this one did not.
    """

    from app.core.config import get_settings
    from app.services.auth.auth_service import AuthDBService

    root = Path(tempfile.mkdtemp(prefix="querymind-model-config-"))
    monkeypatch.setenv("APP_DB_PATH", str(root / "app.db"))
    monkeypatch.setenv("API_SETTINGS_ENCRYPTION_KEY", "test-key-for-retired-user-model-settings")
    get_settings.cache_clear()
    try:
        yield AuthDBService()
    finally:
        get_settings.cache_clear()
        shutil.rmtree(root, ignore_errors=True)


def test_a_retired_per_user_configuration_is_cleared(auth_service):
    """The stored key is the part deleting the endpoints does not reach.

    An encrypted provider credential that nothing reads is the only kind whose
    disclosure costs its owner everything and buys them nothing.
    """

    from app.services.models.config_store import USER_API_SETTINGS_KEY, purge_user_api_settings

    created = auth_service.register("someone", "Sup3r-Str0ng-Pass!")
    user_id = created["user_id"] if isinstance(created, dict) else created
    auth_service.set_user_metadata(
        user_id,
        USER_API_SETTINGS_KEY,
        {"provider": "openai", "api_key": "placeholder-credential-value", "model": "gpt-5.5"},
    )
    auth_service.set_user_metadata(user_id, "preferences", {"language": "zh"})
    assert auth_service.get_user_metadata(user_id, USER_API_SETTINGS_KEY) is not None

    assert purge_user_api_settings() == 1
    assert auth_service.get_user_metadata(user_id, USER_API_SETTINGS_KEY) is None

    # Unrelated settings survive: this retires one key, it does not reset accounts.
    assert auth_service.get_user_metadata(user_id, "preferences") == {"language": "zh"}

    # Idempotent, so running it on every startup is free after the first.
    assert purge_user_api_settings() == 0


def test_the_purge_runs_at_startup():
    """A purge nothing calls is the defect this whole file is about."""

    source = (APP / "api" / "application" / "lifespan.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    called = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert "_purge_retired_user_model_settings" in called
