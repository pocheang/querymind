"""A redaction token must not reach the reader.

The model is shown `<URL_7>` in place of a URL and writes it back. Observed in a
real answer on 2026-09-09:

    参考来源

    [1] <URL_7>

one paragraph above the pipeline's own reference list showing the actual link.
The token was doing its job -- the provider never saw the URL -- but it means
nothing to a reader, and redaction exists to keep a value from the *provider*,
not from the person who asked about their own document.

**The mapping never leaves one model call**, and that is the point rather than
an implementation detail: a per-request ContextVar or a module-level map would
also work and would risk the one failure that actually matters here, which is
one user's values appearing in another user's answer. A cosmetic token is worth
far less than that, so most of this file is about the boundary rather than the
substitution.
"""

from __future__ import annotations

import pytest

from app.services.security.outbound_redaction import (
    redact_messages_for_provider,
    redact_messages_with_restorer,
)

URL = "https://Example.com/Docs/Runbook.md"


@pytest.fixture(autouse=True)
def _redaction_on(monkeypatch: pytest.MonkeyPatch):
    import app.services.security.outbound_redaction as module

    monkeypatch.setattr(module, "outbound_redaction_enabled", lambda **_: True)


def test_a_token_the_model_echoes_is_put_back():
    messages = [("human", f"Summarise {URL} please")]

    payload, restore = redact_messages_with_restorer(messages, provider="openai")

    sent = str(payload)
    assert URL not in sent, "the provider was shown the real URL"
    assert "<URL_1>" in sent

    # The model echoes the token it was given.
    assert restore("参考来源\n\n[1] <URL_1>") == f"参考来源\n\n[1] {URL}"


def test_the_original_casing_survives():
    """`seen` is keyed on a lower-cased URL so two casings share one token.

    Restoring from that key would hand the reader `https://example.com/docs/...`
    where the document said `Docs/Runbook.md`, and a URL path is case-sensitive.
    """

    _payload, restore = redact_messages_with_restorer([("human", URL)], provider="openai")

    assert restore("see <URL_1>") == f"see {URL}"


def test_longer_tokens_are_restored_first():
    """`<URL_1>` must not eat the prefix of `<URL_11>`."""

    urls = [f"https://example.com/{index}" for index in range(1, 13)]
    _payload, restore = redact_messages_with_restorer([("human", " ".join(urls))], provider="openai")

    restored = restore("<URL_11> and <URL_1>")

    assert restored == f"{urls[10]} and {urls[0]}"


def test_the_mapping_does_not_outlive_the_call():
    """Two calls must not be able to see each other's values.

    This is the failure that would matter: a token from one request resolving to
    another request's URL. The restorer closes over its own state and nothing
    else holds it.
    """

    _first, restore_first = redact_messages_with_restorer(
        [("human", "https://alice.example/private")], provider="openai"
    )
    _second, restore_second = redact_messages_with_restorer(
        [("human", "https://bob.example/private")], provider="openai"
    )

    assert restore_first("<URL_1>") == "https://alice.example/private"
    assert restore_second("<URL_1>") == "https://bob.example/private"
    # And neither can produce the other's value under any token.
    assert "bob.example" not in restore_first("<URL_1> <URL_2> <URL_3>")
    assert "alice.example" not in restore_second("<URL_1> <URL_2> <URL_3>")


def test_a_local_provider_is_neither_redacted_nor_restored():
    """The boundary is unchanged: a local endpoint sits inside it."""

    messages = [("human", URL)]
    payload, restore = redact_messages_with_restorer(messages, provider="ollama")

    assert payload is messages
    assert restore("<URL_1>") == "<URL_1>"


def test_the_old_entry_point_still_redacts():
    """`redact_messages_for_provider` is still what the streaming path and the
    embedding wrapper use; adding a restorer must not have changed it."""

    sent = str(redact_messages_for_provider([("human", URL)], provider="openai"))

    assert URL not in sent
    assert "<URL_1>" in sent


def test_the_streaming_path_is_left_alone_on_purpose():
    """A token can straddle a chunk boundary, and half of one substituted is
    worse than the whole of one left alone. The fragments are a draft the
    frontend replaces with the answer from the query response."""

    import inspect

    from app.services.models.runtime import OutboundRedactedChatModel

    source = inspect.getsource(OutboundRedactedChatModel.stream)

    assert "redact_messages_for_provider" in source
    assert "redact_messages_with_restorer" not in source


def test_the_wrapper_restores_what_the_model_returned(monkeypatch: pytest.MonkeyPatch):
    from app.services.models.runtime import OutboundRedactedChatModel

    class _Reply:
        def __init__(self, content):
            self.content = content

    class _Model:
        def invoke(self, messages):
            # Echo the token back, which is exactly what was observed.
            return _Reply("参考来源\n[1] <URL_1>")

    wrapped = OutboundRedactedChatModel(_Model(), provider="openai")
    reply = wrapped.invoke([("human", f"about {URL}")])

    assert URL in reply.content
    assert "<URL_1>" not in reply.content
