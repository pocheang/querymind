"""Domain classification matches keywords as words, and the LLM is not bypassed.

Two defects, one symptom: ordinary questions were routed to a domain specialist.

- All three keyword classifiers -- the domain registry, `classify_agent_class`
  and the fallback behind the LLM intent classifier (deleted since, with the
  classifier: one routing call now decides the class) -- tested `keyword in text`,
  so `"ai"` matched "email", `"rag"` "storage", `"soc"` "social", `"log"`
  "blog". Measured before the fix, each of the first three was routed to a
  specialist.
- The router consulted the registry *before* the LLM classifier and returned
  its hit at 0.95, so the LLM only ran when no keyword had matched and could
  never correct one that had. The keyword rules are now only a suggestion in
  the one routing call, and the model's answer outranks them.
"""

from __future__ import annotations

import pytest

from app.agents.registry import DomainAgentRegistry
from app.agents.router import routing
from app.agents.shared.cache import clear_router_decision_cache
from app.services.agent_classifier import classify_agent_class
from app.services.models.runtime import LocalEvidenceChatModel
from app.services.query.keyword_match import contains_keyword

# --- the matcher -------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "keyword"),
    [
        ("please email me", "ai"),
        ("the maintenance window", "ai"),
        ("object storage for the average user", "rag"),
        ("our social media policy", "soc"),
        ("an ec2 instance", "c2"),
        ("read the blog post", "log"),
        ("some tips for onboarding", "ips"),
        ("the kids' schedule", "ids"),
        ("i have already signed", "read"),
    ],
)
def test_a_latin_keyword_inside_a_word_does_not_match(text: str, keyword: str):
    assert not contains_keyword(text, keyword)


@pytest.mark.parametrize(
    ("text", "keyword"),
    [
        ("what is ai?", "ai"),
        ("AI 安全治理", "ai"),
        # `\b` would miss both of these: to Python a CJK character is a word
        # character, so there is no boundary between it and a Latin letter.
        ("用ai做客服", "ai"),
        ("这份pdf里写了什么", "pdf"),
        ("rag 系统怎么评测", "rag"),
        ("SOC 告警太多", "soc"),
        ("att&ck 矩阵", "att&ck"),
        ("kv cache 占多少显存", "kv cache"),
    ],
)
def test_a_latin_keyword_as_a_word_matches(text: str, keyword: str):
    assert contains_keyword(text, keyword)


def test_a_chinese_keyword_still_matches_as_a_substring():
    # Chinese has no word boundaries to require.
    assert contains_keyword("如何防御sql注入攻击", "sql注入")
    assert contains_keyword("这是一次勒索软件事件", "勒索")


# --- the three classifiers -----------------------------------------------------

FALSE_POSITIVES = [
    "Please email me the maintenance schedule",
    "How do I set up storage for the average user?",
    "What is our social media plan for next quarter?",
]


@pytest.mark.parametrize("question", FALSE_POSITIVES)
def test_the_registry_does_not_claim_an_ordinary_question(question: str):
    assert DomainAgentRegistry().match_agent_class(question) is None


@pytest.mark.parametrize("question", FALSE_POSITIVES)
def test_the_rule_classifier_does_not_claim_an_ordinary_question(question: str):
    assert classify_agent_class(question) == "general"


@pytest.mark.parametrize(
    "question",
    [
        "Any tips for writing a blog post?",
        "I have already signed the onboarding form",
        "The kids' club began in spring",
    ],
)
def test_the_rules_do_not_claim_these_either(question: str):
    # `ips`, `log`, `read`, `ids`, `gan` -- all substrings of these sentences.
    # They were written for the LLM classifier's own keyword fallback, deleted
    # with the classifier; the rules that remain must pass them too.
    assert classify_agent_class(question) == "general"


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("我们被 Log4Shell 打了吗？", "cybersecurity"),
        ("如何防护勒索病毒", "cybersecurity"),
        ("大模型的 kv cache 占多少显存", "artificial_intelligence"),
        ("RAG 系统怎么评测", "artificial_intelligence"),
    ],
)
def test_a_domain_question_is_still_recognised(question: str, expected: str):
    # The fix narrows what a keyword matches; it must not stop real ones.
    assert DomainAgentRegistry().match_agent_class(question) == expected
    assert classify_agent_class(question) == expected


def test_the_pdf_rule_now_sees_pdf_written_against_chinese():
    # `\bpdf\b` missed this, so it was never classified pdf_text.
    assert classify_agent_class("帮我读取这份pdf的内容") == "pdf_text"


# --- the router does not bypass the LLM --------------------------------------


class _RouteModel:
    """Answers the one routing call with a fixed JSON reply."""

    def __init__(self, reply: str | Exception) -> None:
        self._reply = reply

    def invoke(self, prompt):
        del prompt
        if isinstance(self._reply, Exception):
            raise self._reply
        return type("R", (), {"content": self._reply})()


@pytest.fixture
def route_model(monkeypatch: pytest.MonkeyPatch):
    clear_router_decision_cache()
    monkeypatch.setattr(routing, "_get_calibrator", lambda: None)

    def use(reply):
        monkeypatch.setattr(routing, "get_chat_model", lambda **_: _RouteModel(reply))

    yield use
    clear_router_decision_cache()


def test_a_keyword_hit_does_not_bypass_the_model(route_model):
    # "勒索" is a registry keyword. Before the fix the registry answered at 0.95
    # and the model was never asked.
    route_model('{"route": "vector", "agent_class": "general", "reason": "ok", "confidence": 0.9}')
    assert routing.decide_route("如何防护勒索病毒").agent_class == "general"


def test_the_registry_still_decides_when_the_llm_is_not_used(route_model):
    route_model('{"route": "vector", "agent_class": "general", "reason": "ok", "confidence": 0.9}')
    assert routing.decide_route("如何防护勒索病毒", use_llm_intent=False).agent_class == "cybersecurity"


def test_the_registry_still_decides_when_the_model_raises(route_model):
    route_model(RuntimeError("provider down"))
    assert routing.decide_route("如何防护勒索病毒").agent_class == "cybersecurity"


def test_the_offline_backend_still_reaches_the_specialists(monkeypatch: pytest.MonkeyPatch):
    """`MODEL_BACKEND=local` is what a fresh checkout runs. Its model answers
    the routing prompt without an agent class, so the keyword rules decide --
    driven here through the real `LocalEvidenceChatModel`, not a fake that
    answers whatever it is asked."""

    clear_router_decision_cache()
    monkeypatch.setattr(routing, "_get_calibrator", lambda: None)
    monkeypatch.setattr(routing, "get_chat_model", lambda **_: LocalEvidenceChatModel())
    try:
        assert routing.decide_route("如何防护勒索病毒").agent_class == "cybersecurity"
    finally:
        clear_router_decision_cache()
