"""What decide_route decides, pinned before it was split up.

It was one 130-line function: smalltalk, intent classification with two
fallbacks, keyword skill selection, an LLM call, validation of everything that
call returned, a configurable web downgrade, a low-confidence recovery path with
its own fallback, and calibration. The tests it had were about its cache.

The route is an instruction the rest of the pipeline follows -- it decides which
retrievers run and which answer shape the synthesizer is given -- so what this
function does with a malformed or unconfident answer from the model is worth
stating.
"""

from __future__ import annotations

import json

import pytest

from app.agents.router import routing
from app.agents.shared.cache import clear_router_decision_cache


class _Reply:
    def __init__(self, content: str) -> None:
        self.content = content


class _Model:
    def __init__(self, payload) -> None:
        self._payload = payload
        self.prompts: list[str] = []

    def invoke(self, prompt: str) -> _Reply:
        self.prompts.append(prompt)
        if isinstance(self._payload, Exception):
            raise self._payload
        return _Reply(json.dumps(self._payload) if not isinstance(self._payload, str) else self._payload)


@pytest.fixture(autouse=True)
def _router_wiring(monkeypatch: pytest.MonkeyPatch):
    """No cache between tests, no calibrator, and no real model or classifier."""

    clear_router_decision_cache()
    monkeypatch.setattr(routing, "_get_calibrator", lambda: None)
    # The keyword rules' suggestion; the model's answer is what each test sets.
    monkeypatch.setattr(routing, "classify_agent_class", lambda question: "general")
    monkeypatch.setattr(routing, "get_settings", lambda: type("S", (), {"enable_web_route_downgrade": False})())
    yield
    clear_router_decision_cache()


def _answer(monkeypatch: pytest.MonkeyPatch, payload) -> _Model:
    model = _Model(payload)
    monkeypatch.setattr(routing, "get_chat_model", lambda: model)
    monkeypatch.setattr(routing, "get_reasoning_model", lambda: model)
    return model


def test_smalltalk_never_reaches_the_model(monkeypatch: pytest.MonkeyPatch) -> None:
    model = _answer(monkeypatch, {"route": "graph"})

    decision = routing.decide_route("hello")

    assert decision.route == routing.ROUTE_VECTOR
    assert decision.skill == routing.SKILL_DEFAULT
    assert decision.confidence == pytest.approx(0.95)
    assert model.prompts == []


def test_the_model_decides_the_route_and_may_change_the_skill(monkeypatch: pytest.MonkeyPatch) -> None:
    _answer(monkeypatch, {"route": "graph", "reason": "entities", "skill": "timeline_builder", "confidence": 0.9})

    decision = routing.decide_route("how do the services depend on each other")

    assert decision.route == "graph"
    assert decision.skill == "timeline_builder"
    assert decision.reason == "entities"
    assert decision.confidence == pytest.approx(0.9)


def test_a_route_the_model_invented_falls_back_to_vector_and_says_so(monkeypatch: pytest.MonkeyPatch) -> None:
    _answer(monkeypatch, {"route": "telepathy", "reason": "guessing", "confidence": 0.9})

    decision = routing.decide_route("what does the report say about costs")

    assert decision.route == routing.ROUTE_VECTOR
    assert "invalid_route=telepathy" in decision.reason


def test_a_skill_the_model_invented_keeps_the_one_already_chosen(monkeypatch: pytest.MonkeyPatch) -> None:
    _answer(monkeypatch, {"route": "vector", "reason": "ok", "skill": "astrology", "confidence": 0.9})

    decision = routing.decide_route("compare the two vendors on price")

    assert decision.skill == "compare_entities"  # from the question, not from the model
    assert "invalid_skill=astrology" in decision.reason


@pytest.mark.parametrize(
    ("question", "expected_skill"),
    [
        ("compare the two vendors on price", "compare_entities"),
        ("what is the difference between them", "compare_entities"),
        ("give me the timeline of the incident", "timeline_builder"),
        ("what is the history of this project", "timeline_builder"),
        ("what does the document say about revenue", "answer_with_citations"),
    ],
)
def test_the_question_picks_a_skill_before_the_model_is_asked(
    monkeypatch: pytest.MonkeyPatch, question: str, expected_skill: str
) -> None:
    _answer(monkeypatch, {"route": "vector", "reason": "ok", "confidence": 0.9})

    assert routing.decide_route(question).skill == expected_skill


