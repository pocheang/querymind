from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from app.core.config import get_settings
from app.domain.text import normalize_string

logger = logging.getLogger(__name__)

EXTERNAL_PROVIDERS = {"openai", "anthropic", "deepseek", "custom"}
_STRUCTURAL_STRING_KEYS = {
    "role",
    "type",
    "media_type",
    "mime_type",
    "finish_reason",
    "tool_name",
    "tool_call_id",
    "id",
}
_BINARY_PAYLOAD_KEYS = {"data", "b64_json", "image", "images"}

_SECRET_PATTERNS = [
    re.compile(r"\b(?:sk|rk|pk)-[A-Za-z0-9_\-]{6,}\b"),
    # The whitespace runs are bounded, not `\s+`/`\s*`. An unbounded run means no
    # finite look-back can prove a match does not straddle a chunk boundary, which
    # is what app/privacy/streaming.py needs in order to redact a stream safely.
    # Eight is far past anything a real credential line contains.
    re.compile(r"\b[Bb][Ee][Aa][Rr][Ee][Rr]\s{1,8}[A-Za-z0-9._\-]{8,}\b"),
    re.compile(r"\b(?:api[_-]?key|token|secret|password)\s{0,8}[:=]\s{0,8}\S+\b", flags=re.IGNORECASE),
]
_URL_RE = re.compile(r"https?://[^\s'\"<>]+", flags=re.IGNORECASE)
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_UUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b")
_WINDOWS_PATH_RE = re.compile(r"\b[A-Za-z]:\\(?:[^\\\s]+\\)*[^\\\s]*")
_UNIX_PATH_RE = re.compile(r"/(?:[^/\s]+/)+[^/\s]+")
# `[\d()\-\s]` treats a dash and a space as free filler, so this rule used to
# claim any digit run of the right length that happened to contain one -- and two
# of those shapes are not phone numbers in any reading. Measured on the shipped
# pattern through the live `filter_output`:
#
#     Log4Shell 是 CVE-2021-44228           -> Log4Shell 是 CVE-<PHONE_1>
#     备份保留窗口为 2026-01-01 至 2026-12-31   -> 备份保留窗口为 <PHONE_1> 至 <PHONE_2>
#     2026-09-21 12:00 告警，2026-09-21 12:40 隔离
#                                           -> <PHONE_1>:00 告警，<PHONE_1>:40 隔离
#
# This is the failure recorded just below for China-specific identifiers -- the
# generic rule owning a specific one's span and reporting it under the wrong
# name -- reached from the other side: here the span is not sensitive at all, so
# the redaction destroys text both the reader and the model need. The third line
# is worse than noise: tokenization is stable by value, so two DIFFERENT
# timestamps collapse into one token and an incident timeline reads as two
# events at the same moment.
#
# `privacy_permission` REPLACES `request.question` with the inspected text, so
# this ran inbound too: a question about CVE-2021-44228 reached the router, the
# retrievers and `querymind_cyber_cve_lookup` as `CVE-<PHONE_1>`, in an
# application whose skills include `cyber_attack_analysis`.
#
# A CVE id and a calendar date are public by construction, so the fix is to
# match NOTHING rather than to match under a better name. A new kind would also
# have to be added to the sets in app/privacy/text.py to have any effect at all
# (`test_every_pattern_kind_is_reachable`), and a kind whose only purpose is to
# hide a public identifier is a redaction that buys nobody anything.
#
# THREE lookarounds, and the second exists because the first two are not enough.
# Rejecting a start AT the year only moves the start INSIDE the date -- the scan
# restarts at the next offset, and `-` is not `\w` so `(?<!\w)` lets it in.
# Measured, with only the CVE and date rules in place:
#
#     '2013-9-1 1997-11-14'  ->  matched '9-1 1997-11-14'
#
# `(?<!\d-)` forbids starting immediately after a dashed digit group, which is
# what makes two adjacent dates survive whole. It cannot cost a real number: a
# phone written `+86-138-0013-8000` is matched from its `+`, and an eleven-digit
# mainland number preceded by `2021-` is MOBILE_CN's, which runs first.
#
# Deliberately STILL matched, because shape alone cannot separate these from a
# national number: a bare `2021-44228` with no prefix, a range like `8000-9000`,
# and a plain ten-digit run. `test_phone_false_positives.py` pins those as
# matching too, so the boundary is stated rather than discovered.
_PHONE_RE = re.compile(
    # a CVE identifier's digits are not a phone number
    r"(?<![Cc][Vv][Ee]-)"
    # nor is a fragment that starts inside a dashed digit group
    r"(?<!\d-)"
    r"(?<!\w)\+?"
    # nor is a calendar date, or a calendar date followed by a clock time
    r"(?!(?:19|20)\d{2}-\d{1,2}-\d{1,2}(?!\d))"
    r"\d[\d()\-\s]{7,}\d(?!\w)"
)

