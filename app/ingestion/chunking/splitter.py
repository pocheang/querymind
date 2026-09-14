"""Canonical document splitting and separator selection."""

from __future__ import annotations

import hashlib
import re
import uuid
from typing import Any

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter  # type: ignore
except ImportError:
    RecursiveCharacterTextSplitter = None  # type: ignore[assignment]

from app.core.config import get_settings
from app.ingestion.processing.structure import section_headings

from .metadata import enhance_chunk_metadata, extract_table_columns

# ============================================================================
# 智能分隔符选择
# ============================================================================


def get_smart_separators(doc_type: str | None = None, language: str = "mixed") -> list[str]:
    """
    Select smart separators based on document type and language

    Args:
        doc_type: Document type (markdown, code, pdf, etc.)
        language: Language (zh, en, mixed)

    Returns:
        List of separators (ordered by priority)
    """
    # Markdown文档
    if doc_type == "markdown":
        return [
            "\n## ",  # 二级标题
            "\n### ",  # 三级标题
            "\n\n",  # 段落
            "\n- ",  # 列表项
            "\n* ",  # 列表项
            "\n1. ",  # 数字列表
            "\n",  # 换行
            ". ",  # 句子
            " ",  # 空格
            "",  # 字符
        ]

    # 代码文档
    if doc_type == "code":
        return [
            "\nclass ",  # 类定义
            "\ndef ",  # 函数定义
            "\n\n",  # 空行
            "\n",  # 换行
            ";",  # 语句结束
            " ",  # 空格
            "",  # 字符
        ]

    # PDF文档（可能包含多列）
    if doc_type == "pdf":
        if language == "zh":
            return [
                "\n\n",  # 段落
                "。\n",  # 句号+换行
                "。",  # 句号
                "；",  # 分号
                "，",  # 逗号
                "\n",  # 换行
                " ",  # 空格
                "",  # 字符
            ]
        else:
            return [
                "\n\n",  # 段落
                ". \n",  # 句号+换行
                ". ",  # 句号
                "; ",  # 分号
                ", ",  # 逗号
                "\n",  # 换行
                " ",  # 空格
                "",  # 字符
            ]

    # 默认：混合语言
    return [
        "\n\n",  # 段落
        "。\n",  # 中文句号+换行
        ". \n",  # 英文句号+换行
        "。",  # 中文句号
        ". ",  # 英文句号
        "！",  # 感叹号
        "？",  # 问号
        "；",  # 分号
        "\n",  # 换行
        " ",  # 空格
        "",  # 字符
    ]


# ============================================================================
# 优化的文档切分函数
# ============================================================================


def _clone_document(doc: Any, text: str, metadata: dict[str, Any]):
    """Clone document object"""
    cls = doc.__class__
    return cls(page_content=text, metadata=metadata)


def _sanitize_chunk_params(chunk_size: int, chunk_overlap: int) -> tuple[int, int]:
    """Sanitize chunk parameters"""
    size = max(1, int(chunk_size))
    overlap = max(0, int(chunk_overlap))
    if overlap >= size:
        overlap = min(size - 1, size // 5)
    return size, overlap


class _SimpleTextSplitter:
    """Simple text splitter (fallback)"""

    def __init__(self, chunk_size: int, chunk_overlap: int):
        self.chunk_size, self.chunk_overlap = _sanitize_chunk_params(chunk_size, chunk_overlap)

    def split_text(self, text: str) -> list[str]:
        source = str(text or "")
        if not source:
            return []
        if len(source) <= self.chunk_size:
            return [source]
        step = max(1, self.chunk_size - self.chunk_overlap)
        out: list[str] = []
        i = 0
        while i < len(source):
            out.append(source[i : i + self.chunk_size])
            if i + self.chunk_size >= len(source):
                break
            i += step
        return out


def _build_splitter(chunk_size: int, chunk_overlap: int, separators: list[str]):
    """Build text splitter"""
    size, overlap = _sanitize_chunk_params(chunk_size, chunk_overlap)
    if RecursiveCharacterTextSplitter is None:
        return _SimpleTextSplitter(chunk_size=size, chunk_overlap=overlap)
    return RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        separators=separators,
    )