def test_a_forced_agent_class_wins_and_is_recorded(monkeypatch: pytest.MonkeyPatch) -> None:
    _answer(monkeypatch, {"route": "vector", "reason": "ok", "confidence": 0.9})

    decision = routing.decide_route("what does the report say", agent_class_hint="cybersecurity")

    assert decision.agent_class == "cybersecurity"
    assert "forced_agent_class=cybersecurity" in decision.reason


def test_the_web_route_survives_when_the_downgrade_is_off(monkeypatch: pytest.MonkeyPatch) -> None:
    _answer(monkeypatch, {"route": "web", "reason": "needs fresh data", "confidence": 0.9})

    assert routing.decide_route("what happened in the news today about this").route == "web"


def test_the_web_route_is_rewritten_when_the_downgrade_is_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """A third answer to "who authorised the web", and an invisible one."""

    _answer(monkeypatch, {"route": "web", "reason": "needs fresh data", "confidence": 0.9})
    monkeypatch.setattr(routing, "get_settings", lambda: type("S", (), {"enable_web_route_downgrade": True})())

    decision = routing.decide_route("what happened in the news today about this")

    assert decision.route == routing.ROUTE_VECTOR
    assert "web_downgraded_to_local_first" in decision.reason


@pytest.mark.parametrize(
    ("stated", "expected"),
    # Only values that clear the low-confidence threshold: below it the recovery
    # path takes over and the clamp is no longer what is being read.
    [(1.7, 1.0), (None, 0.7), ("high", 0.7)],
)
def test_the_models_confidence_is_clamped_or_defaulted(
    monkeypatch: pytest.MonkeyPatch, stated, expected: float
) -> None:
    payload = {"route": "vector", "reason": "ok"}
    if stated is not None:
        payload["confidence"] = stated
    _answer(monkeypatch, payload)

    decision = routing.decide_route(f"what does the report say about item {stated}")

    assert decision.raw_confidence == pytest.approx(expected)


def test_low_confidence_takes_the_reasoning_model_when_it_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    _answer(monkeypatch, {"route": "vector", "reason": "unsure", "confidence": 0.1})
    monkeypatch.setattr(routing, "_try_fallback_with_reasoning", lambda *args: ("graph", "reasoned_again", 0.85))

    decision = routing.decide_route("something the router is unsure about")

    assert (decision.route, decision.reason) == ("graph", "reasoned_again")
    assert decision.raw_confidence == pytest.approx(0.85)


def test_low_confidence_falls_back_to_the_safe_route_and_keeps_saying_it_is_unsure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _answer(monkeypatch, {"route": "graph", "reason": "unsure", "confidence": 0.1})
    monkeypatch.setattr(routing, "_try_fallback_with_reasoning", lambda *args: None)

    decision = routing.decide_route("something else the router is unsure about")

    assert decision.route == routing.ROUTE_VECTOR
    assert "fallback_safe_route" in decision.reason
    # Floored at 0.5 rather than raised to it: the uncertainty is the message.
    assert decision.raw_confidence == pytest.approx(0.5)


def test_a_model_that_raises_still_returns_a_usable_decision(monkeypatch: pytest.MonkeyPatch) -> None:
    _answer(monkeypatch, RuntimeError("provider timeout"))

    decision = routing.decide_route("compare the two vendors on price and support")

    assert decision.route == routing.ROUTE_VECTOR
    assert "router_invoke_error:RuntimeError" in decision.reason
    assert decision.raw_confidence == pytest.approx(0.5)
    # The skill chosen before the call survives it.
    assert decision.skill == "compare_entities"


def test_a_model_that_names_no_agent_class_keeps_the_rules_choice(monkeypatch: pytest.MonkeyPatch) -> None:
    _answer(monkeypatch, {"route": "vector", "reason": "ok", "confidence": 0.9})
    monkeypatch.setattr(routing, "classify_agent_class", lambda question: "pdf_text")

    decision = routing.decide_route("what does page four of the manual say")

    assert decision.agent_class == "pdf_text"
    assert decision.skill == "pdf_text_reader"


@pytest.mark.parametrize("invented", ["finance_bot", "", 42])
def test_an_agent_class_the_model_invented_keeps_the_rules_choice(monkeypatch: pytest.MonkeyPatch, invented) -> None:
    _answer(monkeypatch, {"route": "vector", "agent_class": invented, "reason": "ok", "confidence": 0.9})
    monkeypatch.setattr(routing, "classify_agent_class", lambda question: "pdf_text")

    assert routing.decide_route("what does page four of the manual say").agent_class == "pdf_text"


