"""Domain classification matches keywords as words, and the LLM is not bypassed.

Two defects, one symptom: ordinary questions were routed to a domain specialist.

- All three keyword classifiers -- the domain registry, `classify_agent_class`
  and the fallback behind the LLM intent classifier -- tested `keyword in text`,
  so `"ai"` matched "email", `"rag"` "storage", `"soc"` "social", `"log"`
  "blog". Measured before the fix, each of the first three was routed to a
  specialist.
- `routing._classify` consulted the registry *before* the LLM classifier and
  returned its hit at 0.95, so the LLM only ran when no keyword had matched and
  could never correct one that had.
"""

from __future__ import annotations

import pytest

from app.agents.registry import DomainAgentRegistry
from app.agents.router import routing
from app.services.agent_classifier import classify_agent_class
from app.services.models.runtime import LocalEvidenceChatModel
from app.services.query import intent_classifier
from app.services.query.intent_classifier import _fallback_classification
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
def test_the_llm_fallback_does_not_claim_an_ordinary_question(question: str):
    # `ips`, `log`, `read`, `ids`, `gan` -- all substrings of these sentences.
    assert _fallback_classification(question)["agent_class"] == "general"


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


def _llm_says(agent_class: str, confidence: float = 0.8):
    def classify(question: str) -> dict:
        del question
        return {"agent_class": agent_class, "confidence": confidence, "method": "llm"}

    return classify


def test_a_keyword_hit_does_not_bypass_the_llm_classifier(monkeypatch: pytest.MonkeyPatch):
    # "勒索" is a registry keyword. Before the fix the registry answered at 0.95
    # and the LLM was never asked.
    monkeypatch.setattr(routing, "classify_intent_with_llm", _llm_says("general", 0.9))

    agent_class, confidence, method = routing._classify("如何防护勒索病毒", None, use_llm_intent=True)

    assert (agent_class, confidence) == ("general", 0.9)
    assert method.startswith("llm")


def test_the_registry_still_decides_when_the_llm_is_not_used():
    agent_class, _, method = routing._classify("如何防护勒索病毒", None, use_llm_intent=False)

    assert agent_class == "cybersecurity"
    assert method == "rule_based"


def test_the_registry_still_decides_when_the_llm_classifier_raises(monkeypatch: pytest.MonkeyPatch):
    def broken(question: str) -> dict:
        raise RuntimeError("provider down")

    monkeypatch.setattr(routing, "classify_intent_with_llm", broken)

    agent_class, _, method = routing._classify("如何防护勒索病毒", None, use_llm_intent=True)

    assert (agent_class, method) == ("cybersecurity", "rule_fallback")


def test_the_offline_backend_still_reaches_the_specialists(monkeypatch: pytest.MonkeyPatch):
    """Removing the short-circuit must not switch the specialists off offline.

    `MODEL_BACKEND=local` is what a fresh checkout runs. Its model answers the
    intent prompt with no JSON, so the classifier falls back to the registry --
    driven here through the real `LocalEvidenceChatModel`, not a fake that
    answers whatever it is asked.
    """

    monkeypatch.setattr(intent_classifier, "get_chat_model", lambda **_: LocalEvidenceChatModel())

    agent_class, _, _ = routing._classify("如何防护勒索病毒", None, use_llm_intent=True)

    # Only the class is asserted. `_classify` labels this `llm(...)` although the
    # classifier fell back to the registry -- a pre-existing mislabel, not pinned.
    assert agent_class == "cybersecurity"