def _neighbours(texts: list[str], index: int) -> tuple[str | None, str | None]:
    """The raw chunks either side of `index`, for `enhance_chunk_metadata`.

    Raw, not stripped: the caller strips the chunk it is describing, and the
    neighbours are read from the splitter's own output. The two are different
    strings whenever a chunk begins or ends on whitespace, so this is a property
    of the original and not an oversight to tidy up.
    """
    previous = texts[index - 1] if index > 0 else None
    following = texts[index + 1] if index < len(texts) - 1 else None
    return previous, following


def _parent_id(identity: str, doc_idx: int, parent_idx: int, parent_text: str) -> str:
    """Stable across re-ingests when the document has an identity, random when not.

    `identity` is `{document_id}|v{version}` where both are present and the source
    path otherwise; with neither, there is nothing to be stable against and a
    uuid4 is the honest answer.
    """
    if not identity:
        return f"parent-{doc_idx}-{parent_idx}-{uuid.uuid4().hex[:8]}"
    text_hash = hashlib.sha1(parent_text.encode("utf-8")).hexdigest()[:12]
    parent_seed = f"{identity}|{doc_idx}|{parent_idx}|{text_hash}"
    return f"parent-{hashlib.sha1(parent_seed.encode('utf-8')).hexdigest()[:16]}"


def _heading_scope(text: str, carried: str | None) -> tuple[str | None, str | None]:
    """Which section this chunk sits under, and what the next chunk inherits.

    The splitter cuts by size, so a chunk from the middle of a section contains no
    heading at all -- and the separator list cuts *at* a heading, which strands it
    in a chunk of its own. Walking the chunks in order and carrying the last
    heading forward is what lets the chunks holding an answer say which section
    they came from.

    If a chunk begins with a heading (e.g. cutting at \n##), it marks the beginning
    of that new section, so its scope is immediately the new heading. Only if the chunk
    starts with body text before an embedded heading does it inherit the carried scope.
    """
    headings = section_headings(text)
    if not headings:
        return carried, carried
    cleaned_headings = [_ROW_LABEL_PATTERN.sub("", h).strip() for h in headings]
    cleaned_headings = [h for h in cleaned_headings if h and h not in ("###", "##", "#")]
    if not cleaned_headings:
        return carried, carried

    first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    starts_with_heading = any(
        first_line.startswith(h) or first_line.endswith(h) or h.endswith(first_line) or first_line == h
        for h in cleaned_headings
    ) or first_line.startswith(("#", "第"))

    current_scope = cleaned_headings[0] if (starts_with_heading or not carried) else carried
    return current_scope, cleaned_headings[-1]


_TABLE_SEP_PATTERN = re.compile(r"^\|(\s*:?-+[-:]*\s*\|)+$")
_ROW_LABEL_PATTERN = re.compile(r"\s*\(Rows?\s+\d+(?:-\d+)?\s+of\s+\d+\)", re.IGNORECASE)
_ROW_LABEL_MATCH = re.compile(r"\(Rows?\s+(\d+)(?:-(\d+))?\s+of\s+(\d+)(?:[^)]*)?\)", re.IGNORECASE)


def _is_table_row(line: str) -> bool:
    """Check if a line looks like a markdown pipe table row."""
    s = line.strip()
    return s.startswith("|") and s.endswith("|") and s.count("|") >= 2


def _is_table_separator(line: str) -> bool:
    """Check if a line matches markdown table separator row (|---|---|)."""
    s = line.strip()
    return bool(_TABLE_SEP_PATTERN.match(s))


def _clean_prefix(prefix_lines: list[str]) -> str:
    """Clean prefix lines by removing any leftover row coordinate labels to avoid label stacking."""
    cleaned: list[str] = []
    for line in prefix_lines:
        c = _ROW_LABEL_PATTERN.sub("", line).strip()
        if c and c not in ("###", "##", "#"):
            cleaned.append(c)
    return "\n\n".join(cleaned)


