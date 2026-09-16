"""Table Entity Extraction and Linking for Graph-Table Hybrid Retrieval."""

from __future__ import annotations

import logging
import re

from app.domain.text import normalize_string

logger = logging.getLogger(__name__)

# Common non-entity table header words and metadata terms to skip
_IGNORED_HEADER_TERMS = frozenset(
    {
        "id",
        "no",
        "num",
        "index",
        "序号",
        "编号",
        "key",
        "value",
        "val",
        "total",
        "sum",
        "avg",
        "min",
        "max",
        "count",
        "合计",
        "总计",
        "平均",
        "备注",
        "note",
        "notes",
        "comment",
        "comments",
        "status",
        "状态",
        "created_at",
        "updated_at",
        "date",
        "time",
        "日期",
        "时间",
        "year",
        "month",
        "day",
        "年",
        "月",
        "日",
        "季度",
        "quarter",
        "page",
        "sheet",
        "columns",
        "total rows",
        "operation",
        "action",
        "操作",
        "正常",
        "异常",
        "成功",
        "失败",
        "通过",
        "未通过",
        "维护中",
        "active",
        "inactive",
        "pending",
        "running",
        "warning",
        "stopped",
        "disabled",
        "enabled",
        "ok",
        "error",
        "fail",
        "success",
    }
)

# Pattern to detect purely numeric, currency, percentage, or date strings
_NUMERIC_OR_METRIC_PATTERN = re.compile(
    r"^[\s\d\.,\+\-/%$￥€¥#*&()\[\]]+$"
    r"|^\d{4}[-/.]\d{1,2}(?:[-/.]\d{1,2})?$"
    r"|^\d+(?:\.\d+)?(?:%|‰|万|亿|k|m|g|t|w)?$",
    re.IGNORECASE,
)

# Pattern to match table rows with pipes
_PIPE_ROW_PATTERN = re.compile(r"^\s*\|(.+)\|\s*$", re.MULTILINE)


def _clean_cell(cell: str) -> str:
    """Clean markdown artifacts and formatting from a cell."""
    text = cell.strip()
    # Remove markdown bold/italic/code backticks
    text = re.sub(r"[*`_~]", "", text).strip()
    return text


def _is_valid_entity_candidate(text: str) -> bool:
    """Check whether a cell or header string is a plausible business entity."""
    if not text or len(text) < 2 or len(text) > 50:
        return False

    lowered = text.lower()
    if lowered in _IGNORED_HEADER_TERMS:
        return False

    if _NUMERIC_OR_METRIC_PATTERN.match(text):
        return False

    # Filter year-prefixed metric headers like "2024预算 (万元)"
    if re.match(r"^\d{4}\s*(?:预算|金额|度|年|季度|q[1-4])", lowered):
        return False

    # Skip table divider dashes: e.g. "---", ":---:"
    if re.match(r"^:?-+:?$", text):
        return False

    # Must contain at least one word or Chinese character
    if not re.search(r"[\u4e00-\u9fffA-Za-z]", text):
        return False

    return True


def _add_entity_candidate(val: str, seen: set[str], candidates: list[str]) -> None:
    cleaned = _clean_cell(val)
    if _is_valid_entity_candidate(cleaned):
        norm = normalize_string(cleaned, lowercase=True)
        if norm and norm not in seen:
            seen.add(norm)
            candidates.append(cleaned)


def _extract_pipe_and_column_entities(
    content: str,
    max_limit: int,
    seen: set[str],
    candidates: list[str],
) -> None:
    for line in content.splitlines():
        line_s = line.strip()
        if not line_s.startswith("|"):
            if line_s.lower().startswith("columns") and ":" in line_s:
                parts = line_s.split(":", 1)[1].split("|")
                for p in parts:
                    _add_entity_candidate(p, seen, candidates)
            continue

        cells = [c.strip() for c in line_s.split("|")[1:-1]]
        for cell in cells:
            _add_entity_candidate(cell, seen, candidates)
            if len(candidates) >= max_limit:
                return


def _extract_delimiter_entities(
    content: str,
    seen: set[str],
    candidates: list[str],
) -> None:
    for line in content.splitlines()[:10]:
        for delim in ("\t", ",", " | "):
            if delim in line:
                for part in line.split(delim):
                    _add_entity_candidate(part, seen, candidates)


def extract_table_entities(content: str, max_entities: int = 15) -> list[str]:
    """Extract candidate business entities from structured table text/markdown.

    Extracts:
    1. Significant column headers
    2. Primary categorical / entity cells from data rows
    """
    if not content or not content.strip():
        return []

    candidates: list[str] = []
    seen: set[str] = set()

    _extract_pipe_and_column_entities(content, max_entities * 2, seen, candidates)
    if not candidates:
        _extract_delimiter_entities(content, seen, candidates)

    return candidates[:max_entities]


def detect_graph_table_overlap(graph_content: str, table_content: str) -> list[str]:
    """Detect shared business entities between graph triples and table content.

    Used by cross-modality resonance scoring to reward mutually reinforcing evidence.
    """
    if not graph_content or not table_content:
        return []

    # Extract entities from both sides
    table_ents = extract_table_entities(table_content, max_entities=30)
    if not table_ents:
        return []

    # For graph content, extract Entity / Neighbor / Path names
    # Pattern e.g. "Entity: X", "Neighbor: X -[...] -> Y", "Path2Hop: X -[...] -> Y -[...] -> Z"
    graph_ents: set[str] = set()
    for match in re.finditer(r"(?:Entity|Neighbor|Path2Hop):\s*([^\n\-\|]+)", graph_content):
        ent = match.group(1).strip()
        if _is_valid_entity_candidate(ent):
            graph_ents.add(normalize_string(ent, lowercase=True))

    # Also search directly for table entity mentions in the graph text
    overlapping: list[str] = []
    graph_lower = graph_content.lower()
    for ent in table_ents:
        norm = normalize_string(ent, lowercase=True)
        if norm in graph_ents or (len(norm) >= 2 and norm in graph_lower):
            overlapping.append(ent)

    return overlapping


__all__ = [
    "extract_table_entities",
    "detect_graph_table_overlap",
]
