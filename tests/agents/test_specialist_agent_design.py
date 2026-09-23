"""The rest of the 2026-09-23 specialist review: skill order, scoring, dead parts, registry.

Each section names the defect it pins. Every one was reproduced against the code
before the fix rather than argued from reading it.
"""

from __future__ import annotations

import logging

import pytest

import app.agents.registry as registry_module
from app.agents import ai as ai_package
from app.agents import cybersecurity as cyber_package
from app.agents.ai.service import AIAgentService
from app.agents.base import BaseSpecialistAgent
from app.agents.cybersecurity.service import CybersecurityAgentService, extract_security_indicators
from app.agents.registry import DomainAgentRegistry
from app.services import agent_classifier


class _Specialist(BaseSpecialistAgent):
    """A minimal specialist; its synthesizer is never called here."""

    def __init__(self, agent_class: str, skills: tuple[str, ...] = ()) -> None:
        super().__init__(synthesizer=object())  # type: ignore[arg-type]
        self._class = agent_class
        self._skills = skills

    @property
    def agent_class(self) -> str:
        return self._class

    @property
    def supported_skills(self) -> tuple[str, ...]:
        return self._skills


# --- 3a: the security specialist asks "how do I respond" before "what is it" ---


@pytest.mark.parametrize(
    ("question", "skill"),
    [
        # Named a CVE and asked for a response: used to be attack analysis.
        ("CVE-2021-44228 漏洞应急处置步骤", "cybersecurity_incident_response"),
        ("我们被 Log4Shell 打了，怎么隔离恢复？", "cybersecurity_incident_response"),
        # Named a CVE and asked what it affects: the assessment skill could not
        # be reached by any question containing "cve".
        ("CVE-2024-3094 影响哪些版本，怎么修复？", "cve_vulnerability_assessment"),
        ("Is CVE-2024-3094 exploitable, and which versions are affected?", "cve_vulnerability_assessment"),
        ("横向移动一般是怎么做到的？", "cyber_attack_analysis"),
        ("讲讲这个攻击链", "cyber_attack_analysis"),
    ],
)
def test_the_security_specialist_picks_by_what_is_being_asked(question: str, skill: str):
    assert CybersecurityAgentService(synthesizer=object()).pick_skill(question) == skill  # type: ignore[arg-type]


# --- 3b: a pattern adds weight; it no longer decides on its own ----------------


def test_a_prompt_injection_question_is_a_security_question():
    # Scored 2 against the AI specialist's 5 before: `\bllm\b` counted "llm" a
    # second time at three times the weight, and no keyword named the attack.
    assert DomainAgentRegistry().match_agent_class("LLM 遭遇 prompt 注入攻击怎么防护？") == "cybersecurity"


def test_injection_as_a_design_pattern_is_not_a_security_question():
    # Why the new keywords are phrases and not a bare "注入".
    assert DomainAgentRegistry().match_agent_class("依赖注入和控制反转有什么区别？") != "cybersecurity"


def test_a_strong_pattern_still_outweighs_several_generic_words():
    # llm, rag and prompt are three AI keywords; a CVE id is one keyword plus
    # one pattern. The pattern weight is what keeps the specific signal ahead.
    question = "用 LLM 和 RAG 做 CVE-2021-44228 的 prompt 分析"
    assert DomainAgentRegistry().match_agent_class(question) == "cybersecurity"


def test_a_pattern_hit_no_longer_returns_ahead_of_the_keywords():
    registry = DomainAgentRegistry()

    class _PatternOnly(_Specialist):
        @property
        def intent_patterns(self) -> tuple[str, ...]:
            return (r"\bquux\b",)

    class _Keywords(_Specialist):
        @property
        def intent_keywords(self) -> tuple[str, ...]:
            return ("alpha", "beta", "gamma", "delta")

    registry.register_agent(_PatternOnly("pattern_only"))
    registry.register_agent(_Keywords("keywords"))

    # One pattern (3) against four keywords (4). Before, the pattern returned first.
    assert registry.match_agent_class("quux alpha beta gamma delta") == "keywords"


# --- 4: the domain system prompts nothing read are gone ------------------------


@pytest.mark.parametrize(
    ("module", "name"),
    [
        (ai_package, "AI_SPECIALIST_SYSTEM_PROMPT"),
        (cyber_package, "CYBERSECURITY_SYSTEM_PROMPT"),
    ],
)
def test_no_specialist_exports_a_prompt_nothing_reads(module, name: str):
    # Exported, documented, and never passed to a model. Reintroducing one is a
    # decision about how it reaches generation, not a constant to add back.
    assert not hasattr(module, name)
    assert not hasattr(module.service, name)


# --- 5: one AI skill, because there is one AI answer shape ---------------------