def _format_table_title(prefix_str: str, label: str) -> str:
    """Attach coordinate label cleanly to the primary heading line in prefix."""
    label = label.strip()
    if not prefix_str:
        return f"### {label}".strip() if label else ""
    if not label:
        return prefix_str if prefix_str.startswith("#") else f"### {prefix_str}"

    lines = [ln.strip() for ln in prefix_str.split("\n\n") if ln.strip()]
    if not lines:
        return f"### {label}".strip()

    attached = False
    new_lines = []
    for line in lines:
        if not attached and line.startswith("#"):
            new_lines.append(f"{line} {label}".strip())
            attached = True
        else:
            new_lines.append(line)

    if not attached:
        first = new_lines[0]
        if not first.startswith("#"):
            first = f"### {first}"
        new_lines[0] = f"{first} {label}".strip()

    return "\n\n".join(new_lines)


def _extract_markdown_cells(line: str) -> list[str]:
    """Extract cell contents from a markdown pipe table row, respecting escaped pipes (\\|)."""
    parts = re.split(r"(?<!\\)\|", line)
    if len(parts) >= 2 and parts[0].strip() == "" and parts[-1].strip() == "":
        parts = parts[1:-1]
    return [p.replace(r"\|", "|").strip() for p in parts]


def _extract_document_blocks(text: str) -> list[tuple[str, str]]:
    """Partition text into an ordered sequence of ('text', content) and ('table', content) blocks.

    Ensures that prose preceding, between, or following tables is completely preserved
    and not mangled or dropped.
    """
    lines = text.splitlines()
    blocks: list[tuple[str, str]] = []
    text_acc: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        if _is_table_row(lines[i]) and i + 1 < n and _is_table_separator(lines[i + 1]):
            table_titles: list[str] = []
            if text_acc:
                idx = len(text_acc) - 1
                while idx >= 0 and not text_acc[idx].strip():
                    idx -= 1
                while idx >= 0:
                    cand = text_acc[idx].strip()
                    is_title_cand = (
                        cand.startswith("#")
                        or (cand.startswith("**") and cand.endswith("**") and len(cand) < 120)
                        or cand.lower().startswith("**sheet:")
                        or cand.lower().startswith("**table")
                        or cand.startswith("**表")
                        or bool(re.match(r"^(?:table|sheet|表|附表|图表)\s*[\d.:\-_\s]", cand, re.IGNORECASE))
                    )
                    if is_title_cand:
                        table_titles.append(cand)
                        idx -= 1
                        while idx >= 0 and not text_acc[idx].strip():
                            idx -= 1
                    else:
                        break

                if table_titles:
                    text_acc = text_acc[: idx + 1]
                    table_titles.reverse()

            if text_acc:
                t = "\n".join(text_acc).strip()
                if t:
                    blocks.append(("text", t))
                text_acc = []

            header_line = lines[i]
            sep_line = lines[i + 1]
            table_lines = [header_line, sep_line]
            k = i + 2
            while k < n and _is_table_row(lines[k]):
                if k + 1 < n and _is_table_separator(lines[k + 1]):
                    break
                table_lines.append(lines[k])
                k += 1

            if table_titles:
                table_block = "\n\n".join(table_titles) + "\n\n" + "\n".join(table_lines)
            else:
                table_block = "\n".join(table_lines)
            blocks.append(("table", table_block.strip()))
            i = k
        else:
            text_acc.append(lines[i])
            i += 1

    if text_acc:
        t = "\n".join(text_acc).strip()
        if t:
            blocks.append(("text", t))

    return blocks


