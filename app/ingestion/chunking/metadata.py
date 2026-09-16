"""Canonical chunk metadata classification and enrichment."""

from __future__ import annotations

import re
from typing import Any

from .classification import ChunkType, classify_chunk_type

# One definition of what a URL looks like. There were two: a substring test
# for the two scheme literals here, and this pattern in extract_entities, so a
# chunk could report has_url=False and still yield a URL. Case-insensitive
# because both spellings occur in real documents and neither form caught it.
_URL = re.compile(r"https?://\S+", re.IGNORECASE)

# ============================================================================
# 元数据增强
# ============================================================================


_PIPE_TABLE_SEP = re.compile(r"^\|?(:?-+:?\|)+:?-+:?\|?$")
_KV_ROW_PATTERN = re.compile(r"^-\s+\*\*([^*]+)\*\*:")


def _extract_pipe_table_columns(lines: list[str]) -> list[str] | None:
    for idx, line in enumerate(lines):
        if idx + 1 < len(lines) and "|" in line:
            sep = lines[idx + 1].strip().replace(" ", "")
            if bool(sep) and bool(_PIPE_TABLE_SEP.match(sep)):
                raw_cells = [c.strip().replace(r"\|", "|") for c in re.split(r"(?<!\\)\|", line.strip("|"))]
                meaningful = [c for c in raw_cells if c and not re.match(r"^(?:column|col)_\d+$", c, re.IGNORECASE)]
                return meaningful if meaningful else [c for c in raw_cells if c]
    return None


def _extract_kv_columns(lines: list[str]) -> list[str]:
    kv_cols: list[str] = []
    for line in lines:
        m = _KV_ROW_PATTERN.match(line)
        if m:
            k = m.group(1).strip()
            if k and k not in kv_cols:
                kv_cols.append(k)
    return kv_cols


