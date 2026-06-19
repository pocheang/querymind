# External LLM Redaction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the default Ollama dependency for new sessions and redact sensitive outbound prompt content before any external LLM or embedding call.

**Architecture:** Add a focused outbound redaction service with provider-aware wrappers around chat and embedding models in `app/core/models.py`. Update backend and frontend defaults from `ollama` to `local` so new users start from a non-networked baseline while preserving explicit Ollama support.

**Tech Stack:** FastAPI, Pydantic settings, LangChain model wrappers, React TypeScript, pytest

---

### Task 1: Add provider-aware outbound redaction primitives

**Files:**
- Create: `app/services/outbound_redaction.py`
- Modify: `app/core/config.py`
- Test: `tests/test_outbound_redaction.py`

- [ ] Define regex-based outbound redaction helpers for secrets, URLs, IPs, emails, phone-like strings, file paths, and UUID-like identifiers.
- [ ] Add config flags to enable outbound LLM redaction and outbound embedding redaction by default.
- [ ] Add focused pytest coverage for external-provider redaction and local-provider bypass behavior.

### Task 2: Wrap external chat and embedding models

**Files:**
- Modify: `app/core/models.py`
- Test: `tests/test_model_provider_config.py`

- [ ] Add lightweight proxy wrappers that redact outbound chat messages and embedding texts only for external providers.
- [ ] Keep local and Ollama behavior unchanged while ensuring `openai`, `anthropic`, `deepseek`, and `custom` routes are covered centrally.
- [ ] Add tests proving wrapped external models redact outbound payloads before invoking the inner model.

### Task 3: Switch new-session defaults away from Ollama

**Files:**
- Modify: `app/core/config.py`
- Modify: `app/core/schemas.py`
- Modify: `app/services/model_config_store.py`
- Modify: `app/api/dependencies.py`
- Modify: `app/api/routes/admin_settings.py`
- Modify: `frontend/src/components/apiSettingsConstants.ts`
- Modify: `frontend/src/components/apiSettingsUtils.ts`
- Test: `tests/test_user_api_settings_test_api.py`

- [ ] Change backend schema and route fallbacks from `ollama` to `local` for new users and empty settings.
- [ ] Change frontend default provider payloads from `ollama` to `local` without removing the Ollama option from provider lists.
- [ ] Add or update tests that verify the empty-settings default now resolves to `local`.

### Task 4: Verify the safety slice

**Files:**
- Test: `tests/test_outbound_redaction.py`
- Test: `tests/test_model_provider_config.py`
- Test: `tests/test_user_api_settings_test_api.py`

- [ ] Run the focused pytest subset covering redaction wrappers and default-provider changes.
- [ ] Review failures for unintended Ollama assumptions before widening the rollout.