def _is_kv_table_content(text: str) -> bool:
    """Check if text is a Key-Value folded table representation."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    kv_lines = [ln for ln in lines if ln.startswith("- **") and "**: " in ln]
    if len(kv_lines) < 3:
        return False
    # Must have a table header/row indicator or sheet label, not just generic markdown bullets
    has_table_marker = any(
        bool(_ROW_LABEL_PATTERN.search(ln) or "Sheet:" in ln or "Table:" in ln or ln.startswith("### (Row"))
        for ln in lines[:3]
    )
    return has_table_marker


def _split_kv_table_text(text: str, max_chunk_size: int) -> list[str]:
    """Split a Key-Value folded table entity across chunks, propagating header and row ID."""
    if len(text) <= max_chunk_size:
        return [text]

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    header_line = lines[0] if lines and lines[0].startswith("#") else ""
    kv_lines = lines[1:] if header_line else lines

    chunks: list[str] = []
    sub_lines: list[str] = []
    sub_len = 0
    part_idx = 1
    prefix = header_line

    for eline in kv_lines:
        overhead = len(prefix) + 25 if prefix else 0
        budget = max_chunk_size - overhead

        # Single line exceeds budget: slice value text across bounded parts
        if len(eline) > budget:
            if sub_lines:
                part_header = f"{prefix} (Part {part_idx})" if prefix else ""
                part_str = f"{part_header}\n" + "\n".join(sub_lines) if part_header else "\n".join(sub_lines)
                chunks.append(part_str.strip())
                sub_lines = []
                sub_len = 0
                part_idx += 1

            prefix_tag = eline.split(": ", 1)[0] + ": " if ": " in eline else "- "
            val_text = eline[len(prefix_tag) :]
            avail = max(40, budget - len(prefix_tag) - 10)
            for offset in range(0, len(val_text), avail):
                val_slice = val_text[offset : offset + avail]
                slice_line = f"{prefix_tag}{val_slice}" if offset == 0 else f"{prefix_tag}(cont.) {val_slice}"
                part_header = f"{prefix} (Part {part_idx})" if prefix else ""
                part_str = f"{part_header}\n{slice_line}" if part_header else slice_line
                chunks.append(part_str.strip())
                part_idx += 1
            continue

        if sub_len + len(eline) + 1 > budget and sub_lines:
            part_header = f"{prefix} (Part {part_idx})" if prefix else ""
            part_str = f"{part_header}\n" + "\n".join(sub_lines) if part_header else "\n".join(sub_lines)
            chunks.append(part_str.strip())
            sub_lines = [eline]
            sub_len = len(eline)
            part_idx += 1
        else:
            sub_lines.append(eline)
            sub_len += len(eline) + 1

    if sub_lines:
        part_header = f"{prefix} (Part {part_idx})" if (prefix and part_idx > 1) else prefix
        part_str = f"{part_header}\n" + "\n".join(sub_lines) if part_header else "\n".join(sub_lines)
        chunks.append(part_str.strip())

    return chunks if chunks else [text]


def _is_markdown_table_content(text: str) -> bool:
    """Check if text contains a markdown pipe table or a KV-folded table entity."""
    if _is_kv_table_content(text):
        return True
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for i, line in enumerate(lines):
        if _is_table_row(line) and i + 1 < len(lines) and _is_table_separator(lines[i + 1]):
            return True
    return False


def _split_single_table_block(
    table_text: str,
    max_chunk_size: int,
    row_overlap: int = 1,
    global_row_offset: int = 0,
    global_total_rows: int | None = None,
) -> list[str]:
    """Split a single table block preserving headers, sheet metadata, and row overlap.

    Implements:
    1. Table-RAG (SIGIR 2024): Sliding row window with row_overlap to preserve cross-row context.
    2. TableLlama (NAACL 2024): Adaptive Key-Value folding for ultra-wide rows exceeding chunk thresholds.
    """
    lines = [line.strip() for line in table_text.splitlines() if line.strip()]
    header_idx = -1
    for idx, ln in enumerate(lines):
        if _is_table_row(ln) and idx + 1 < len(lines) and _is_table_separator(lines[idx + 1]):
            header_idx = idx
            break

    if header_idx == -1:
        return [table_text]

    prefix_lines = lines[:header_idx]
    if global_total_rows is None:
        for pl in prefix_lines:
            m = _ROW_LABEL_MATCH.search(pl)
            if m:
                start_row = int(m.group(1))
                global_row_offset = start_row - 1
                global_total_rows = int(m.group(3))
                break

    prefix_str = _clean_prefix(prefix_lines)
    header_line = lines[header_idx]
    sep_line = lines[header_idx + 1]
    data_rows = lines[header_idx + 2 :]
    total_data_rows = len(data_rows)
    display_total_rows = global_total_rows if global_total_rows is not None else total_data_rows

    if total_data_rows == 0:
        return [table_text]

    if len(table_text) <= max_chunk_size and (global_total_rows is None or global_total_rows == total_data_rows):
        return [table_text]

    # Ultra-wide table check: adaptive KV-folding (TableLlama / StructLM NAACL/EMNLP 2024)
    # Check max row length across all rows instead of only checking row 0
    max_row_len = max((len(r) for r in data_rows), default=0)
    if (max_row_len + len(header_line)) > max_chunk_size * 0.75:
        cols = _extract_markdown_cells(header_line)
        entity_records: list[str] = []

        for r_i, r in enumerate(data_rows, start=1):
            vals = _extract_markdown_cells(r)
            vals += [""] * max(0, len(cols) - len(vals))
            entity_lines = [f"- **{col}**: {val}" for col, val in zip(cols, vals, strict=False) if val and col.strip()]
            primary_label = f" - {cols[0]}: {vals[0]}" if cols and vals and vals[0] and cols[0].strip() else ""
            actual_row = global_row_offset + r_i
            row_coord = f"(Row {actual_row} of {display_total_rows}{primary_label})"
            header_prefix = _format_table_title(prefix_str, row_coord)
            full_entity_str = f"{header_prefix}\n" + "\n".join(entity_lines)
            entity_records.append(full_entity_str)

        kv_chunks: list[str] = []
        cur_entities: list[str] = []
        cur_len = 0
        overlap = max(0, min(row_overlap, 2))
        e_idx = 0

        while e_idx < len(entity_records):
            entity_str = entity_records[e_idx]

            # Oversize guard: if a single entity exceeds max_chunk_size, split it with _split_kv_table_text
            if len(entity_str) > max_chunk_size:
                if cur_entities:
                    kv_chunks.append("\n\n".join(cur_entities))
                    cur_entities = []
                    cur_len = 0
                sub_parts = _split_kv_table_text(entity_str, max_chunk_size)
                kv_chunks.extend(sub_parts)
                e_idx += 1
                continue

            cost = len(entity_str) + (2 if cur_entities else 0)
            if cur_len + cost <= max_chunk_size:
                cur_entities.append(entity_str)
                cur_len += cost
                e_idx += 1
            else:
                if cur_entities:
                    kv_chunks.append("\n\n".join(cur_entities))
                    keep_count = min(len(cur_entities) - 1, overlap)
                    if keep_count > 0:
                        cur_entities = cur_entities[-keep_count:]
                        cur_len = sum(len(e) for e in cur_entities) + 2 * (len(cur_entities) - 1)
                    else:
                        cur_entities = []
                        cur_len = 0
                else:
                    cur_entities.append(entity_str)
                    cur_len = len(entity_str)
                    e_idx += 1

        if cur_entities:
            kv_chunks.append("\n\n".join(cur_entities))

        return kv_chunks if kv_chunks else [table_text]

    # Standard sliding window with row overlap (Table-RAG SIGIR 2024)
    header_block = f"{header_line}\n{sep_line}"
    chunks: list[str] = []
    start_idx = 1
    overlap = max(0, min(row_overlap, 3))

    while start_idx <= total_data_rows:
        current_rows: list[str] = []
        end_idx = start_idx - 1
        for r_idx in range(start_idx, total_data_rows + 1):
            cand_rows = current_rows + [data_rows[r_idx - 1]]
            global_s = global_row_offset + start_idx
            global_e = global_row_offset + r_idx
            if global_s == global_e:
                label = f"(Row {global_s} of {display_total_rows})" if display_total_rows > 1 else ""
            else:
                label = f"(Rows {global_s}-{global_e} of {display_total_rows})" if display_total_rows > 1 else ""
            pfx = _format_table_title(prefix_str, label)
            candidate_chunk = (
                f"{pfx}\n\n{header_block}\n" + "\n".join(cand_rows)
                if pfx
                else f"{header_block}\n" + "\n".join(cand_rows)
            )
            if len(candidate_chunk) > max_chunk_size and current_rows:
                break
            current_rows = cand_rows
            end_idx = r_idx

        global_s = global_row_offset + start_idx
        global_e = global_row_offset + end_idx
        if global_s == global_e:
            label = f"(Row {global_s} of {display_total_rows})" if display_total_rows > 1 else ""
        else:
            label = f"(Rows {global_s}-{global_e} of {display_total_rows})" if display_total_rows > 1 else ""
        pfx = _format_table_title(prefix_str, label)
        chunk_content = (
            f"{pfx}\n\n{header_block}\n" + "\n".join(current_rows)
            if pfx
            else f"{header_block}\n" + "\n".join(current_rows)
        )
        chunks.append(chunk_content.strip())
        if end_idx >= total_data_rows:
            break
        next_start_idx = max(start_idx + 1, end_idx - overlap + 1)
        start_idx = next_start_idx

    return chunks if chunks else [table_text]


def _split_markdown_table_text(
    text: str,
    max_chunk_size: int,
    row_overlap: int = 1,
    global_row_offset: int = 0,
    global_total_rows: int | None = None,
) -> list[str] | None:
    """Split markdown text containing one or more tables while preserving headers and surrounding text.

    Returns None if text is not a valid markdown table or does not contain table blocks.
    """
    if not text or not text.strip():
        return None

    if _is_kv_table_content(text):
        return _split_kv_table_text(text, max_chunk_size)

    blocks = _extract_document_blocks(text)
    has_table = any(b_type == "table" for b_type, _ in blocks)
    if not has_table:
        return None

    if len(text) <= max_chunk_size and len(blocks) == 1 and blocks[0][0] == "table" and global_total_rows is None:
        return [text]

    chunks: list[str] = []
    table_block_count = sum(1 for b_type, _ in blocks if b_type == "table")
    first_table_consumed = False

    for b_type, b_content in blocks:
        b_content = b_content.strip()
        if not b_content:
            continue

        if b_type == "table":
            use_offset = 0
            use_total = None
            if global_total_rows is not None:
                if table_block_count == 1 or not first_table_consumed:
                    use_offset = global_row_offset
                    use_total = global_total_rows
                    first_table_consumed = True

            tbl_chunks = _split_single_table_block(
                b_content,
                max_chunk_size=max_chunk_size,
                row_overlap=row_overlap,
                global_row_offset=use_offset,
                global_total_rows=use_total,
            )
            chunks.extend(c for c in tbl_chunks if c.strip())
        else:
            if len(b_content) <= max_chunk_size:
                chunks.append(b_content)
            else:
                sub_splitter = _build_splitter(
                    chunk_size=max_chunk_size,
                    chunk_overlap=max(0, min(max_chunk_size // 5, 100)),
                    separators=get_smart_separators("markdown"),
                )
                sub_chunks = sub_splitter.split_text(b_content)
                chunks.extend(c.strip() for c in sub_chunks if c.strip())

    return chunks if chunks else [text]


def _split_parent(
    doc: Any,
    parent_text: str,
    splitter: Any,
    *,
    base_metadata: dict[str, Any],
    parent_id: str,
    parent_idx: int,
    enhance: bool,
    heading: str | None,
    settings: Any | None = None,
) -> list[Any]:
    """The child chunks of one parent, each carrying its parent linkage."""
    is_table = base_metadata.get("modality") == "table" or _is_markdown_table_content(parent_text)
    chunk_size = int(getattr(splitter, "chunk_size", getattr(splitter, "_chunk_size", 400)))
    row_overlap = getattr(settings, "table_row_overlap", 1) if settings else 1

    parent_offset = 0
    parent_total = None
    m = _ROW_LABEL_MATCH.search(parent_text)
    if m:
        parent_offset = int(m.group(1)) - 1
        parent_total = int(m.group(3))

    table_children = (
        _split_markdown_table_text(
            parent_text,
            chunk_size,
            row_overlap=row_overlap,
            global_row_offset=parent_offset,
            global_total_rows=parent_total,
        )
        if is_table
        else None
    )
    child_texts = table_children if table_children is not None else (splitter.split_text(parent_text) or [parent_text])

    total_children = len(child_texts)
    children: list[Any] = []
    carried = heading

    for child_idx, raw_child in enumerate(child_texts):
        child_text = (raw_child or "").strip()
        if not child_text:
            continue

        scope, carried = _heading_scope(child_text, carried)
        metadata = dict(base_metadata)
        metadata["parent_id"] = parent_id
        metadata["parent_index"] = parent_idx
        metadata["child_index"] = child_idx
        if scope:
            metadata["heading"] = scope

        if _is_markdown_table_content(child_text):
            metadata["modality"] = "table"
        elif base_metadata.get("modality") == "table" and not _is_markdown_table_content(child_text):
            metadata["modality"] = "text"

        if metadata.get("modality") == "table":
            if "table_id" not in metadata:
                metadata["table_id"] = base_metadata.get("table_id") or f"tbl-{parent_id}"
            if "table_columns" not in metadata:
                cols = extract_table_columns(child_text)
                if cols:
                    metadata["table_columns"] = ", ".join(cols)
                elif base_metadata.get("table_columns"):
                    metadata["table_columns"] = base_metadata["table_columns"]
            m_row = _ROW_LABEL_MATCH.search(child_text)
            if m_row:
                s_row = int(m_row.group(1))
                e_row = int(m_row.group(2)) if m_row.group(2) else s_row
                metadata["table_row_range"] = f"{s_row}-{e_row}" if s_row != e_row else str(s_row)
                metadata["total_table_rows"] = int(m_row.group(3))
            elif "table_row_range" not in metadata:
                t_lines = [ln.strip() for ln in child_text.splitlines() if ln.strip()]
                sep_i = -1
                for idx_l, ln in enumerate(t_lines):
                    if _is_table_separator(ln) and idx_l > 0 and _is_table_row(t_lines[idx_l - 1]):
                        sep_i = idx_l
                        break
                if sep_i != -1:
                    d_count = sum(1 for ln in t_lines[sep_i + 1 :] if _is_table_row(ln))
                    if d_count > 0:
                        metadata["table_row_range"] = f"1-{d_count}" if d_count > 1 else "1"
                        metadata["total_table_rows"] = d_count
                elif base_metadata.get("table_row_range"):
                    metadata["table_row_range"] = base_metadata["table_row_range"]
                    if base_metadata.get("total_table_rows"):
                        metadata["total_table_rows"] = base_metadata["total_table_rows"]

        if enhance:
            metadata = enhance_chunk_metadata(
                child_text, metadata, child_idx, total_children, *_neighbours(child_texts, child_idx)
            )

        children.append(_clone_document(doc, text=child_text, metadata=metadata))

    return children


def _splitters(base_metadata: dict[str, Any], settings: Any) -> tuple[Any, Any]:
    """The parent and child splitters for one document, sharing its separators."""
    # 智能选择分隔符
    separators = get_smart_separators(
        base_metadata.get("doc_type") or base_metadata.get("file_type"),
        base_metadata.get("language", "mixed"),
    )
    return (
        _build_splitter(
            chunk_size=settings.parent_chunk_size,
            chunk_overlap=settings.parent_chunk_overlap,
            separators=separators,
        ),
        _build_splitter(
            chunk_size=settings.child_chunk_size,
            chunk_overlap=settings.child_chunk_overlap,
            separators=separators,
        ),
    )


def _document_identity(base_metadata: dict[str, Any]) -> str:
    """What a parent id is made stable against, or "" if there is nothing.

    `document_id` plus `version` where both are present, because that pair
    survives a file being moved; the source path otherwise.
    """
    document_id = str(base_metadata.get("document_id", "") or "")
    version = str(base_metadata.get("version", "") or "")
    if document_id and version:
        return f"{document_id}|v{version}"
    return str(base_metadata.get("source", "") or "")


def _split_document(
    doc: Any,
    doc_idx: int,
    *,
    settings: Any,
    enhance: bool,
) -> tuple[list[Any], list[dict[str, Any]]]:
    """One document's child chunks and parent records, in order.

    Note that a blank chunk is skipped but still *counts*: `child_idx`,
    `parent_idx` and the totals handed to `enhance_chunk_metadata` are positions
    in the splitter's output, not in the kept subset. Renumbering them would
    change what "chunk 3 of 7" means to every consumer of that metadata.
    """
    base_metadata = dict(getattr(doc, "metadata", {}) or {})
    raw_text = str(getattr(doc, "page_content", "") or "").strip()
    if not raw_text:
        return [], []

    is_table = base_metadata.get("modality") == "table" or _is_markdown_table_content(raw_text)
    row_overlap = getattr(settings, "table_row_overlap", 1)
    table_parents = (
        _split_markdown_table_text(raw_text, settings.parent_chunk_size, row_overlap=row_overlap) if is_table else None
    )

    parent_splitter, child_splitter = _splitters(base_metadata, settings)
    identity = _document_identity(base_metadata)

    parent_texts = table_parents if table_parents is not None else (parent_splitter.split_text(raw_text) or [raw_text])
    total_parents = len(parent_texts)
    children: list[Any] = []
    records: list[dict[str, Any]] = []
    carried_heading: str | None = None

    for parent_idx, raw_parent in enumerate(parent_texts):
        parent_text = (raw_parent or "").strip()
        if not parent_text:
            continue

        scope, carried_heading = _heading_scope(parent_text, carried_heading)
        parent_id = _parent_id(identity, doc_idx, parent_idx, parent_text)
        parent_meta = dict(base_metadata)
        parent_meta.update({"parent_id": parent_id, "parent_index": parent_idx})
        if scope:
            parent_meta["heading"] = scope
        if _is_markdown_table_content(parent_text):
            parent_meta["modality"] = "table"
        elif base_metadata.get("modality") == "table" and not _is_markdown_table_content(parent_text):
            parent_meta["modality"] = "text"

        if parent_meta.get("modality") == "table":
            if "table_id" not in parent_meta:
                parent_meta["table_id"] = base_metadata.get("table_id") or f"tbl-{parent_id}"
            if "table_columns" not in parent_meta:
                cols = extract_table_columns(parent_text)
                if cols:
                    parent_meta["table_columns"] = ", ".join(cols)
                elif base_metadata.get("table_columns"):
                    parent_meta["table_columns"] = base_metadata["table_columns"]
            m_row = _ROW_LABEL_MATCH.search(parent_text)
            if m_row:
                s_row = int(m_row.group(1))
                e_row = int(m_row.group(2)) if m_row.group(2) else s_row
                parent_meta["table_row_range"] = f"{s_row}-{e_row}" if s_row != e_row else str(s_row)
                parent_meta["total_table_rows"] = int(m_row.group(3))
            elif "table_row_range" not in parent_meta:
                t_lines = [ln.strip() for ln in parent_text.splitlines() if ln.strip()]
                sep_i = -1
                for idx_l, ln in enumerate(t_lines):
                    if _is_table_separator(ln) and idx_l > 0 and _is_table_row(t_lines[idx_l - 1]):
                        sep_i = idx_l
                        break
                if sep_i != -1:
                    d_count = sum(1 for ln in t_lines[sep_i + 1 :] if _is_table_row(ln))
                    if d_count > 0:
                        parent_meta["table_row_range"] = f"1-{d_count}" if d_count > 1 else "1"
                        parent_meta["total_table_rows"] = d_count
                elif base_metadata.get("table_row_range"):
                    parent_meta["table_row_range"] = base_metadata["table_row_range"]
                    if base_metadata.get("total_table_rows"):
                        parent_meta["total_table_rows"] = base_metadata["total_table_rows"]

        if enhance:
            parent_meta = enhance_chunk_metadata(
                parent_text, parent_meta, parent_idx, total_parents, *_neighbours(parent_texts, parent_idx)
            )

        records.append({"id": parent_id, "text": parent_text, "metadata": parent_meta})
        children.extend(
            _split_parent(
                doc,
                parent_text,
                child_splitter,
                base_metadata=parent_meta,
                parent_id=parent_id,
                parent_idx=parent_idx,
                enhance=enhance,
                heading=scope,
                settings=settings,
            )
        )

    return children, records


def split_documents_enhanced(
    documents: list[Any],
    enable_metadata_enhancement: bool = True,
) -> tuple[list[Any], list[dict[str, Any]]]:
    """
    Enhanced document splitting with intelligent classification and metadata enhancement

    Args:
        documents: List of documents
        enable_metadata_enhancement: Enable metadata enhancement, which is also
            what performs chunk classification -- `enhance_chunk_metadata` calls
            `classify_chunk_type`. There used to be a separate
            `enable_classification` parameter here, documented as "Enable chunk
            classification" and read by nothing: passing False left classification
            running, and only this switch ever turned it off.

    Returns:
        (child_chunks, parent_records)
    """
    settings = get_settings()
    child_chunks: list[Any] = []
    parent_records: list[dict[str, Any]] = []

    for doc_idx, doc in enumerate(documents):
        children, records = _split_document(doc, doc_idx, settings=settings, enhance=enable_metadata_enhancement)
        child_chunks.extend(children)
        parent_records.extend(records)

    return child_chunks, parent_records


def split_documents(documents: list[Any]) -> tuple[list[Any], list[dict[str, Any]]]:
    """Backward compatible document splitting."""
    return split_documents_enhanced(documents, enable_metadata_enhancement=True)
