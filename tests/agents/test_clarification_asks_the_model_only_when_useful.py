"""A question the rules find complete does not cost a model call before its answer.

The rules answer "complete" for anything they do not recognise, and the service
then asked the model on every such question -- one serial model call ahead of
every answer, "is log4j 2.14.1 affected?" included. The model is asked on a
first round only when there may be constraints to collect: a question too
short to say what it is about, or an open-ended task.
"""

from __future__ import annotations

import pytest

from app.agents.clarification import service as clarification_service
from app.agents.clarification.service import ClarificationAgentService
from app.orchestration.request import OrchestrationRequest


class _CountingModel:
    calls = 0

    def invoke(self, messages):
        type(self).calls += 1
        return type("R", (), {"content": '{"needs_clarification": false}'})()


@pytest.fixture
def model(monkeypatch):
    _CountingModel.calls = 0
    monkeypatch.setattr(clarification_service, "get_chat_model", lambda *a, **k: _CountingModel())
    return _CountingModel


@pytest.mark.parametrize(
    "question",
    [
        "我们用的 log4j 2.14.1 受影响吗？CVE-2021-44228 怎么处置？",
        "70B 模型 FP16 推理需要多少显存？",
        "我们的数据保留制度符合个保法吗？",
        "Which regions had the highest Q3 sales in my table?",
    ],
)
def test_a_specific_question_is_not_sent_to_the_model(model, question: str) -> None:
    result = ClarificationAgentService().clarify(OrchestrationRequest(question=question))

    assert model.calls == 0
    assert result.action == "continue"


@pytest.mark.parametrize(
    "question",
    [
        "这个怎么弄？",
        "How do I fix it?",
        "帮我规划一个高并发微服务系统方案",
        "Help me build a scalable cloud infrastructure",
    ],
)
def test_a_short_question_or_an_open_task_still_is(model, question: str) -> None:
    ClarificationAgentService().clarify(OrchestrationRequest(question=question))

    assert model.calls == 1
