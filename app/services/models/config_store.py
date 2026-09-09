from __future__ import annotations

import math
from typing import Any

from app.core.config import get_settings
from app.domain.text import normalize_string
from app.services.auth.auth_service import AuthDBService
from app.services.models.catalog import get_model_catalog, provider_defaults, provider_supports_embeddings
from app.services.security.network import validate_api_base_url_for_provider

GLOBAL_MODEL_SETTINGS_KEY = "global_model_settings"
# The users table still carries this key on rows written before 2026-09-08, when
# per-user model configuration was removed. `purge_user_api_settings` clears it.
USER_API_SETTINGS_KEY = "api_settings"
PROVIDERS = set(get_model_catalog())


class ModelSettingsReindexError(RuntimeError):
    """Keep the persisted settings available when an embedding rebuild fails."""

    def __init__(self, settings_data: dict[str, Any], cause: Exception) -> None:
        self.settings_data = dict(settings_data)
        self.cause = cause
        super().__init__(str(cause))


def default_global_model_settings() -> dict[str, Any]:
    settings = get_settings()
    provider = str(settings.model_backend or "local").strip().lower()
    if provider not in PROVIDERS:
        provider = "local"
    return {
        "enabled": False,
        "provider": provider,
        "api_key": "",
        "base_url": _default_base_url(provider),
        "chat_model": _default_chat_model(provider),
        "reasoning_model": _default_reasoning_model(provider),
        "embedding_model": _default_embedding_model(provider),
        "temperature": 0.7,
        "max_tokens": 2048,
    }


def _default_base_url(provider: str) -> str:
    settings = get_settings()
    provider = normalize_string(provider, lowercase=True)
    if provider == "ollama":
        return str(settings.ollama_base_url or provider_defaults(provider)["base_url"]).rstrip("/")
    if provider == "openai":
        return str(settings.openai_base_url or provider_defaults(provider)["base_url"]).rstrip("/")
    return provider_defaults(provider)["base_url"]


def _default_chat_model(provider: str) -> str:
    settings = get_settings()
    provider = normalize_string(provider, lowercase=True)
    if provider == "ollama":
        return str(settings.ollama_chat_model or provider_defaults(provider)["chat_model"])
    if provider == "openai":
        return str(settings.openai_chat_model or provider_defaults(provider)["chat_model"])
    if provider == "anthropic":
        return str(settings.anthropic_chat_model or provider_defaults(provider)["chat_model"])
    return provider_defaults(provider)["chat_model"]


def _default_reasoning_model(provider: str) -> str:
    settings = get_settings()
    provider = normalize_string(provider, lowercase=True)
    if provider == "ollama":
        return str(settings.ollama_reasoning_model or provider_defaults(provider)["reasoning_model"])
    if provider == "openai":
        return str(
            settings.openai_reasoning_model
            or settings.openai_chat_model
            or provider_defaults(provider)["reasoning_model"]
        )
    if provider == "anthropic":
        return str(
            settings.anthropic_reasoning_model
            or settings.anthropic_chat_model
            or provider_defaults(provider)["reasoning_model"]
        )
    return provider_defaults(provider)["reasoning_model"]


def _default_embedding_model(provider: str) -> str:
    settings = get_settings()
    provider = normalize_string(provider, lowercase=True)
    if not provider_supports_embeddings(provider):
        return ""
    if provider == "ollama":
        return str(settings.ollama_embed_model or provider_defaults(provider)["embedding_model"])
    if provider in {"openai", "custom"}:
        return str(settings.openai_embed_model or provider_defaults("openai")["embedding_model"])
    return provider_defaults(provider)["embedding_model"]


def normalize_persisted_temperature(value: Any, *, default: float = 0.7) -> float:
    try:
        temperature = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    if not math.isfinite(temperature):
        return default
    return min(1.0, max(0.0, temperature))


