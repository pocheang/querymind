"""Cross-page table detection and merging."""

import re

_SEPARATOR_ROW_RE = re.compile(r"^\|[\s\-:]+\|")
"""The row under a markdown table header.

Named on 2026-09-05 because three call sites had to agree on it. Two of them,
`is_table_start` and `extract_table_header`, were deleted the next day together
with `merge_table_pages`, their only caller -- so one asks it today. Still named
and compiled once: `is_table_continuation` is defined by what it excludes, and a
bare pattern there would say less than the name does."""


def _is_table_row(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.endswith("|") and s.count("|") >= 2


def _is_table_separator(line: str) -> bool:
    s = line.strip()
    return bool(re.match(r"^\|(?:\s*:?-[-:]*\s*\|)+$", s))


def _extract_markdown_cells(line: str) -> list[str]:
    parts = re.split(r"(?<!\\)\|", line)
    if len(parts) >= 2 and parts[0].strip() == "" and parts[-1].strip() == "":
        parts = parts[1:-1]
    return [p.replace(r"\|", "|").strip() for p in parts]


def _extract_table_header_from_end(text: str) -> tuple[int, list[str]]:
    """Extract column count and header cells of the last table in text."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    header_idx = -1
    for idx in range(len(lines) - 1, -1, -1):
        line = lines[idx]
        if _is_table_separator(line) and idx > 0 and _is_table_row(lines[idx - 1]):
            header_idx = idx - 1
            break
    if header_idx != -1:
        cells = _extract_markdown_cells(lines[header_idx])
        return len(cells), cells
    for line in reversed(lines[-5:]):
        if _is_table_row(line) and not _is_table_separator(line):
            cells = _extract_markdown_cells(line)
            if cells:
                return len(cells), []
    return 0, []


def _extract_table_columns_from_end(text: str) -> int:
    return _extract_table_header_from_end(text)[0]


def is_table_continuation(text: str, prev_cols: int | None = None, prev_headers: list[str] | None = None) -> bool:
    """Check if text looks like table continuation.

    Args:
        text: Text content
        prev_cols: Optional expected column count from previous page's table
        prev_headers: Optional expected column headers from previous page's table

    Returns:
        True if looks like table continuation
    """
    is_cont, _ = check_table_continuation(text, prev_cols=prev_cols, prev_headers=prev_headers)
    return is_cont


def _find_first_table_line_idx(lines: list[str]) -> int:
    for idx, line in enumerate(lines[:5]):
        if line.startswith(("#", "第")) and not line.startswith("|"):
            return -1
        if _is_table_row(line):
            return idx
    return -1


def _matches_repeated_header(
    first_tbl_idx: int,
    first_cells: list[str],
    prev_headers: list[str] | None,
) -> tuple[bool, int]:
    if not prev_headers:
        return False, 0
    norm_prev = [h.strip().lower() for h in prev_headers if h.strip()]
    norm_curr = [c.strip().lower() for c in first_cells if c.strip()]
    if norm_prev and norm_curr:
        matches = sum(1 for p, c in zip(norm_prev, norm_curr, strict=False) if p == c)
        if matches / max(len(norm_prev), 1) < 0.6:
            return False, 0
    return True, first_tbl_idx + 2


def _matches_direct_continuation_data(
    lines: list[str],
    first_tbl_idx: int,
    col_count: int,
) -> bool:
    pipe_lines = [ln for ln in lines[first_tbl_idx : first_tbl_idx + 5] if _is_table_row(ln)]
    if len(pipe_lines) >= 1:
        pipe_counts = [len(_extract_markdown_cells(ln)) for ln in pipe_lines]
        if len(set(pipe_counts)) == 1 and pipe_counts[0] == col_count:
            return True
    return False


def check_table_continuation(
    text: str,
    prev_cols: int | None = None,
    prev_headers: list[str] | None = None,
) -> tuple[bool, int]:
    """Check if text is a table continuation, returning (is_continuation, data_start_line_idx).

    Supports:
    1. Direct table continuation without header (just data rows matching columns).
    2. Repeated header continuation (where next page repeats header row + separator row).
    3. Column count and header similarity validation against previous page table.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False, 0

    first_tbl_idx = _find_first_table_line_idx(lines)
    if first_tbl_idx == -1:
        return False, 0

    first_cells = _extract_markdown_cells(lines[first_tbl_idx])
    col_count = len(first_cells)
    if col_count < 2 or (prev_cols is not None and prev_cols > 0 and col_count != prev_cols):
        return False, 0

    has_sep = first_tbl_idx + 1 < len(lines) and _is_table_separator(lines[first_tbl_idx + 1])
    if has_sep:
        return _matches_repeated_header(first_tbl_idx, first_cells, prev_headers)

    if _matches_direct_continuation_data(lines, first_tbl_idx, col_count):
        return True, first_tbl_idx

    return False, 0


def detect_incomplete_table(text: str) -> bool:
    """Detect if page ends with an incomplete table.

    Args:
        text: Page text content

    Returns:
        True if page likely ends with incomplete table
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return False

    last_lines = lines[-5:]
    table_lines = [line for line in last_lines if _is_table_row(line)]

    if len(table_lines) >= 1 and _is_table_row(lines[-1]) and not _is_table_separator(lines[-1]):
        return True

    return False


def _extract_continuation_parts(next_lines: list[str], start_idx: int) -> tuple[list[str], list[str], list[str]]:
    prefix_notes: list[str] = []
    if start_idx >= 2 and _is_table_separator(next_lines[start_idx - 1]):
        prefix_notes = next_lines[: start_idx - 2]
    elif start_idx > 0 and not _is_table_row(next_lines[0]):
        prefix_notes = next_lines[:start_idx]

    table_cont_lines: list[str] = []
    k = start_idx
    while k < len(next_lines) and _is_table_row(next_lines[k]):
        table_cont_lines.append(next_lines[k])
        k += 1

    remaining_lines = next_lines[k:]
    return prefix_notes, table_cont_lines, remaining_lines


def _combine_page_fragments(current: str, prefix_notes: list[str], text_block: str) -> str:
    if prefix_notes:
        return current.rstrip() + "\n\n" + "\n".join(prefix_notes) + "\n\n" + text_block
    if text_block:
        return current.rstrip() + "\n" + text_block
    return current


def _merge_next_page_table(
    current: str,
    next_page: str,
) -> tuple[bool, str, str, bool]:
    prev_cols, prev_headers = _extract_table_header_from_end(current)
    is_cont, start_idx = check_table_continuation(next_page, prev_cols=prev_cols, prev_headers=prev_headers)
    if not is_cont:
        return False, current, next_page, True

    next_lines = [ln.strip() for ln in next_page.splitlines() if ln.strip()]
    prefix_notes, table_cont_lines, remaining_lines = _extract_continuation_parts(next_lines, start_idx)

    has_heading = any(ln.startswith(("#", "第")) for ln in remaining_lines)
    is_substantial_prose = len("\n".join(remaining_lines)) > 300

    if has_heading or is_substantial_prose:
        cont_text = "\n".join(table_cont_lines)
        merged_current = _combine_page_fragments(current, prefix_notes, cont_text)
        next_page_remaining = "\n\n".join(remaining_lines)
        return True, merged_current, next_page_remaining, True

    cleaned_next = "\n".join(next_lines[start_idx:]) if start_idx < len(next_lines) else ""
    merged_current = _combine_page_fragments(current, prefix_notes, cleaned_next.lstrip())
    return True, merged_current, "", False


def merge_cross_page_tables_with_spans(pages_content: list[str]) -> list[tuple[str, list[int]]]:
    """Merge tables across pages while tracking 1-indexed page spans.

    Args:
        pages_content: List of page content (Markdown format)

    Returns:
        List of tuples: (merged_page_content, list_of_original_1_indexed_page_numbers)
    """
    if not pages_content:
        return []

    spanned: list[tuple[str, list[int]]] = []
    i = 0
    n = len(pages_content)

    while i < n:
        current = pages_content[i]
        current_span = [i + 1]

        while i + 1 < n and detect_incomplete_table(current):
            merged, current, next_remaining, stop = _merge_next_page_table(current, pages_content[i + 1])
            if not merged:
                break
            current_span.append(i + 2)
            if stop:
                pages_content[i + 1] = next_remaining
                break
            i += 1

        spanned.append((current, current_span))
        i += 1

    return spanned


def merge_cross_page_tables(pages_content: list[str]) -> list[str]:
    """Main function to merge tables across pages.

    Args:
        pages_content: List of page content (Markdown format)

    Returns:
        List of pages with cross-page tables merged
    """
    spanned = merge_cross_page_tables_with_spans(pages_content)
    return [content for content, _ in spanned]