# --- one call decides the route and who answers --------------------------------
#
# Intent classification used to be a model call of its own ahead of the route
# call. Measured on the configured model the two took 8.3-12.4s against an 8s
# ceiling, on every one of eight questions, so the route stage always timed out.


def test_one_model_call_decides_the_route_and_the_agent_class(monkeypatch: pytest.MonkeyPatch) -> None:
    model = _answer(monkeypatch, {"route": "hybrid", "agent_class": "cybersecurity", "reason": "ok", "confidence": 0.9})

    decision = routing.decide_route("how do we harden the exposed service")

    assert len(model.prompts) == 1
    assert decision.route == "hybrid"
    assert decision.agent_class == "cybersecurity"


def test_the_model_outranks_the_keyword_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    """A keyword hit once returned ahead of the model, and one was "ai" in "email"."""

    _answer(monkeypatch, {"route": "vector", "agent_class": "general", "reason": "ok", "confidence": 0.9})
    monkeypatch.setattr(routing, "classify_agent_class", lambda question: "artificial_intelligence")

    assert routing.decide_route("please forward this email to the team").agent_class == "general"


def test_a_moved_question_gets_a_skill_for_its_new_specialist(monkeypatch: pytest.MonkeyPatch) -> None:
    """The suggested skill belonged to the rules' class; kept unchanged by the
    model, it is suggested again for the class the model chose."""

    _answer(monkeypatch, {"route": "vector", "agent_class": "cybersecurity", "reason": "ok", "confidence": 0.9})

    decision = routing.decide_route("CVE-2021-44228 应急处置步骤")

    assert decision.agent_class == "cybersecurity"
    assert decision.skill == "cybersecurity_incident_response"


def test_a_skill_the_model_chose_survives_a_change_of_class(monkeypatch: pytest.MonkeyPatch) -> None:
    _answer(
        monkeypatch,
        {
            "route": "vector",
            "agent_class": "cybersecurity",
            "skill": "timeline_builder",
            "reason": "ok",
            "confidence": 0.9,
        },
    )

    assert routing.decide_route("when did the breach unfold").skill == "timeline_builder"


def test_a_forced_class_is_shown_as_fixed_and_not_overridden(monkeypatch: pytest.MonkeyPatch) -> None:
    model = _answer(
        monkeypatch, {"route": "vector", "agent_class": "artificial_intelligence", "reason": "ok", "confidence": 0.9}
    )

    decision = routing.decide_route("what does the report say", agent_class_hint="cybersecurity")

    assert decision.agent_class == "cybersecurity"
    assert "fixed by the user" in model.prompts[0]


def test_without_llm_intent_the_rules_decide(monkeypatch: pytest.MonkeyPatch) -> None:
    _answer(monkeypatch, {"route": "vector", "agent_class": "cybersecurity", "reason": "ok", "confidence": 0.9})
    monkeypatch.setattr(routing, "classify_agent_class", lambda question: "pdf_text")

    assert routing.decide_route("what does page four say", use_llm_intent=False).agent_class == "pdf_text"


def test_the_prompt_describes_every_agent_class_and_asks_for_one() -> None:
    assert '"agent_class"' in routing.ROUTER_PROMPT
    assert "1. cybersecurity" in routing.ROUTER_PROMPT


def test_calibration_replaces_the_reported_confidence_but_not_the_raw_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """raw_confidence exists to feed the calibrator without training it on itself."""

    _answer(monkeypatch, {"route": "vector", "reason": "ok", "confidence": 0.8})
    monkeypatch.setattr(
        routing, "_get_calibrator", lambda: type("C", (), {"calibrate": staticmethod(lambda v: 0.42)})()
    )

    decision = routing.decide_route("what does the summary say about margins")

    assert decision.confidence == pytest.approx(0.42)
    assert decision.raw_confidence == pytest.approx(0.8)


def test_a_negative_confidence_is_clamped_to_zero_before_the_recovery_sees_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The clamp runs first, so the recovery path is never handed a nonsense number."""

    _answer(monkeypatch, {"route": "vector", "reason": "ok", "confidence": -0.4})
    seen: list[float] = []

    def record(question, agent_class, skill, confidence):
        seen.append(confidence)
        return None

    monkeypatch.setattr(routing, "_try_fallback_with_reasoning", record)

    routing.decide_route("a question the model is very unsure about")

    assert seen == [0.0]
