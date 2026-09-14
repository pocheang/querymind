"""
智能Chunk切分和分类系统 (Intelligent Chunk Splitting & Classification)

优化目标：
1. 语义完整性 - 保持段落/主题完整
2. 元数据增强 - 添加分类和上下文信息
3. 检索优化 - 让agent更容易找到相关内容
4. 结构感知 - 识别文档结构（标题、列表、表格等）

核心改进：
- 智能分隔符：根据文档类型自适应
- 语义边界检测：在自然语义边界切分
- Chunk分类：自动分类chunk类型
- 元数据增强：添加丰富的检索元数据
- 上下文窗口：保留前后文信息
"""

from __future__ import annotations

import re
from typing import Any, Literal

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    RecursiveCharacterTextSplitter = None  # type: ignore[assignment]


# ============================================================================
# Chunk类型分类
# ============================================================================

ChunkType = Literal[
    "heading",  # 标题
    "paragraph",  # 段落
    "list",  # 列表
    "table",  # 表格
    "code",  # 代码块
    "quote",  # 引用
    "definition",  # 定义/术语
    "procedure",  # 步骤/流程
    "metadata",  # 元数据信息
    "mixed",  # 混合内容
]


def classify_chunk_type(text: str, metadata: dict[str, Any]) -> ChunkType:
    """
    智能分类chunk类型

    Args:
        text: chunk文本内容
        metadata: chunk元数据

    Returns:
        ChunkType: chunk类型
    """
    # `text.lower().strip()` stood here with its result discarded, so the
    # normalization never happened -- every check below reads the raw `text`.
    # Deleted rather than turned into an assignment: making it one would change
    # what every document classifies as, which is a decision, not a cleanup.

    # 优先检查表格和代码块（防止以标题开头的表格块/代码块被错误识别为标题）
    if _is_table(text, metadata):
        return "table"

    if _is_code_block(text):
        return "code"

    # 检查标题模式
    if _is_heading(text, metadata):
        return "heading"

    # 检查步骤/流程（必须优先于通用列表，防止有序操作步骤被误判为普通列表）
    if _is_procedure(text):
        return "procedure"

    # 检查列表
    if _is_list(text):
        return "list"

    # 检查引用
    if _is_quote(text):
        return "quote"

    # 检查定义/术语
    if _is_definition(text):
        return "definition"

    # 检查元数据信息（文档属性、标签等）
    if _is_metadata_info(text):
        return "metadata"

    # 默认为段落
    return "paragraph"


def _is_heading(text: str, metadata: dict[str, Any]) -> bool:
    """检查是否为标题"""
    if not text or not text.strip():
        return False

    # 检查元数据中的标题标记
    if metadata.get("is_heading") or metadata.get("heading_level"):
        return True

    stripped = text.strip()

    # Markdown标题（仅对单行或简短的纯标题生效）
    if stripped.startswith("#"):
        lines = stripped.splitlines()
        if len(lines) == 1:
            return True
        if len(lines) <= 2 and len(stripped) < 120:
            return True

    # 显式章节结构标记（如“第一章 引言”、“Chapter 1: Overview”）
    if re.match(r"^(?:第[一二三四五六七八九十\d]+[章节部分篇条]|Chapter\s+\d+|Section\s+\d+)", stripped, re.IGNORECASE):
        lines = stripped.splitlines()
        if len(lines) <= 2 and len(stripped) < 100:
            return True

    # 单行无终结标点的简短独立标题（排除含逗号、分号的多分句文本）
    lines = stripped.splitlines()
    if len(lines) == 1 and len(stripped) < 60:
        if not stripped.rstrip().endswith((".", "。", "!", "！", "?", "？", ":", "：", ",", "，", ";", "；")):
            if not any(p in stripped for p in (",", "，", ";", "；")):
                words = stripped.split()
                if 1 <= len(words) <= 7 and (stripped.isupper() or all(w[0].isupper() for w in words if w)):
                    return True

    return False