@pytest.mark.parametrize(
    "question",
    ["训练 7B 模型需要多少 FLOPs", "这个模型有多少 layer", "multiplayer 游戏的推荐算法", "显存 80 GB 够不够"],
)
def test_the_ai_specialist_has_one_skill(question: str):
    agent = AIAgentService(synthesizer=object())  # type: ignore[arg-type]

    assert agent.supported_skills == ("ai_deep_dive",)
    assert agent.pick_skill(question) == "ai_deep_dive"


@pytest.mark.parametrize(
    "agent",
    [AIAgentService(synthesizer=object()), CybersecurityAgentService(synthesizer=object())],  # type: ignore[arg-type]
    ids=lambda a: a.agent_class,
)
def test_every_declared_skill_is_translated_and_nothing_else_is(agent: BaseSpecialistAgent):
    # A skill without a translation falls to the fallback; a translation for a
    # skill nobody declares is a distinction the router can never ask for.
    assert set(agent.pipeline_skills) == set(agent.supported_skills)


# --- 6: an extension's agent is not overwritten by the built-in ---------------


def test_an_agent_registered_before_the_first_lookup_survives_it():
    registry = DomainAgentRegistry()
    mine = _Specialist("cybersecurity", ("my_skill",))

    registry.register_agent(mine)

    # The first lookup used to build the built-in and write it over this one.
    assert registry.get_agent("cybersecurity") is mine
    assert registry.get_agent_for_skill("my_skill") is mine
    assert registry.get_agent("artificial_intelligence") is not None  # the other default still loads


def test_a_class_already_registered_is_not_even_built(monkeypatch: pytest.MonkeyPatch):
    built: list[str] = []

    def factory() -> BaseSpecialistAgent:
        built.append("cybersecurity")
        return _Specialist("cybersecurity")

    monkeypatch.setattr(registry_module, "_BUILTIN_AGENT_FACTORIES", {"cybersecurity": factory})
    registry = DomainAgentRegistry()
    registry.register_agent(_Specialist("cybersecurity"))

    registry.list_agents()

    assert built == []


# --- 7: a built-in that fails to build is retried, reported, and isolated -----


def test_a_failing_default_is_isolated_reported_and_retried(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    broken = {"now": True}

    def flaky() -> BaseSpecialistAgent:
        if broken["now"]:
            raise RuntimeError("model settings unreadable")
        return _Specialist("cybersecurity")

    monkeypatch.setattr(
        registry_module,
        "_BUILTIN_AGENT_FACTORIES",
        {"cybersecurity": flaky, "artificial_intelligence": lambda: _Specialist("artificial_intelligence")},
    )
    registry = DomainAgentRegistry()

    with caplog.at_level(logging.DEBUG, logger=registry_module.__name__):
        # One failure no longer takes the other default with it...
        assert registry.get_agent("artificial_intelligence") is not None
        assert registry.get_agent("cybersecurity") is None
        # ...is named rather than looking like a specialist that was never shipped...
        assert "cybersecurity" in registry.describe()["unavailable_defaults"]

        # ...and is retried: the registry used to mark itself initialized and stop.
        broken["now"] = False
        assert registry.get_agent("cybersecurity") is not None
        assert registry.describe()["unavailable_defaults"] == {}

    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(errors) == 1, "the traceback is logged once, not on every retry"


# --- minor: indicator extraction ----------------------------------------------


@pytest.mark.parametrize(
    ("text", "ips"),
    [
        ("来源 192.168.1.100 和 10.0.0.5", ["10.0.0.5", "192.168.1.100"]),
        ("攻击来自 10.0.0.5.", ["10.0.0.5"]),  # the address that ends a sentence
        ("999.1.1.1 is not an address", []),
        ("upgrade to 1.2.3.4.5", []),  # a version string's first four parts
    ],
)
def test_ip_extraction(text: str, ips: list[str]):
    assert extract_security_indicators(text)["ips"] == ips


@pytest.mark.parametrize(("length", "found"), [(32, True), (40, True), (64, True), (50, False), (33, False)])
def test_hash_extraction_takes_only_digest_lengths(length: int, found: bool):
    digest = ("a1B2" * 20)[:length]
    assert bool(extract_security_indicators(f"hash {digest} seen")["hashes"]) is found


# --- minor: one definition of the domain classes -------------------------------


def test_the_rule_classifier_has_no_domain_lists_of_its_own(monkeypatch: pytest.MonkeyPatch):
    # With the registry gone, a security question is not recognised: the
    # registry is the only place the domain vocabulary lives. The copies that
    # used to sit here had drifted from it.
    def unavailable():
        raise RuntimeError("registry down")

    monkeypatch.setattr(registry_module, "get_domain_agent_registry", unavailable)

    assert agent_classifier.classify_agent_class("如何防护勒索病毒") == "general"
    assert agent_classifier.classify_agent_class("读取这份pdf") == "pdf_text"  # the class no specialist owns


def test_the_second_security_skill_picker_is_gone():
    # It returned a different vocabulary of skills from the specialist's, and
    # could only run when the registry was unavailable.
    assert not hasattr(agent_classifier, "pick_cyber_skill")
