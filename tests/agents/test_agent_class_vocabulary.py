"""Agent classes have one definition, and every reader applies one rule.

The list was written out by hand four times in the backend and seven times in
the frontend, and two of the backend copies had already drifted: the LLM intent
classifier's lacked ``policy``, and the API's hint normalizer ignored classes a
registered specialist declares while the router's honoured them. Neither
failure raises -- an unrecognised class becomes ``general``, which is exactly
what an ordinary unrecognised question looks like.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.agents.base import BaseSpecialistAgent
from app.agents.catalog import BUILTIN_AGENT_CLASSES, AgentClass, known_agent_classes, normalize_agent_class
from app.agents.registry import get_domain_agent_registry, reset_domain_agent_registry

_REPO = Path(__file__).resolve().parents[2]
_DEFINITION = _REPO / "app" / "agents" / "catalog.py"
_FRONTEND = _REPO / "frontend" / "src"
_FRONTEND_TYPES = _FRONTEND / "pages" / "chat" / "types.ts"
_FRONTEND_MODES = _FRONTEND / "pages" / "chat" / "constants.ts"

#: Classes the backend ships that the chat sidebar deliberately offers no card
#: for, each with the reason. A class added to `AgentClass` without a card and
#: without an entry here fails, so the omission is a decision, not an accident.
CLASSES_WITHOUT_A_CARD: dict[str, str] = {
    AgentClass.POLICY: "no specialist answers it yet; the card lands with the compliance agent",
}

#: Classes the LLM intent classifier's prompt deliberately does not describe.
CLASSES_THE_LLM_IS_NOT_OFFERED: dict[str, str] = {
    AgentClass.POLICY: "assigned to uploads by filename only; no specialist answers it yet",
}


@pytest.fixture(autouse=True)
def _fresh_registry():
    reset_domain_agent_registry()
    yield
    reset_domain_agent_registry()


class _ExtensionAgent(BaseSpecialistAgent):
    """A specialist an extension registers, so its class is not a built-in."""

    def __init__(self) -> None:
        super().__init__(synthesizer=SimpleNamespace())

    @property
    def agent_class(self) -> str:
        return "finance"


# --- one definition ----------------------------------------------------------


def _hand_written_class_lists(path: Path) -> list[tuple[int, list[str]]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Set | ast.List | ast.Tuple | ast.Dict):
            elements = node.keys if isinstance(node, ast.Dict) else node.elts
            named = [e.value for e in elements if isinstance(e, ast.Constant) and e.value in BUILTIN_AGENT_CLASSES]
            if len(named) >= 2:
                found.append((node.lineno, named))
    return found


def _python_sources() -> list[Path]:
    return [
        p
        for root in ("app", "scripts")
        for p in (_REPO / root).rglob("*.py")
        if "__pycache__" not in p.parts and p != _DEFINITION
    ]


@pytest.mark.parametrize("path", _python_sources(), ids=lambda p: str(p.relative_to(_REPO)))
def test_no_module_writes_out_its_own_list_of_agent_classes(path: Path) -> None:
    """A second list is how the copies drifted; a single class name is fine.

    Only collections naming two or more classes count, because a lone
    ``"cybersecurity"`` is also a tool category and a skill prefix, and flagging
    those would bury the one shape that actually caused the drift.
    """

    lists = _hand_written_class_lists(path)
    assert not lists, (
        f"{path.relative_to(_REPO)} writes out agent classes by hand at {lists}. "
        "Use AgentClass / BUILTIN_AGENT_CLASSES / known_agent_classes() from app/agents/catalog.py."
    )


def test_the_scan_can_find_a_hand_written_list(tmp_path: Path) -> None:
    """The scan above passes on the shipped tree; prove it is able not to."""

    planted = tmp_path / "planted.py"
    planted.write_text('ALLOWED = {"general", "cybersecurity", "pdf_text"}\nTOOL = "cybersecurity"\n', encoding="utf-8")
    assert _hand_written_class_lists(planted) == [(1, ["general", "cybersecurity", "pdf_text"])]


# --- one rule ----------------------------------------------------------------


def _router_rule(value: str | None) -> str | None:
    from app.agents.router import routing

    return routing._normalize_agent_class_hint(value)


def _api_rule(value: str | None) -> str | None:
    """What the prompts API resolves a hint to, or None where it guessed instead."""

    from app.api import dependencies

    resolved = dependencies._resolve_effective_agent_class("今天天气怎么样", value)
    return resolved if resolved == normalize_agent_class(value) else None


def _llm_rule(value: str | None, monkeypatch: pytest.MonkeyPatch) -> str:
    from app.services.query import intent_classifier

    payload = '{"agent_class": %s, "confidence": 0.9, "reason": "stub"}' % ("null" if value is None else f'"{value}"')
    model = SimpleNamespace(invoke=lambda messages: SimpleNamespace(content=payload))
    monkeypatch.setattr(intent_classifier, "get_chat_model", lambda **kwargs: model)
    return intent_classifier.classify_intent_with_llm("q")["agent_class"]


_INPUTS = [*sorted(BUILTIN_AGENT_CLASSES), "  CyberSecurity ", "finance", "not_a_class", "", None]


@pytest.mark.parametrize("value", _INPUTS)
def test_every_reader_applies_the_catalog_rule(value: str | None, monkeypatch: pytest.MonkeyPatch) -> None:
    get_domain_agent_registry().register_agent(_ExtensionAgent())
    expected = normalize_agent_class(value)

    assert _router_rule(value) == expected
    assert _api_rule(value) == expected
    assert _llm_rule(value, monkeypatch) == (expected or AgentClass.GENERAL)


def test_a_class_an_extension_registers_is_known() -> None:
    """The API's copy used to reject this while the router accepted it."""

    assert "finance" not in known_agent_classes()
    get_domain_agent_registry().register_agent(_ExtensionAgent())
    assert "finance" in known_agent_classes()
    assert normalize_agent_class("Finance") == "finance"