def extract_table_columns(text: str) -> list[str]:
    """Extract table column names from markdown pipe tables or KV-folded entity blocks."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    pipe_cols = _extract_pipe_table_columns(lines)
    if pipe_cols is not None:
        return pipe_cols
    return _extract_kv_columns(lines)


def _enrich_table_metadata(metadata: dict[str, Any], chunk_type: str, chunk_text: str) -> None:
    if (chunk_type == "table" or metadata.get("modality") == "table") and not metadata.get("table_columns"):
        cols = extract_table_columns(chunk_text)
        if cols:
            metadata["table_columns"] = ", ".join(cols)


def _populate_semantic_and_context_features(
    metadata: dict[str, Any],
    chunk_text: str,
    chunk_index: int,
    total_chunks: int,
    prev_chunk_text: str | None,
    next_chunk_text: str | None,
) -> None:
    metadata["has_question"] = "?" in chunk_text or "？" in chunk_text
    metadata["has_code"] = any(marker in chunk_text for marker in ["```", "def ", "class ", "function"])
    metadata["has_url"] = bool(_URL.search(chunk_text))
    metadata["has_email"] = "@" in chunk_text and "." in chunk_text

    if prev_chunk_text:
        metadata["prev_chunk_preview"] = (
            prev_chunk_text[:100] + "..." if len(prev_chunk_text) > 100 else prev_chunk_text
        )
    if next_chunk_text:
        metadata["next_chunk_preview"] = (
            next_chunk_text[:100] + "..." if len(next_chunk_text) > 100 else next_chunk_text
        )

    if chunk_index == 0:
        metadata["position"] = "start"
    elif chunk_index == total_chunks - 1:
        metadata["position"] = "end"
    else:
        metadata["position"] = "middle"


def enhance_chunk_metadata(
    chunk_text: str,
    base_metadata: dict[str, Any],
    chunk_index: int,
    total_chunks: int,
    prev_chunk_text: str | None = None,
    next_chunk_text: str | None = None,
) -> dict[str, Any]:
    """
    Enhance chunk metadata with classification and context information

    Args:
        chunk_text: chunk text
        base_metadata: base metadata
        chunk_index: chunk index
        total_chunks: total chunks
        prev_chunk_text: previous chunk text (optional)
        next_chunk_text: next chunk text (optional)

    Returns:
        Enhanced metadata
    """
    metadata = dict(base_metadata)

    # Chunk基本信息
    metadata["chunk_index"] = chunk_index
    metadata["total_chunks"] = total_chunks
    # Multilingual word/character count (supports both English words and CJK characters)
    zh_chars = len(re.findall(r"[\u4e00-\u9fa5]", chunk_text))
    en_words = len(re.findall(r"\b\w+\b", chunk_text))
    metadata["word_count"] = zh_chars + en_words if zh_chars > 0 else len(chunk_text.split())

    # Chunk类型分类
    chunk_type = classify_chunk_type(chunk_text, metadata)
    metadata["chunk_type"] = chunk_type

    # 提取关键信息
    keywords = extract_keywords(chunk_text)
    if keywords:
        metadata["keywords"] = keywords[:10]  # 最多10个关键词

    # 实体识别（简化版）
    entities = extract_entities(chunk_text)
    if entities:
        metadata["entities"] = entities

    # 结构化表格元数据提取
    _enrich_table_metadata(metadata, chunk_type, chunk_text)

    # 语义与上下文位置特征
    _populate_semantic_and_context_features(
        metadata, chunk_text, chunk_index, total_chunks, prev_chunk_text, next_chunk_text
    )

    # 重要性评分（简单启发式）
    metadata["importance_score"] = calculate_importance_score(chunk_text, chunk_type, metadata)

    return metadata


try:
    import jieba  # type: ignore
except ImportError:
    jieba = None


def extract_keywords(text: str, top_n: int = 10) -> list[str]:
    """Extract keywords with dual support for Chinese (via jieba/bigrams) and English.

    Args:
        text: Text content
        top_n: Return top N keywords

    Returns:
        List of keywords
    """
    stopwords = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "as",
        "is",
        "are",
        "was",
        "were",
        "this",
        "that",
        "these",
        "those",
        "sheet",
        "sheets",
        "table",
        "tables",
        "row",
        "rows",
        "col",
        "cols",
        "column",
        "columns",
        "part",
        "total",
        "是",
        "的",
        "了",
        "在",
        "有",
        "和",
        "与",
        "及",
        "等",
        "中",
        "将",
        "可以",
        "进行",
        "对于",
        "通过",
        "一个",
        "没有",
        "我们",
        "他们",
    }

    candidates: list[str] = []

    # Chinese keyword segmentation
    if re.search(r"[\u4e00-\u9fa5]", text):
        if jieba is not None:
            zh_tokens = [
                w.strip()
                for w in jieba.cut(text)
                if len(w.strip()) >= 2 and w.strip() not in stopwords and re.match(r"^[\u4e00-\u9fa5]+$", w.strip())
            ]
            candidates.extend(zh_tokens)
        else:
            zh_tokens = [w for w in re.findall(r"[\u4e00-\u9fa5]{2,4}", text) if w not in stopwords]
            candidates.extend(zh_tokens)

    # English / alphanumeric keywords (excluding structural placeholders like column_1, row_2)
    en_tokens = [
        w.lower()
        for w in re.findall(r"\b\w{3,}\b", text)
        if w.lower() not in stopwords and not re.match(r"^(?:column|col|row|sheet|part|table)_\d+$", w.lower())
    ]
    candidates.extend(en_tokens)

    word_freq: dict[str, int] = {}
    for word in candidates:
        word_freq[word] = word_freq.get(word, 0) + 1

    sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in sorted_keywords[:top_n]]


def _first_distinct(values: list[str], limit: int | None = None) -> list[str]:
    """Distinct values in order of first appearance.

    Every one of these was `list(set(values))`, and set iteration order over
    strings depends on `PYTHONHASHSEED`, which Python randomises per process. For
    `acronyms`, `numbers` and `urls` that is not cosmetic: all three are truncated,
    so *which* five acronyms reached a chunk's metadata changed between ingests of
    the same unchanged document. Order of appearance also makes the truncation
    mean something -- "the first five in this chunk" rather than "an arbitrary
    five".

    Found on 2026-09-06 while characterising `split_documents_enhanced` for a
    refactor: two runs of the unmodified splitter produced different metadata.
    """
    distinct = list(dict.fromkeys(values))
    return distinct if limit is None else distinct[:limit]


def extract_entities(text: str) -> dict[str, list[str]]:
    """
    Simplified entity recognition (rule-based)

    Args:
        text: Text content

    Returns:
        Entity dictionary {type: [entity list]}
    """
    entities: dict[str, list[str]] = {}

    # 技术术语（大写缩写）
    acronyms = re.findall(r"\b[A-Z]{2,10}\b", text)
    if acronyms:
        entities["acronyms"] = _first_distinct(acronyms, 5)

    # 数字（版本号、ID等，过滤掉行号坐标标记如 (Rows 1-20 of 50)）
    # What the lazy `.*?` meant -- up to the first ")" on the line -- without a
    # class that also matches digits sitting next to `\d+` and competing with it
    # for the same characters (python:S8786). The label's tail must start with a
    # non-digit, which `\d+` being greedy made true of every match anyway.
    cleaned_for_numbers = re.sub(
        r"\(Rows?\s+\d+(?:-\d+)?\s+of\s+\d+(?:[^)\d\n][^)\n]*)?\)", " ", text, flags=re.IGNORECASE
    )
    numbers = re.findall(r"\b\d+(?:\.\d+)*\b", cleaned_for_numbers)
    if numbers:
        entities["numbers"] = _first_distinct(numbers, 5)

    # IP地址
    ips = re.findall(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", text)
    if ips:
        entities["ip_addresses"] = _first_distinct(ips)

    # 邮箱
    emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text)
    if emails:
        entities["emails"] = _first_distinct(emails)

    # URL
    urls = _URL.findall(text)
    if urls:
        entities["urls"] = _first_distinct(urls, 3)

    return entities


def calculate_importance_score(text: str, chunk_type: ChunkType, metadata: dict[str, Any]) -> float:
    """
    Calculate chunk importance score (0.0-1.0)

    Args:
        text: Chunk text
        chunk_type: Chunk type
        metadata: Metadata

    Returns:
        Importance score
    """
    # 类型加权（表格在企业业务数据中包含高密度关键事实，给予高基础权重 0.85）
    type_weights = {
        "heading": 0.9,
        "table": 0.85,
        "definition": 0.8,
        "procedure": 0.8,
        "code": 0.6,
        "list": 0.6,
        "quote": 0.5,
        "paragraph": 0.5,
        "metadata": 0.3,
        "mixed": 0.5,
    }
    score = type_weights.get(chunk_type, 0.5)

    # 位置加权（开头和结尾更重要）
    if metadata.get("position") == "start":
        score += 0.1
    elif metadata.get("position") == "end":
        score += 0.05

    # 长度调整（太短或太长都降低分数）
    chunk_length = len(text)
    if chunk_length < 50:
        score -= 0.1
    elif chunk_length > 2000:
        score -= 0.05
    elif 200 <= chunk_length <= 800:
        score += 0.05  # 理想长度

    # 包含关键元素加分
    if metadata.get("has_code"):
        score += 0.05
    if metadata.get("keywords") and len(metadata["keywords"]) >= 3:
        score += 0.05
    if metadata.get("entities"):
        score += 0.05
    # 表格结构化元数据或高密度数值实体加分
    num_entities = metadata.get("entities", {}).get("numbers", []) if isinstance(metadata.get("entities"), dict) else []
    if metadata.get("table_columns") or len(num_entities) >= 3:
        score += 0.05

    # 限制在0-1范围
    return max(0.0, min(1.0, score))
