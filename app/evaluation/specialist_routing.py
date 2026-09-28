"""Which specialist answers a question: a labelled set, and the offline rules measured against it.

"Router accuracy >95%" sat in the quality table with nothing behind it -- no
labelled routing set existed. `config/eval/specialist_routing.json` is that set.
Its labels say what a correct router should answer; they were never written to
match the rules, because a label copied from the implementation measures
nothing.

The rules are measured here offline and deterministically (no model): they are
what answers when the model router times out or is unavailable, so they carry
real traffic. Where they disagree with a label, `KNOWN_MISROUTES` records the
exact wrong answer, the same shape as `KNOWN_LEXICAL_LIMITS` in
`retrieval_eval.py` -- so a regression fails, and so does an improvement, which
means the entry should go. The model router is measured by
`scripts/eval_specialist_routing.py --llm`, a manual command: a CI runner has no
model, and a number describing a fallback is worse than none.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "KNOWN_MISROUTES",
    "RoutingCase",
    "RoutingReport",
    "evaluate",
    "load_cases",
    "rule_route",
]

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "config" / "eval" / "specialist_routing.json"

# Question id -> ((agent_class, skill) the offline rules return today, why).
# Each entry is a known gap, not an accepted answer. Measured 2026-09-28 (68 questions since the document specialist).
#
# The keyword-rule entries are deliberately left as they are rather than "fixed"
# by adding the missing words: a keyword added to pass one question here is
# tuned to the test set, and the set then stops measuring anything. A keyword
# list change needs its own justification and a counter-example in this set.
KNOWN_MISROUTES: dict[str, tuple[tuple[str, str], str]] = {
    # Keyword-rule limits.
    "sec-10": (
        ("general", "answer_with_citations"),
        "'incident response' and 'phishing' are not intent keywords; the model router is needed",
    ),
    "ai-10": (
        ("general", "answer_with_citations"),
        "'neural network' is only listed in Chinese (神经网络)",
    ),
    "data-01": (
        ("general", "answer_with_citations"),
        "'销售表' carries no data keyword: '表' alone is left out because it is inside 代表, 表示 and 发表",
    ),
    "data-06": (
        ("general", "answer_with_citations"),
        "'table' is not a data keyword: routing tables, hash tables and tables of contents are not data analysis",
    ),
    "pdf-07": (
        ("general", "answer_with_citations"),
        "no reading keyword: asking what chapter 3 of a document says is the model router's call",
    ),
    "pdf-08": (
        ("general", "answer_with_citations"),
        "no reading keyword: asking what section 4 of a document says is the model router's call",
    ),
    "comp-06": (
        ("general", "answer_with_citations"),
        "'PIPL' is not a keyword; the compliance specialist knows the law by its Chinese names",
    ),
    "edge-14": (
        ("compliance", "compliance_qa"),
        "'等保' is a compliance keyword and nothing in the rules reads 'how do I configure'",
    ),
    "edge-13": (
        ("general", "answer_with_citations"),
        "'泄露' is not a security keyword; the model router is needed",
    ),
    "edge-10": (
        ("cybersecurity", "cyber_attack_analysis"),
        "'高危漏洞' carries no assessment keyword, so pick_skill falls back to attack analysis",
    ),
    "edge-12": (
        ("artificial_intelligence", "ai_deep_dive"),
        "'投毒' is not a security keyword and '大模型' is an AI one",
    ),
    # The answer shape. A specialist's pick_skill answers before the wording
    # checks in _skill_for run, and neither specialist ever proposes a
    # comparison or hardening; the timeline check knows only the English word.
    "sec-05": (("cybersecurity", "cyber_attack_analysis"), "the security specialist has no hardening branch"),
    "edge-01": (("cybersecurity", "cyber_attack_analysis"), "the security specialist has no hardening branch"),
    "edge-02": (("cybersecurity", "cyber_attack_analysis"), "the security specialist has no hardening branch"),
    "sec-07": (("cybersecurity", "cyber_attack_analysis"), "a specialist never proposes a comparison"),
    "sec-09": (("cybersecurity", "cyber_attack_analysis"), "a specialist never proposes a comparison"),
    "ai-02": (("artificial_intelligence", "ai_deep_dive"), "a specialist never proposes a comparison"),
    "ai-03": (("artificial_intelligence", "ai_deep_dive"), "a specialist never proposes a comparison"),
    "ai-12": (("artificial_intelligence", "ai_deep_dive"), "a specialist never proposes a comparison"),
    "gen-06": (("general", "answer_with_citations"), "the timeline check matches 'timeline'/'history' only"),
}


@dataclass(frozen=True)
class RoutingCase:
    id: str
    question: str
    agent_class: str
    skill: str
    boundary: bool = False
    why: str = ""


@dataclass(frozen=True)
class RoutingOutcome:
    case: RoutingCase
    agent_class: str
    skill: str

    @property
    def class_correct(self) -> bool:
        return self.agent_class == self.case.agent_class

    @property
    def skill_correct(self) -> bool:
        """Compared as the answer shape the synthesizer receives, not as the raw name.

        The two router paths speak different vocabularies: the rules return a
        specialist's own skill (`cybersecurity_incident_response`), the model
        router a pipeline skill (`incident_response_playbook`), and the
        specialist maps one onto the other before synthesis
        (`pipeline_skill_for`). Compared raw, the first measurement of the model
        router scored most right answers wrong.
        """

        return answer_shape(self.agent_class, self.skill) == answer_shape(self.case.agent_class, self.case.skill)


@dataclass(frozen=True)
class RoutingReport:
    outcomes: tuple[RoutingOutcome, ...]
    per_class: dict[str, tuple[int, int]] = field(default_factory=dict)

    @property
    def class_accuracy(self) -> float:
        return sum(o.class_correct for o in self.outcomes) / len(self.outcomes) if self.outcomes else 0.0

    @property
    def skill_accuracy(self) -> float:
        """Skill is only scored where the class was right: a wrong specialist's skill means nothing."""

        routed = [o for o in self.outcomes if o.class_correct]
        return sum(o.skill_correct for o in routed) / len(routed) if routed else 0.0

    @property
    def confusion(self) -> Counter[tuple[str, str]]:
        """(expected, got) for every wrong class."""

        return Counter((o.case.agent_class, o.agent_class) for o in self.outcomes if not o.class_correct)

    def observed_misroutes(self) -> dict[str, tuple[str, str]]:
        return {o.case.id: (o.agent_class, o.skill) for o in self.outcomes if not (o.class_correct and o.skill_correct)}