_IPV6_RE = re.compile(
    r"(?<![:.\w])(?:"
    r"(?:[0-9A-Fa-f]{1,4}:){7}[0-9A-Fa-f]{1,4}"
    r"|(?:[0-9A-Fa-f]{1,4}:){1,7}:"
    r"|(?:[0-9A-Fa-f]{1,4}:){1,6}:[0-9A-Fa-f]{1,4}"
    r"|(?:[0-9A-Fa-f]{1,4}:){1,5}(?::[0-9A-Fa-f]{1,4}){1,2}"
    r"|(?:[0-9A-Fa-f]{1,4}:){1,4}(?::[0-9A-Fa-f]{1,4}){1,3}"
    r"|(?:[0-9A-Fa-f]{1,4}:){1,3}(?::[0-9A-Fa-f]{1,4}){1,4}"
    r"|(?:[0-9A-Fa-f]{1,4}:){1,2}(?::[0-9A-Fa-f]{1,4}){1,5}"
    r"|[0-9A-Fa-f]{1,4}:(?::[0-9A-Fa-f]{1,4}){1,6}"
    r"|::(?:[0-9A-Fa-f]{1,4}:){0,6}[0-9A-Fa-f]{1,4}"
    r")(?![:.\w])"
)

# China-specific identifiers. Until 2026-09-04 there were none, and the three
# most common ones were caught only by accident: an ID card, a bank card and a
# mainland mobile number are all long digit runs, so _PHONE_RE swallowed them
# and reported every one as a PHONE. Coverage was real; the label was wrong,
# which makes a privacy report describe something that did not happen. A
# passport number fell through entirely -- eight digits, one short of _PHONE_RE.
#
# These must stay ahead of _PHONE_RE in _BASE_PATTERNS: patterns are applied in
# order and the first to match owns the span, so the generic rule has to run
# last or it takes the specific ones' matches and mislabels them again.
_ID_CARD_CN_RE = re.compile(r"(?<!\d)[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)")
# The boundary is non-alphanumeric, not merely non-digit. `(?!\d)` is satisfied by
# a letter, so this rule took the seventeen leading digits out of a credit code
# ending in its checksum letter (91110108551385095Q) and reported a bank card.
_BANK_CARD_RE = re.compile(r"(?<![A-Za-z0-9])\d{16,19}(?![A-Za-z0-9])")
_MOBILE_CN_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
# A letter plus eight digits is also the shape of an ordinary date-coded document
# id -- E20260904, H20250101 -- and an adversarial pass found exactly that, so the
# eight digits must not read as a date. The trade is deliberate and one-sided: a
# passport number whose digits happen to spell a recent calendar date is rare, and
# redacting every document reference of that shape corrupts text the model has to
# reason about.
# python:S5843 measures this at 24 against 20 allowed. Splitting the date
# exclusion out of the lookahead would mean matching a bare `[EGDSPH]\d{8}`
# candidate here and rejecting date-shaped ones with a second, kind-specific
# check -- but every pattern in _BASE_PATTERNS is walked by one generic loop
# (`_active_patterns` / `redact_sensitive_text` below), and a passport-only
# postfilter bolted onto that loop is a second, quieter definition of what
# "this kind matched" means, in the one file where getting that wrong means a
# real passport number reaches an external provider. Left as measured.
_PASSPORT_CN_RE = re.compile(
    r"(?<![A-Za-z0-9])[EGDSPH](?!(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])(?![A-Za-z0-9]))\d{8}(?![A-Za-z0-9])"  # NOSONAR
)
# Unified social credit code: 18 characters from a checksum alphabet that omits
# I, O, Z, S and V, with the six-digit administrative division in the middle.
_USCC_RE = re.compile(r"(?<![A-Za-z0-9])[0-9A-HJ-NPQRTUWXY]{2}\d{6}[0-9A-HJ-NPQRTUWXY]{10}(?![A-Za-z0-9])")

