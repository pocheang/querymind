"""The offline backend decides clarification from the question, not from its own prompt.

`LocalEvidenceChatModel._clarification_json` scanned the whole prompt for
设计 / 选型 / 方案 / 架构, and the clarification prompt's instructions contain
all four -- so on the backend a fresh checkout runs, every question was asked
which tech stack it planned to use, including "is log4j 2.14.1 affected?".
"""

from __future__ import annotations

import json

import pytest

from app.agents.clarification.prompts import build_clarification_prompt
from app.services.models.runtime import LocalEvidenceChatModel


def _verdict(question: str, language: str = "zh") -> dict:
    prompt = build_clarification_prompt(question=question, collected_info={}, asked_questions=[], language=language)
    return json.loads(LocalEvidenceChatModel().invoke([("system", prompt)]).content)


@pytest.mark.parametrize(
    "question",
    [
        "我们用的 log4j 2.14.1 受影响吗？CVE-2021-44228 怎么处置？",
        "70B 模型 FP16 推理需要多少显存？",
        "我们的数据保留制度符合个保法吗？",
    ],
)
def test_a_specific_question_is_not_asked_to_clarify(question: str) -> None:
    assert _verdict(question)["needs_clarification"] is False


def test_the_prompt_itself_still_carries_the_words_that_used_to_trigger_it() -> None:
    # Without this, the tests above would pass the day the prompt stopped
    # containing those words, whatever the model does.
    prompt = build_clarification_prompt(question="x", collected_info={}, asked_questions=[], language="zh")
    assert any(word in prompt for word in ("设计", "选型", "方案", "架构"))


def test_a_design_question_is_still_asked_about_its_architecture() -> None:
    assert _verdict("帮我设计一个企业知识库的架构")["needs_clarification"] is True


def test_the_reply_follows_the_prompt_language() -> None:
    assert _verdict("Please design an architecture for our knowledge base", language="en")["question"].startswith(
        "What architecture"
    )