def load_cases(path: Path | None = None) -> tuple[RoutingCase, ...]:
    payload = json.loads((path or DEFAULT_PATH).read_text(encoding="utf-8"))
    return tuple(
        RoutingCase(
            id=str(row["id"]),
            question=str(row["question"]),
            agent_class=str(row["agent_class"]),
            skill=str(row["skill"]),
            boundary=bool(row.get("boundary", False)),
            why=str(row.get("why", "")),
        )
        for row in payload["queries"]
    )


def answer_shape(agent_class: str, skill: str) -> str:
    """The synthesis skill a routed question is answered with.

    A specialist translates its own skill names and passes through the ones
    with a template of their own; a class with no specialist uses the skill as
    chosen.
    """

    from app.agents.registry import get_domain_agent_registry

    specialist = get_domain_agent_registry().get_agent(agent_class)
    return specialist.pipeline_skill_for(skill) if specialist is not None else skill


def rule_route(question: str) -> tuple[str, str]:
    """What the router answers with no model: the keyword rules and the specialist's own skill choice."""

    from app.agents.router.routing import _skill_for
    from app.services.agent_classifier import classify_agent_class

    agent_class = classify_agent_class(question)
    return agent_class, _skill_for(agent_class, question)


def evaluate(
    cases: tuple[RoutingCase, ...],
    route: Callable[[str], tuple[str, str]] = rule_route,
) -> RoutingReport:
    outcomes = tuple(RoutingOutcome(case, *route(case.question)) for case in cases)
    per_class: dict[str, tuple[int, int]] = {}
    for outcome in outcomes:
        correct, total = per_class.get(outcome.case.agent_class, (0, 0))
        per_class[outcome.case.agent_class] = (correct + outcome.class_correct, total + 1)
    return RoutingReport(outcomes=outcomes, per_class=per_class)
