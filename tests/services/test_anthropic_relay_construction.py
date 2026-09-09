"""An Anthropic relay must be constructible, and must inherit the request timeout.

`AnthropicRelayChatModel` exists for exactly one situation -- an Anthropic-
compatible gateway reached at a `base_url` -- and until 2026-09-09 the only code
that constructs it passed `streaming=True`, which its `__init__` does not accept.
So every relay configuration raised

    AnthropicRelayChatModel.__init__() got an unexpected keyword argument 'streaming'

at construction, and the branch had never run. The flag was never needed either:
the adapter streams by having a `stream()` method.

Found by configuring a real relay through the admin console and pressing
Connection Test, which is the first thing that had ever reached this branch.

The timeout half is the quieter one. Every other backend threads
`request_timeout_seconds` through; this branch dropped it and took the 30s
default, so `LLM_REQUEST_TIMEOUT_SECONDS` silently did not apply to the one
provider most likely to sit behind a slow hop.
"""

from __future__ import annotations

import inspect

import pytest

from app.services.models.runtime import AnthropicRelayChatModel, _build_chat_model_cached

RELAY = {
    "provider": "anthropic",
    "backend": "anthropic",
    "temperature": 0.3,
    "openai_model": "",
    "openai_api_key": "",
    "openai_base_url": "",
    "ollama_model": "",
    "ollama_base_url": "",
    "anthropic_model": "claude-sonnet-5",
    "anthropic_api_key": "placeholder-credential-value",
    "anthropic_base_url": "https://relay.example.invalid",
    "max_tokens": 2048,
    "request_timeout_seconds": 17.0,
}


def _unwrap(model):
    """`_wrap_chat_model_for_provider` proxies an external provider for redaction."""
    return getattr(model, "_inner", model)


def test_a_relay_configuration_builds_at_all():
    """The regression proper: this raised `TypeError` for the life of the class."""

    model = _unwrap(_build_chat_model_cached(**RELAY))

    assert isinstance(model, AnthropicRelayChatModel)
    assert model.model == "claude-sonnet-5"
    assert model.base_url == "https://relay.example.invalid"


def test_the_relay_inherits_the_configured_request_timeout():
    """Dropping it left the relay on a 30s default nothing could change."""

    model = _unwrap(_build_chat_model_cached(**{**RELAY, "request_timeout_seconds": 17.0}))

    assert model.timeout_seconds == 17.0, (
        "the relay kept its own default, so LLM_REQUEST_TIMEOUT_SECONDS does not reach it"
    )


def test_the_adapter_streams_by_method_not_by_flag():
    """Why `streaming=True` was wrong rather than merely unsupported.

    If the class took a flag, adding one would have been the fix. It does not:
    it streams because it implements `stream()`, so the caller passing a flag
    was describing a constructor that never existed.
    """

    assert callable(AnthropicRelayChatModel.stream)
    assert "streaming" not in inspect.signature(AnthropicRelayChatModel.__init__).parameters


@pytest.mark.parametrize("field", ["model", "api_key", "base_url", "temperature", "max_tokens"])
def test_every_constructor_argument_is_one_the_class_takes(field: str):
    """Pins the whole call, not just the argument that happened to be wrong.

    A second unsupported keyword would fail identically and for the same reason,
    and only at the moment somebody configures a relay.
    """

    assert field in inspect.signature(AnthropicRelayChatModel.__init__).parameters