def _normalize_global_model_settings(raw: dict[str, Any]) -> dict[str, Any]:
    current = default_global_model_settings()
    current.update({k: v for k, v in dict(raw or {}).items() if v is not None})
    provider = str(current.get("provider", "") or "").strip().lower()
    if provider not in PROVIDERS:
        raise ValueError("unsupported provider")
    base_url = str(current.get("base_url", "") or "").strip().rstrip("/")
    if provider == "ollama":
        base_url = base_url.removesuffix("/v1")
    if provider != "local":
        if not base_url:
            raise ValueError("base_url is required")
        base_url = validate_api_base_url_for_provider(base_url, provider=provider)
    else:
        base_url = ""
    chat_model = str(current.get("chat_model", "") or current.get("model", "") or "").strip()
    reasoning_model = str(current.get("reasoning_model", "") or chat_model).strip()
    embedding_model = str(current.get("embedding_model", "") or "").strip()
    if not chat_model:
        raise ValueError("chat_model is required")
    if provider_supports_embeddings(provider) and not embedding_model:
        raise ValueError("embedding_model is required")
    api_key = str(current.get("api_key", "") or "").strip()
    if provider in {"openai", "anthropic", "deepseek", "custom"} and not api_key:
        raise ValueError("api_key is required for this provider")
    if provider in {"local", "ollama"}:
        api_key = ""
    return {
        "enabled": bool(current.get("enabled", False)),
        "provider": provider,
        "api_key": api_key,
        "base_url": base_url,
        "chat_model": chat_model,
        "reasoning_model": reasoning_model,
        "embedding_model": embedding_model,
        "temperature": normalize_persisted_temperature(current.get("temperature", 0.7)),
        "max_tokens": min(131072, max(256, int(current.get("max_tokens", 2048) or 2048))),
    }


def get_global_model_settings() -> dict[str, Any]:
    stored = AuthDBService().get_system_metadata(GLOBAL_MODEL_SETTINGS_KEY)
    if not isinstance(stored, dict):
        return default_global_model_settings()
    try:
        return _normalize_global_model_settings(stored)
    except ValueError:  # includes OutboundURLValidationError, which derives from it
        safe = default_global_model_settings()
        safe["enabled"] = False
        return safe


def _reuse_existing_api_key(raw: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    payload = dict(raw or {})
    provider = normalize_string(payload.get("provider"), lowercase=True)
    incoming_api_key = str(payload.get("api_key", "") or "").strip()
    current_provider = normalize_string(current.get("provider"), lowercase=True)
    if not incoming_api_key and provider == current_provider:
        payload["api_key"] = str(current.get("api_key", "") or "").strip()
    return payload


def save_global_model_settings(raw: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_global_model_settings(_reuse_existing_api_key(raw, get_global_model_settings()))
    AuthDBService().set_system_metadata(GLOBAL_MODEL_SETTINGS_KEY, normalized)
    return normalized


def global_model_settings_probe_payload(raw: dict[str, Any]) -> dict[str, Any]:
    payload = _reuse_existing_api_key(raw, get_global_model_settings())
    payload["enabled"] = bool(payload.get("enabled", False))
    normalized = _normalize_global_model_settings(payload)
    return {
        "provider": normalized["provider"],
        "api_key": normalized["api_key"],
        "base_url": normalized["base_url"],
        "model": normalized["chat_model"],
        "temperature": normalized["temperature"],
        "max_tokens": normalized["max_tokens"],
    }


def purge_user_api_settings() -> int:
    """Drop every stored per-user model configuration; return how many were removed.

    Per-user model configuration was removed on 2026-09-08 -- models are
    configured by an administrator, and that configuration applies to every
    user. What rows written before then still carry is an encrypted third-party
    API key that nothing reads: a credential with no purpose, which is the only
    kind whose disclosure costs its owner everything and buys them nothing.

    Idempotent, so running it on every startup is free after the first.
    """
    return AuthDBService().clear_user_metadata_key(USER_API_SETTINGS_KEY)


def apply_global_model_settings(raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Persist global settings and rebuild embeddings only when their signature changed."""
    from app.retrievers.stores.vector import clear_vector_store_cache
    from app.services.documents.index_manager import rebuild_all_vector_index
    from app.services.models.runtime import clear_model_caches
    from app.services.runtime.rag_runtime_scope import embedding_settings_signature

    current = get_global_model_settings()
    embedding_before = embedding_settings_signature(current)
    saved = save_global_model_settings(raw)
    clear_model_caches()
    clear_vector_store_cache()
    if embedding_settings_signature(saved) == embedding_before:
        return saved, None
    try:
        return saved, rebuild_all_vector_index()
    except Exception as error:
        raise ModelSettingsReindexError(saved, error) from error


def mask_api_key(api_key: str) -> str:
    value = str(api_key or "").strip()
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


def public_global_model_settings(settings_data: dict[str, Any]) -> dict[str, Any]:
    out = dict(settings_data)
    out["api_key_masked"] = mask_api_key(str(out.pop("api_key", "") or ""))
    return out