def test_the_llm_classifier_accepts_policy() -> None:
    """Its own set of four lacked `policy`; the unified rule does not."""

    assert normalize_agent_class("policy") == AgentClass.POLICY


def test_an_upload_label_is_always_a_known_class() -> None:
    from app.api.deps.documents import _guess_agent_class_for_upload

    for name in ("report.pdf", "scan.png", "CVE漏洞处置.docx", "大模型训练笔记.md", "notes.txt"):
        assert _guess_agent_class_for_upload(name) in known_agent_classes()
    assert _guess_agent_class_for_upload("report.pdf") == AgentClass.PDF_TEXT


# --- the frontend ------------------------------------------------------------


def _frontend_union() -> set[str]:
    source = _FRONTEND_TYPES.read_text(encoding="utf-8")
    match = re.search(r"export type AgentClassHint = ([^;]+);", source)
    assert match, f"{_FRONTEND_TYPES.name} no longer declares AgentClassHint"
    return set(re.findall(r'"([^"]*)"', match.group(1)))


def test_the_frontend_declares_the_hint_type_once() -> None:
    declarations = [
        str(p.relative_to(_REPO))
        for p in _FRONTEND.rglob("*.ts*")
        if re.search(r"^\s*(export\s+)?type AgentClassHint\s*=", p.read_text(encoding="utf-8"), re.MULTILINE)
    ]
    assert declarations == [str(_FRONTEND_TYPES.relative_to(_REPO))]


def test_the_frontend_offers_only_classes_the_backend_knows() -> None:
    offered = _frontend_union() - {""}
    assert offered, "the frontend offers no agent classes at all"
    assert offered <= BUILTIN_AGENT_CLASSES, f"unknown to the backend: {sorted(offered - BUILTIN_AGENT_CLASSES)}"


def test_every_backend_class_has_a_card_or_a_reason() -> None:
    missing = BUILTIN_AGENT_CLASSES - _frontend_union() - set(CLASSES_WITHOUT_A_CARD)
    assert not missing, f"no sidebar card and no entry in CLASSES_WITHOUT_A_CARD: {sorted(missing)}"
    stale = set(CLASSES_WITHOUT_A_CARD) & _frontend_union()
    assert not stale, f"CLASSES_WITHOUT_A_CARD lists classes that now have a card: {sorted(stale)}"


def test_every_mode_card_names_a_class_in_the_union() -> None:
    source = _FRONTEND_MODES.read_text(encoding="utf-8")
    block = re.search(r"export const AGENT_MODES[^=]*= \[(.*?)\n\];", source, re.DOTALL)
    assert block, f"{_FRONTEND_MODES.name} no longer declares AGENT_MODES"
    keys = set(re.findall(r'key: "([^"]*)"', block.group(1)))
    assert keys == _frontend_union()


# --- the LLM classifier's prompt ----------------------------------------------


def test_the_llm_prompt_describes_every_class_it_may_choose() -> None:
    """A class the prompt never names is one the model will never return."""

    from app.services.query.intent_classifier import INTENT_CLASSIFICATION_PROMPT

    described = set(re.findall(r"^\d+\. ([a-z_]+)（", INTENT_CLASSIFICATION_PROMPT, re.MULTILINE))
    expected = BUILTIN_AGENT_CLASSES - set(CLASSES_THE_LLM_IS_NOT_OFFERED)
    assert described == expected