_BASE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("SECRET", _SECRET_PATTERNS[2]),
    ("SECRET", _SECRET_PATTERNS[1]),
    ("SECRET", _SECRET_PATTERNS[0]),
    ("URL", _URL_RE),
    ("EMAIL", _EMAIL_RE),
    ("IP", _IPV4_RE),
    ("IP", _IPV6_RE),
    ("UUID", _UUID_RE),
    ("PATH", _WINDOWS_PATH_RE),
    ("PATH", _UNIX_PATH_RE),
    ("ID_CARD_CN", _ID_CARD_CN_RE),
    # BANK_CARD ahead of USCC_CN: the credit-code alphabet includes digits, so an
    # 18-digit order number matched USCC first and was reported as a company
    # registration. A real credit code carries letters in its organization part
    # and so is not touched by the digits-only rule above it.
    ("BANK_CARD", _BANK_CARD_RE),
    ("USCC_CN", _USCC_RE),
    ("MOBILE_CN", _MOBILE_CN_RE),
    ("PASSPORT_CN", _PASSPORT_CN_RE),
    ("PHONE", _PHONE_RE),
]


@dataclass
class _RedactionState:
    counters: dict[str, int] = field(default_factory=dict)
    replacements: dict[str, int] = field(default_factory=dict)
    seen: dict[tuple[str, str], str] = field(default_factory=dict)
    # token -> the value AS WRITTEN, for restoring a reply. `seen` is keyed on
    # the normalized form (URLs and emails are lower-cased so the same address in
    # two casings gets one token), and restoring from that key would hand the
    # reader `https://example.com/path` where the document said
    # `https://Example.com/Path` -- a URL path is case-sensitive.
    originals: dict[str, str] = field(default_factory=dict)

    def token_for(self, kind: str, raw: str) -> str:
        value = str(raw or "").strip()
        if not value:
            return value
        self.replacements[kind] = int(self.replacements.get(kind, 0)) + 1
        key = (kind, _normalize_seen_value(kind, value))
        existing = self.seen.get(key)
        if existing:
            return existing
        next_index = int(self.counters.get(kind, 0)) + 1
        self.counters[kind] = next_index
        token = f"<{kind}_{next_index}>"
        self.seen[key] = token
        self.originals[token] = value
        return token


def is_external_provider(provider: str) -> bool:
    return normalize_string(provider, lowercase=True) in EXTERNAL_PROVIDERS


def _normalize_seen_value(kind: str, value: str) -> str:
    normalized = str(value or "").strip()
    if kind in {"EMAIL", "URL", "IP", "UUID"}:
        return normalize_string(normalized, lowercase=True)
    return normalized


def outbound_redaction_enabled(*, for_embeddings: bool = False) -> bool:
    settings = get_settings()
    if for_embeddings:
        return bool(getattr(settings, "outbound_embedding_redaction_enabled", True))
    return bool(getattr(settings, "outbound_llm_redaction_enabled", True))


def _split_custom_entries(raw: str) -> list[str]:
    return [item.strip() for item in re.split(r"[\r\n,;]+", str(raw or "")) if item.strip()]


@lru_cache(maxsize=16)
def _custom_patterns(custom_terms: str, custom_regexes: str) -> tuple[tuple[str, re.Pattern[str]], ...]:
    patterns: list[tuple[str, re.Pattern[str]]] = []
    for term in sorted(_split_custom_entries(custom_terms), key=len, reverse=True):
        patterns.append(("CUSTOM", re.compile(re.escape(term), flags=re.IGNORECASE)))
    for expr in _split_custom_entries(custom_regexes):
        try:
            patterns.append(("CUSTOM", re.compile(expr, flags=re.IGNORECASE)))
        except re.error:
            logger.warning("Ignoring invalid outbound redaction regex: %s", expr[:120])
            continue
    return tuple(patterns)


def _active_patterns() -> tuple[tuple[str, re.Pattern[str]], ...]:
    settings = get_settings()
    return tuple(_BASE_PATTERNS) + _custom_patterns(
        str(getattr(settings, "outbound_redaction_custom_terms", "") or ""),
        str(getattr(settings, "outbound_redaction_custom_regexes", "") or ""),
    )


def _redact_text_with_state(
    text: str,
    state: _RedactionState,
    *,
    allowed_kinds: frozenset[str] | None = None,
) -> str:
    sanitized = str(text or "")
    for kind, pattern in _active_patterns():
        if allowed_kinds is not None and kind not in allowed_kinds:
            continue
        sanitized = pattern.sub(lambda m, k=kind: state.token_for(k, m.group(0)), sanitized)
    return sanitized


