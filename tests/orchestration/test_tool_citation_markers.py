"""Each cited tool result carries the number the finished answer gives it.

The client's tool panel has to show the same `T{k}` as the answer's tool-source
list, and it cannot derive it: the number follows the order the answer first
cites each tool, and counts only citable results.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.domain.contracts import ToolResult
from app.orchestration.langgraph.nodes import _mark_cited_tools, _tool_sources


class _Privacy:
    def filter_output(self, text, evidence, scope):
        return SimpleNamespace(answer=text, redaction_count=0)


def _run(answer: str, results: tuple[ToolResult, ...]) -> tuple[str, tuple[ToolResult, ...]]:
    numbered, _, _, cited = _tool_sources(_Privacy(), answer, results, "zh", scope=None)
    return numbered, _mark_cited_tools(results, cited)


def test_the_number_follows_the_order_of_first_citation_not_the_order_run() -> None:
    first = ToolResult(tool_id="querymind_cyber_product_exposure", status="succeeded", summary="exposure")
    second = ToolResult(tool_id="querymind_cyber_cve_lookup", status="succeeded", summary="cve")

    numbered, marked = _run("CVSS 10.0 [T2]，受影响版本见 [T1]。", (first, second))

    assert numbered.startswith("CVSS 10.0 [T1]")
    assert [(r.tool_id, r.citation_marker) for r in marked] == [
        ("querymind_cyber_product_exposure", "T2"),
        ("querymind_cyber_cve_lookup", "T1"),
    ]


def test_a_result_that_cannot_be_cited_never_gets_a_number() -> None:
    failed = ToolResult(tool_id="querymind_table_query", status="failed", summary="SQL error")
    derived = ToolResult(tool_id="querymind_cyber_indicator_extract", status="succeeded", summary="x", derived=True)
    listed = ToolResult(tool_id="querymind_table_list", status="succeeded", summary="tables")

    _, marked = _run("三张表 [T1]。", (failed, derived, listed))

    assert [r.citation_marker for r in marked] == [None, None, "T1"]


def test_an_answer_citing_no_tool_leaves_every_result_unnumbered() -> None:
    result = ToolResult(tool_id="querymind_ai_memory_estimate", status="succeeded", summary="130 GiB")

    _, marked = _run("没有引用工具。", (result,))

    assert marked[0].citation_marker is None
