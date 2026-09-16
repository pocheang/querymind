"""Nested table detection and flattening."""

import re

# `[^>]*>` is what the lazy `<table.*?>` meant; two lazy dot-alls in a row could
# trade characters between them (python:S8786).
_HTML_TABLE_RE = re.compile(r"<table[^>]*>.*?</table>", re.IGNORECASE | re.DOTALL)
_ESCAPED_PIPE_TABLE_RE = re.compile(r"\\\|.+?\\\|")
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def detect_nested_table(text: str) -> bool:
    """Detect if text contains nested tables (table within table cells, HTML tables, etc.).

    Args:
        text: Markdown text

    Returns:
        True if nested tables detected
    """
    if not text:
        return False

    if "<table" in text.lower() and "</table" in text.lower():
        return True

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if not (line.startswith("|") and line.endswith("|")):
            continue

        # Check for escaped pipe structures inside cells (e.g. "\| sub1 \| sub2 \|")
        if _ESCAPED_PIPE_TABLE_RE.search(line):
            return True

        # Check for HTML table tags inside cells
        lowered = line.lower()
        if "<td" in lowered or "<tr" in lowered or "<th" in lowered:
            return True

        # Check for nested bracketed sub-tables: [| ... |]
        if re.search(r"\[\|.+?\|\]", line):
            return True

    return False


def _process_nested_table_line(line: str) -> str:
    """Process a single markdown table line to clean escaped pipes and HTML tags."""
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return line

    inner_content = stripped[1:-1]
    raw_cells = re.split(r"(?<!\\)\|", inner_content)
    processed_cells: list[str] = []

    for cell in raw_cells:
        c = cell.strip()
        if "\\|" in c:
            c = "; ".join(part.strip() for part in c.split("\\|"))
        if "<" in c and ">" in c:
            c = _HTML_TAG_RE.sub("", c).strip()
        processed_cells.append(c)

    return "| " + " | ".join(processed_cells) + " |"


def flatten_nested_table(text: str) -> str:
    """Flatten nested tables into single-level structure.

    Args:
        text: Markdown text with potential nested tables

    Returns:
        Flattened text
    """
    if not detect_nested_table(text):
        return text

    # First, replace any inline HTML table tags with flattened text
    def _clean_html_cell(match: re.Match) -> str:
        inner = match.group(0)
        cell_contents = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", inner, re.IGNORECASE | re.DOTALL)
        if cell_contents:
            return "; ".join(_HTML_TAG_RE.sub("", c).strip() for c in cell_contents if c.strip())
        return _HTML_TAG_RE.sub(" ", inner).strip()

    processed = _HTML_TABLE_RE.sub(_clean_html_cell, text)

    # Flatten bracketed sub-tables [| a | b |] -> [a; b] before splitting by pipes
    processed = re.sub(
        r"\[\|(.+?)\|\]",
        lambda m: "[" + "; ".join(part.strip() for part in m.group(1).split("|") if part.strip()) + "]",
        processed,
    )

    return "\n".join(_process_nested_table_line(line) for line in processed.splitlines())


def simplify_complex_table(text: str) -> str:
    """Simplify complex tables for better LLM understanding.

    Args:
        text: Markdown table text

    Returns:
        Simplified table text
    """
    # Flatten nested tables
    text = flatten_nested_table(text)

    # Normalize cell spacing
    lines = text.splitlines()
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            inner = stripped[1:-1]
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", inner)]
            cleaned_line = "| " + " | ".join(cells) + " |"
            cleaned_lines.append(cleaned_line)
        else:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)
