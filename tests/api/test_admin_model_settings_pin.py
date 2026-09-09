"""The model settings page must say whether its settings are in effect.

A deployment can pin the offline backend with `MODEL_BACKEND=local` as a real
environment variable, and `get_chat_model` then discards the global override
outright (`_local_backend_forced`). Before this, `GET /admin/model-settings`
returned only the stored values -- so an admin could fill in an OpenAI key and
model, get a success response, see the values echoed back, and have an audit row
saying the save succeeded, while every answer still came from
`LocalEvidenceChatModel`.

That is the failure this codebase keeps finding in its own surfaces: a page
reporting something other than what runs. `GET /api/advanced-rag/config` had it,
the ops grounding SLO had it, and the audit-action filter had it.

Note what is *not* done here. The configuration page next door refuses a write to
a value the environment pins, because that write would go to a layer the process
does not read. This write persists correctly and takes effect the moment the pin
is removed, so refusing it would block legitimate preparation. It is accepted and
reported inert instead.
"""

from __future__ import annotations

import pytest

from app.api.dependencies import _admin_model_settings_view

_STORED = {
    "enabled": True,
    "provider": "openai",
    # Deliberately not shaped like a real key. This test needs a non-empty
    # string to prove the view masks it, not a credential shape -- and
    # scripts/check_sensitive.py correctly refuses one that has the shape.
    "api_key": "placeholder-credential-value",
    "base_url": "",
    "chat_model": "gpt-5.5",
    "reasoning_model": "",
    "embedding_model": "text-embedding-3-small",
    "temperature": 0.7,
    "max_tokens": 2048,
}


@pytest.fixture
def pinned(monkeypatch):
    monkeypatch.setenv("MODEL_BACKEND", "local")


@pytest.fixture
def unpinned(monkeypatch):
    monkeypatch.delenv("MODEL_BACKEND", raising=False)


def test_a_pinned_environment_is_reported(pinned: None):
    """The assertion that would have caught it."""

    view = _admin_model_settings_view(_STORED).settings

    assert view.environment_pinned is True
    assert "MODEL_BACKEND" in view.pinned_reason


def test_an_unpinned_environment_reports_nothing(unpinned: None):
    """The negative direction, so the test above cannot pass by the flag being
    stuck on."""

    view = _admin_model_settings_view(_STORED).settings

    assert view.environment_pinned is False
    assert view.pinned_reason == ""


def test_the_stored_settings_are_still_returned_when_pinned(pinned: None):
    """Pinned means inert, not lost. The values persist and take effect when the
    pin is removed, which is why the write is accepted rather than refused."""

    view = _admin_model_settings_view(_STORED).settings

    assert view.provider == "openai"
    assert view.chat_model == "gpt-5.5"
    assert view.enabled is True


def test_the_api_key_is_never_returned(pinned: None):
    """Unchanged by this, and worth pinning next to it: the view masks."""

    view = _admin_model_settings_view(_STORED).settings

    assert "placeholder-credential-value" not in view.model_dump_json()
    assert view.api_key_masked


def test_the_enabled_flag_describes_what_it_actually_does():
    """The switch chooses between the administrator's configuration and the
    deployment's environment -- and must not promise a per-user configuration.

    It once read "to users without personal overrides", which was the opposite
    of the code: an enabled global config won over every user's own settings.
    Per-user model configuration was removed on 2026-09-08, so the wording that
    replaced it -- "overriding their personal API settings" -- became wrong the
    other way round, describing a thing users no longer have.
    """

    from app.api.schemas import AdminModelSettings

    description = AdminModelSettings.model_fields["enabled"].description or ""

    assert "without personal overrides" not in description
    assert "personal" not in description.lower()
    assert "every user" in description.lower()


def test_the_checkbox_a_human_reads_says_the_same_thing():
    """The label beside the switch is a separate string, and it drifted.

    `test_the_enabled_flag_describes_what_it_actually_does` above checks the
    schema description -- which no administrator ever sees. What they read is an
    i18n string in the frontend, and on 2026-09-08 that string was left saying
    the switch "replaces every user's own API settings" **after** per-user model
    configuration was deleted. So the backend test passed, and the checkbox
    promised a thing that no longer existed, in both locales.

    Found by opening the page rather than by any check: the two ends had no
    place where they met. This is that place.
    """

    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    key = "enableGlobalModelOverride"

    labels = {}
    for locale in ("en", "zh"):
        data = json.loads((root / "i18n" / "locales" / f"{locale}.json").read_text(encoding="utf-8"))
        labels[locale] = data["admin"]["ui"][key]

    # The inline `defaultValue` renders whenever the key is missing, so it has to
    # be checked too -- it is a second copy of the same claim.
    component = (root / "pages" / "admin" / "AdminModelSettings.tsx").read_text(encoding="utf-8")
    assert key in component, "the label key moved; this guard is now pointing at nothing"

    forbidden_en = ("personal", "own api settings", "their own")
    forbidden_zh = ("\u4e2a\u4eba", "\u81ea\u5df1\u7684 API")

    assert not any(word in labels["en"].lower() for word in forbidden_en), (
        f"the English checkbox promises a per-user configuration: {labels['en']!r}"
    )
    assert not any(word in labels["zh"] for word in forbidden_zh), (
        f"the Chinese checkbox promises a per-user configuration: {labels['zh']!r}"
    )
    assert not any(word in component.lower() for word in forbidden_en), (
        "the inline defaultValue in AdminModelSettings.tsx still promises a per-user configuration"
    )
    # Both locales must say what it does do, not merely avoid the wrong claim.
    assert "every user" in labels["en"].lower()
    assert "\u6240\u6709\u7528\u6237" in labels["zh"]


def test_the_effective_panel_does_not_promise_a_per_user_configuration(monkeypatch: pytest.MonkeyPatch):
    """A third copy of the same claim, in the panel that exists to be authoritative.

    `/admin/model-settings/effective` answers "what will the next question use".
    Both of its chat branches described a per-user configuration -- "including
    those with personal settings" when the global one is on, and "Users with
    personal API settings use their own" when it is off -- which stopped being
    true on 2026-09-08 and stayed on screen.

    Three surfaces described one switch: the schema, the checkbox and this. Each
    was corrected in a different pass, which is the argument for asserting all
    three in one place.
    """

    from app.services.models import effective as effective_module

    forbidden = ("personal settings", "personal api settings")

    monkeypatch.setattr(effective_module, "_local_backend_forced", lambda: False, raising=False)

    for enabled in (True, False):
        stored = {
            "enabled": enabled,
            "provider": "anthropic",
            "chat_model": "claude-sonnet-5",
            "api_key": "placeholder-credential-value",
            "base_url": "https://relay.example.invalid",
            "reasoning_model": "",
            "embedding_model": "",
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        monkeypatch.setattr(effective_module, "get_settings", effective_module.get_settings)
        import app.services.models.config_store as config_store

        monkeypatch.setattr(config_store, "get_global_model_settings", lambda s=stored: s)

        chat = effective_module._chat()
        detail = chat.detail.lower()
        assert not any(word in detail for word in forbidden), (
            f"the effective panel promises a per-user configuration with enabled={enabled}: {chat.detail!r}"
        )
