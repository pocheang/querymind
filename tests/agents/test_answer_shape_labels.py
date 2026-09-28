"""Every answer shape and every tool the backend can report has a name in the UI.

`frontend/src/pages/chat/answerLabels.ts` lists the skill ids and tool ids it
names for the reader (`answerLabels.test.ts` checks each has a locale entry). A
skill the router can choose, or a tool the tool stage can run, that is missing
from those lists is shown as a raw identifier -- nothing fails, which is why it
is checked here, the same way `test_agent_class_vocabulary.py` checks the agent
classes.
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


def _array(name: str) -> set[str]:
    text = LABELS.read_text(encoding="utf-8")
    start = text.index(f"export const {name}")
    block = text[start : text.index("];", start)]
    return set(re.findall(r'"([a-z_]+)"', block))


def _backend_tool_ids() -> set[str]:
    found: set[str] = set()
    for path in (ROOT / "app").rglob("*.py"):
        found.update(_TOOL_ID_RE.findall(path.read_text(encoding="utf-8")))
    return found - _NOT_TOOLS


def test_the_declared_shapes_are_exactly_the_skills_the_router_may_choose() -> None:
    assert _array("ANSWER_SHAPES") == set(VALID_SKILLS)


def test_every_tool_id_in_the_backend_has_a_label() -> None:
    missing = _backend_tool_ids() - _array("TOOL_IDS")
    assert not missing, f"tools with no name in answerLabels.ts: {sorted(missing)}"


def test_the_tool_scan_finds_the_tools_it_exists_for() -> None:
    # A scan that silently stops matching makes the test above pass on nothing.
    assert {"querymind_cyber_cve_lookup", "querymind_table_query", "querymind_ai_memory_estimate"} <= (
        _backend_tool_ids()
    )