def redact_sensitive_text(
    text: str,
    *,
    allowed_kinds: frozenset[str] | None = None,
) -> tuple[str, dict[str, int]]:
    """Redact text deterministically and return safe aggregate counts.

    This provider-neutral entry point lets input, context, and output privacy
    services reuse the exact same patterns and stable tokenization as outbound
    provider redaction without exposing matched sensitive values.
    """

    state = _RedactionState()
    sanitized = _redact_text_with_state(str(text or ""), state, allowed_kinds=allowed_kinds)
    return sanitized, dict(sorted(state.replacements.items()))


def _should_passthrough_string(parent_key: str, value: str) -> bool:
    key = normalize_string(parent_key, lowercase=True)
    text = str(value or "")
    if not key:
        return False
    if key in _STRUCTURAL_STRING_KEYS:
        return True
    if key in _BINARY_PAYLOAD_KEYS:
        return True
    if key == "url" and text.startswith("data:"):
        return True
    return False


def redact_texts_for_provider(texts: list[str], *, provider: str, for_embeddings: bool = False) -> list[str]:
    values = [str(item or "") for item in texts or []]
    if not is_external_provider(provider) or not outbound_redaction_enabled(for_embeddings=for_embeddings):
        return values
    state = _RedactionState()
    return [_redact_text_with_state(item, state) for item in values]


def _redact_dict_fields(item: dict, state: _RedactionState) -> dict:
    rebuilt = dict(item)
    for field_name, field_value in list(rebuilt.items()):
        rebuilt[field_name] = _redact_message_item(field_value, state, parent_key=str(field_name))
    return rebuilt


def _redact_message_item(item: Any, state: _RedactionState, *, parent_key: str = ""):
    if isinstance(item, str):
        if _should_passthrough_string(parent_key, item):
            return item
        return _redact_text_with_state(item, state)
    if isinstance(item, tuple):
        if len(item) < 2:
            return item
        rebuilt = list(item)
        rebuilt[1] = _redact_message_item(rebuilt[1], state, parent_key="content")
        return tuple(rebuilt)
    if isinstance(item, list):
        return [_redact_message_item(value, state, parent_key=parent_key) for value in item]
    if isinstance(item, dict):
        # A message dict and a plain nested dict take the identical path --
        # both walk every field and redact it under its own key -- so there is
        # only one branch to fall into here, not two.
        return _redact_dict_fields(item, state)
    return item


def _apply(messages: Any, state: _RedactionState):
    if isinstance(messages, str):
        return _redact_text_with_state(messages, state)
    if isinstance(messages, tuple | dict):
        return _redact_message_item(messages, state, parent_key="content")
    if isinstance(messages, list):
        return [_redact_message_item(item, state, parent_key="content") for item in messages]
    return messages


def redact_messages_for_provider(messages: Any, *, provider: str):
    if not is_external_provider(provider) or not outbound_redaction_enabled():
        return messages
    return _apply(messages, _RedactionState())


def redact_messages_with_restorer(messages: Any, *, provider: str) -> tuple[Any, Callable[[str], str]]:
    """Redact outbound content, and hand back the way to undo it on the reply.

    The model is shown `<URL_7>` and **writes it back**. Observed in a real
    answer: a reference line reading `[1] <URL_7>`, a token that means nothing to
    a reader, one paragraph above the pipeline's own list showing the real link.

    Redaction exists to keep a value from the *provider*, not from the person who
    asked -- it is their own document. So the reply is restored.

    **The mapping never leaves this call.** It is built here, closed over by the
    returned function, and dropped when the caller lets go of it. A per-request
    ContextVar or a module-level map would work too and would risk the one
    failure that actually matters: one user's values appearing in another's
    answer. A cosmetic token is worth far less than that.

    Restoration is longest-token-first, so `<URL_1>` cannot eat the prefix of
    `<URL_11>`.
    """

    if not is_external_provider(provider) or not outbound_redaction_enabled():
        return messages, lambda text: text

    state = _RedactionState()
    payload = _apply(messages, state)
    originals = dict(state.originals)

    def restore(text: str) -> str:
        out = str(text or "")
        if not out or not originals:
            return out
        for token in sorted(originals, key=len, reverse=True):
            if token in out:
                out = out.replace(token, originals[token])
        return out

    return payload, restore
