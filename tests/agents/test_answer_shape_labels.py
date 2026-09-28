"""Every answer shape and every tool the backend can report has a name in the UI.

`frontend/src/pages/chat/answerLabels.ts` turns a skill id and a tool id into
the words a reader sees. A skill the router can choose, or a tool the tool stage
can run, that is missing from it is shown as a raw identifier -- nothing fails,
which is why it is checked here, the same way `test_agent_class_vocabulary.py`
checks the agent classes.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.agents.shared.config import VALID_SKILLS

ROOT = Path(__file__).resolve().parents[2]
LABELS = ROOT / "frontend" / "src" / "pages" / "chat" / "answerLabels.ts"
_TOOL_ID_RE = re.compile(r"\"(querymind_[a-z_]+)\"")
# Names in app/ shaped like a tool id that are not tools.
_NOT_TOOLS = {"querymind_services", "querymind_multimodal_knowledge_workflow"}


def _function_body(name: str) -> str:
    text = LABELS.read_text(encoding="utf-8")
    start = text.index(f"export function {name}(")
    end = text.find("\nexport ", start + 1)
    return text[start : end if end != -1 else len(text)]


def _cases(name: str) -> set[str]:
    return set(re.findall(r'case "([a-z_]+)":', _function_body(name)))


def _declared_shapes() -> set[str]:
    text = LABELS.read_text(encoding="utf-8")
    block = text[text.index("export const ANSWER_SHAPES") : text.index("] as const;")]
    return set(re.findall(r'"([a-z_]+)"', block))


def _backend_tool_ids() -> set[str]:
    found: set[str] = set()
    for path in (ROOT / "app").rglob("*.py"):
        found.update(_TOOL_ID_RE.findall(path.read_text(encoding="utf-8")))
    return found - _NOT_TOOLS


def test_the_declared_shapes_are_exactly_the_skills_the_router_may_choose() -> None:
    assert _declared_shapes() == set(VALID_SKILLS)


def test_every_declared_shape_has_a_label() -> None:
    assert _cases("useAnswerShapeLabel") == _declared_shapes()


def test_every_tool_id_in_the_backend_has_a_label() -> None:
    missing = _backend_tool_ids() - _cases("useToolLabel")
    assert not missing, f"tools with no name in answerLabels.ts: {sorted(missing)}"


def test_the_tool_scan_finds_the_tools_it_exists_for() -> None:
    # A scan that silently stops matching makes the test above pass on nothing.
    assert {"querymind_cyber_cve_lookup", "querymind_table_query", "querymind_ai_memory_estimate"} <= (
        _backend_tool_ids()
    )
