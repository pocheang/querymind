from types import SimpleNamespace

from app.services.outbound_redaction import (
    redact_messages_for_provider,
    redact_text_for_provider,
    redact_texts_for_provider,
)


def test_redact_text_for_external_provider_masks_common_sensitive_values():
    text = (
        "Contact alice@example.com via https://internal.example.com/runbook "
        "or 10.1.2.3. Token sk-secret-123456 and path C:\\sensitive\\ops.txt."
    )

    out = redact_text_for_provider(text, provider="deepseek")

    assert "alice@example.com" not in out
    assert "https://internal.example.com/runbook" not in out
    assert "10.1.2.3" not in out
    assert "sk-secret-123456" not in out
    assert "C:\\sensitive\\ops.txt" not in out
    assert "<EMAIL_1>" in out
    assert "<URL_1>" in out
    assert "<IP_1>" in out
    assert "<SECRET_1>" in out
    assert "<PATH_1>" in out


def test_redact_messages_reuses_stable_tokens_within_one_payload():
    messages = [
        ("system", "Email alice@example.com and save to /srv/alice/report.txt"),
        ("human", "Repeat alice@example.com and /srv/alice/report.txt"),
    ]

    redacted = redact_messages_for_provider(messages, provider="openai")

    assert redacted[0][1].count("<EMAIL_1>") == 1
    assert redacted[1][1].count("<EMAIL_1>") == 1
    assert redacted[0][1].count("<PATH_1>") == 1
    assert redacted[1][1].count("<PATH_1>") == 1


def test_local_provider_bypasses_redaction():
    text = "admin@example.com sk-secret-123456 /srv/secret.txt"

    assert redact_text_for_provider(text, provider="local") == text
    assert redact_texts_for_provider([text], provider="ollama") == [text]


def test_embedding_redaction_can_be_disabled(monkeypatch):
    monkeypatch.setattr(
        "app.services.outbound_redaction.get_settings",
        lambda: SimpleNamespace(
            outbound_llm_redaction_enabled=True,
            outbound_embedding_redaction_enabled=False,
        ),
    )

    text = "alice@example.com"

    assert redact_text_for_provider(text, provider="openai") != text
    assert redact_texts_for_provider([text], provider="openai", for_embeddings=True) == [text]


def test_redact_messages_handles_nested_multimodal_content():
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Email alice@example.com and save to /srv/alice/report.txt"},
                {"type": "image_url", "image_url": {"url": "https://example.com/image.png"}},
            ],
        }
    ]

    redacted = redact_messages_for_provider(messages, provider="anthropic")

    text_block = redacted[0]["content"][0]
    image_block = redacted[0]["content"][1]
    assert text_block["type"] == "text"
    assert "alice@example.com" not in text_block["text"]
    assert "/srv/alice/report.txt" not in text_block["text"]
    assert "<EMAIL_1>" in text_block["text"]
    assert "<PATH_1>" in text_block["text"]
    assert image_block["image_url"]["url"] == "<URL_1>"


def test_redact_messages_preserves_inline_data_urls_and_base64_fields():
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "BBBB"}},
            ],
        }
    ]

    redacted = redact_messages_for_provider(messages, provider="openai")

    assert redacted[0]["content"][0]["image_url"]["url"] == "data:image/png;base64,AAAA"
    assert redacted[0]["content"][1]["source"]["data"] == "BBBB"


def test_redact_text_supports_custom_terms_and_regexes(monkeypatch):
    monkeypatch.setattr(
        "app.services.outbound_redaction.get_settings",
        lambda: SimpleNamespace(
            outbound_llm_redaction_enabled=True,
            outbound_embedding_redaction_enabled=True,
            outbound_redaction_custom_terms="Project Falcon,Customer Zero",
            outbound_redaction_custom_regexes=r"INC-\d{4}",
        ),
    )

    text = "Project Falcon for Customer Zero is tracked as INC-2048."
    out = redact_text_for_provider(text, provider="deepseek")

    assert "Project Falcon" not in out
    assert "Customer Zero" not in out
    assert "INC-2048" not in out
    assert out.count("<CUSTOM_") == 3


def test_redact_text_reuses_same_token_for_case_variants():
    text = "Email Alice@Example.com then alice@example.com"

    out = redact_text_for_provider(text, provider="openai")

    assert "Alice@Example.com" not in out
    assert "alice@example.com" not in out
    assert out.count("<EMAIL_1>") == 2


def test_invalid_custom_regex_logs_warning(monkeypatch, caplog):
    monkeypatch.setattr(
        "app.services.outbound_redaction.get_settings",
        lambda: SimpleNamespace(
            outbound_llm_redaction_enabled=True,
            outbound_embedding_redaction_enabled=True,
            outbound_redaction_custom_terms="",
            outbound_redaction_custom_regexes="([",
        ),
    )

    out = redact_text_for_provider("hello", provider="openai")

    assert out == "hello"
    assert "Ignoring invalid outbound redaction regex" in caplog.text