def _is_table(text: str, metadata: dict[str, Any]) -> bool:
    """检查是否为表格"""
    if not text or not text.strip():
        return False

    # 元数据标记
    if metadata.get("is_table") or metadata.get("table_index") is not None or metadata.get("modality") == "table":
        return True

    # HTML表格
    lowered = text.lower()
    if "<table" in lowered or "<tr>" in lowered:
        return True

    # Markdown Pipe 表格结构检测 (任意位置包含表头 + 分隔行)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for i, line in enumerate(lines):
        if line.startswith("|") and line.endswith("|") and line.count("|") >= 2:
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if next_line.startswith("|") and re.match(r"^\|(?:\s*:?-[-:]*\s*\|)+$", next_line):
                    return True

    # KV折叠表格结构检测
    kv_lines = [ln for ln in lines if ln.startswith("- **") and "**: " in ln]
    if len(kv_lines) >= 2 and any("(Row " in ln or "Sheet:" in ln or "Table:" in ln for ln in lines[:3]):
        return True

    return False


def _is_code_block(text: str) -> bool:
    """检查是否为代码块"""
    # 代码块标记
    if text.startswith(("```", "    ")):
        return True

    # 包含大量编程关键字
    code_keywords = ["def ", "class ", "import ", "function", "var ", "const ", "let ", "return", "if (", "for ("]
    keyword_count = sum(1 for kw in code_keywords if kw in text)
    if keyword_count >= 2:
        return True

    # 包含大量特殊字符
    special_chars = ["{", "}", "(", ")", ";", "=>", "->"]
    char_count = sum(text.count(char) for char in special_chars)
    if char_count >= 5:
        return True

    return False


def _is_list(text: str) -> bool:
    """检查是否为列表"""
    lines = text.strip().split("\n")
    if len(lines) < 2:
        return False

    # 数字列表: 1. 2. 3.
    numbered_pattern = re.compile(r"^\s*(\d+\.|\d+\)|\(\d+\))")
    numbered_count = sum(1 for line in lines if numbered_pattern.match(line))
    if numbered_count >= 2:
        return True

    # 项目符号列表: - * •
    bullet_pattern = re.compile(r"^\s*[-*•·]")
    bullet_count = sum(1 for line in lines if bullet_pattern.match(line))
    if bullet_count >= 2:
        return True

    # 字母列表: a) b) c)
    alpha_pattern = re.compile(r"^\s*[a-z]\)")
    alpha_count = sum(1 for line in lines if alpha_pattern.match(line))
    if alpha_count >= 2:
        return True

    return False


def _is_quote(text: str) -> bool:
    """检查是否为引用"""
    # 引用标记
    if text.startswith((">", "「", '"')):
        return True

    # 包含引用关键词
    quote_patterns = ["according to", "as stated", "引用", "如下所述", "根据"]
    if any(pattern in text.lower() for pattern in quote_patterns):
        return True

    return False


def _is_definition(text: str) -> bool:
    """检查是否为定义/术语"""
    # 定义模式: "X是...", "X: ...", "X - ..."
    definition_patterns = [
        r"^[A-Z][A-Za-z\s]+(?:is|means|refers to|defined as)",
        r"^[一-龥]+[：:]\s*.+",
        r"^[一-龥]+是指",
        r"^[一-龥]+指的是",
    ]

    for pattern in definition_patterns:
        if re.match(pattern, text.strip()):
            return True

    # 包含术语标记
    if "(acronym)" in text.lower() or "缩写" in text or "全称" in text:
        return True

    return False


def _is_procedure(text: str) -> bool:
    """检查是否为步骤/流程"""
    # 步骤标记
    step_patterns = [
        r"(?:step|步骤)\s*\d+",
        r"第[一二三四五六七八九十\d]+步",
        r"^\s*\d+\.\s*(?:打开|运行|点击|配置|设置|启动|停止|创建|修改|删除|执行|输入|选择|检查|验证|download|install|configure|run|click|open|start|stop|create|update|delete|verify|check|please|first|then|ensure)\b",
    ]

    for pattern in step_patterns:
        if re.search(pattern, text.lower(), flags=re.MULTILINE):
            return True

    # 包含流程关键词
    procedure_keywords = ["首先", "然后", "接下来", "最后", "finally", "next", "after that"]
    keyword_count = sum(1 for kw in procedure_keywords if kw in text.lower())
    if keyword_count >= 2:
        return True

    return False


def _is_metadata_info(text: str) -> bool:
    """检查是否为元数据信息"""
    # 元数据模式
    metadata_patterns = [
        r"(?:author|date|version|status|category|tag|keyword)s?:",
        r"(?:作者|日期|版本|状态|分类|标签|关键词)[：:]",
    ]

    for pattern in metadata_patterns:
        if re.search(pattern, text.lower()):
            return True

    return False
