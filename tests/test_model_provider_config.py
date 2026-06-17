from app.core.models import AnthropicRelayChatModel, _build_chat_model_cached, get_chat_model
from app.services.network_security import validate_api_base_url_for_provider
from app.services.request_context import request_context


def test_anthropic_base_url_uses_sdk_root_path():
    assert validate_api_base_url_for_provider("https://api.anthropic.com/v1", provider="anthropic") == "https://api.anthropic.com"
    assert validate_api_base_url_for_provider("https://cc-vibe.com", provider="anthropic") == "https://cc-vibe.com"


def test_openai_compatible_root_base_url_gets_v1_path():
    assert validate_api_base_url_for_provider("https://example.com", provider="custom") == "https://example.com/v1"


def test_anthropic_model_uses_relay_client_for_custom_base_url():
    _build_chat_model_cached.cache_clear()

    model = _build_chat_model_cached(
        backend="anthropic",
        temperature=0.7,
        openai_model="unused",
        openai_api_key="",
        openai_base_url="",
        ollama_model="unused",
        ollama_base_url="",
        anthropic_model="claude-opus-4-8",
        anthropic_api_key="sk-test",
        anthropic_base_url="https://cc-vibe.com",
        max_tokens=2048,
    )

    assert isinstance(model, AnthropicRelayChatModel)
    assert model.base_url == "https://cc-vibe.com"
    assert model.model == "claude-opus-4-8"


def test_anthropic_relay_message_payload_maps_system_and_user_messages():
    model = AnthropicRelayChatModel(
        model="claude-opus-4-8",
        api_key="sk-test",
        base_url="https://cc-vibe.com",
        temperature=0.7,
        max_tokens=2048,
    )

    payload = model._message_payload([("system", "system prompt"), ("human", "hello")])

    assert payload["system"] == "system prompt"
    assert payload["messages"] == [{"role": "user", "content": "hello"}]


def test_anthropic_relay_extracts_multiple_response_shapes():
    model = AnthropicRelayChatModel(
        model="claude-opus-4-8",
        api_key="sk-test",
        base_url="https://cc-vibe.com",
    )

    assert model._extract_content({"content": [{"type": "text", "text": "OK"}]}) == "OK"
    assert model._extract_content({"content": "OK"}) == "OK"
    assert model._extract_content({"choices": [{"message": {"content": "OK"}}]}) == "OK"


def test_anthropic_relay_invoke_accepts_string_content_response(monkeypatch):
    model = AnthropicRelayChatModel(
        model="claude-opus-4-8",
        api_key="sk-test",
        base_url="https://cc-vibe.com",
    )
    seen = {}

    class Response:
        status_code = 200
        text = '{"content":"OK"}'

        def json(self):
            return {"content": "OK"}

    def fake_post(url, headers, json, timeout):
        seen["url"] = url
        seen["headers"] = headers
        seen["json"] = json
        seen["timeout"] = timeout
        return Response()

    monkeypatch.setattr("httpx.post", fake_post)

    result = model.invoke([("system", "reply OK"), ("human", "test")])

    assert result.content == "OK"
    assert seen["url"] == "https://cc-vibe.com/v1/messages"
    assert seen["json"]["messages"] == [{"role": "user", "content": "test"}]


def test_custom_provider_with_claude_model_uses_anthropic_relay_client():
    _build_chat_model_cached.cache_clear()

    with request_context(
        timeout_ms=12000,
        overload_mode=False,
        api_settings={
            "provider": "custom",
            "api_key": "sk-test",
            "base_url": "https://cc-vibe.com",
            "model": "claude-opus-4-8",
            "temperature": 0.7,
            "max_tokens": 2048,
        },
    ):
        model = get_chat_model()

    assert isinstance(model, AnthropicRelayChatModel)
    assert model.base_url == "https://cc-vibe.com"
    assert model.model == "claude-opus-4-8"
