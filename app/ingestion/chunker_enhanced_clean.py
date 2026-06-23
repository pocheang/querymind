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

import hashlib
import re
import uuid
from typing import Any, Literal

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    RecursiveCharacterTextSplitter = None  # type: ignore[assignment]

from app.core.config import get_settings


# ============================================================================
# Chunk类型分类
# ============================================================================

ChunkType = Literal[
    "heading",        # 标题
    "paragraph",      # 段落
    "list",          # 列表
    "table",         # 表格
    "code",          # 代码块
    "quote",         # 引用
    "definition",    # 定义/术语
    "procedure",     # 步骤/流程
    "metadata",      # 元数据信息
    "mixed",         # 混合内容
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
    text_lower = text.lower().strip()

    # 检查标题模式
    if _is_heading(text, metadata):
        return "heading"

    # 检查代码块
    if _is_code_block(text):
        return "code"

    # 检查表格
    if _is_table(text, metadata):
        return "table"

    # 检查列表
    if _is_list(text):
        return "list"

    # 检查引用
    if _is_quote(text):
        return "quote"

    # 检查定义/术语
    if _is_definition(text):
        return "definition"

    # 检查步骤/流程
    if _is_procedure(text):
        return "procedure"

    # 检查元数据信息（文档属性、标签等）
    if _is_metadata_info(text):
        return "metadata"

    # 默认为段落
    return "paragraph"


def _is_heading(text: str, metadata: dict[str, Any]) -> bool:
    """检查是否为标题"""
    # 检查元数据中的标题标记
    if metadata.get("is_heading") or metadata.get("heading_level"):
        return True

    # 短文本 + 行末无标点 + 大写开头
    if len(text) < 100 and not text.rstrip().endswith((".", "。", "!", "！", "?", "？")):
        if text[0].isupper() or any(char in text for char in "第一二三四五六七八九十"):
            return True

    # Markdown标题
    if text.startswith("#"):
        return True

    return False


def _is_code_block(text: str) -> bool:
    """检查是否为代码块"""
    # 代码块标记
    if text.startswith("```") or text.startswith("    "):
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


def _is_table(text: str, metadata: dict[str, Any]) -> bool:
    """检查是否为表格"""
    # 元数据标记
    if metadata.get("is_table") or metadata.get("table_index") is not None:
        return True

    # 包含表格分隔符
    if "|" in text and text.count("|") >= 4:
        lines = text.split("\n")
        if len(lines) >= 2 and all("|" in line for line in lines[:3]):
            return True

    # HTML表格
    if "<table" in text.lower() or "<tr>" in text.lower():
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
    if text.startswith(">") or text.startswith("「") or text.startswith("""):
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
        r"第[一二三四五六七八九十]+步",
        r"^\d+\.\s+\w+",  # 1. Do something
    ]

    for pattern in step_patterns:
        if re.search(pattern, text.lower()):
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


# ============================================================================
# 元数据增强
# ============================================================================

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
    metadata["chunk_length"] = len(chunk_text)
    metadata["word_count"] = len(chunk_text.split())

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

    # 语义特征
    metadata["has_question"] = "?" in chunk_text or "？" in chunk_text
    metadata["has_code"] = any(marker in chunk_text for marker in ["```", "def ", "class ", "function"])
    metadata["has_url"] = "http://" in chunk_text or "https://" in chunk_text
    metadata["has_email"] = "@" in chunk_text and "." in chunk_text

    # 上下文信息
    if prev_chunk_text:
        metadata["prev_chunk_preview"] = prev_chunk_text[:100] + "..." if len(prev_chunk_text) > 100 else prev_chunk_text

    if next_chunk_text:
        metadata["next_chunk_preview"] = next_chunk_text[:100] + "..." if len(next_chunk_text) > 100 else next_chunk_text

    # 位置信息
    if chunk_index == 0:
        metadata["position"] = "start"
    elif chunk_index == total_chunks - 1:
        metadata["position"] = "end"
    else:
        metadata["position"] = "middle"

    # 重要性评分（简单启发式）
    metadata["importance_score"] = calculate_importance_score(chunk_text, chunk_type, metadata)

    return metadata


def extract_keywords(text: str, top_n: int = 10) -> list[str]:
    """
    Extract keywords (simplified version based on word frequency and length)

    Args:
        text: Text content
        top_n: Return top N keywords

    Returns:
        List of keywords
    """
    # 移除标点和特殊字符
    clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
    words = clean_text.split()

    # 停用词（简化版）
    stopwords = set([
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by",
        "是", "的", "了", "在", "有", "和", "与", "及", "等", "中", "将", "可以", "进行"
    ])

    # 过滤停用词和短词
    keywords = [w for w in words if len(w) > 3 and w not in stopwords]

    # 词频统计
    word_freq: dict[str, int] = {}
    for word in keywords:
        word_freq[word] = word_freq.get(word, 0) + 1

    # 按频率排序
    sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)

    return [word for word, freq in sorted_keywords[:top_n]]


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
    acronyms = re.findall(r'\b[A-Z]{2,10}\b', text)
    if acronyms:
        entities["acronyms"] = list(set(acronyms))[:5]

    # 数字（版本号、ID等）
    numbers = re.findall(r'\b\d+(?:\.\d+)*\b', text)
    if numbers:
        entities["numbers"] = list(set(numbers))[:5]

    # IP地址
    ips = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', text)
    if ips:
        entities["ip_addresses"] = list(set(ips))

    # 邮箱
    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if emails:
        entities["emails"] = list(set(emails))

    # URL
    urls = re.findall(r'https?://[^\s]+', text)
    if urls:
        entities["urls"] = list(set(urls))[:3]

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
    score = 0.5  # 基础分数

    # 类型加权
    type_weights = {
        "heading": 0.9,
        "definition": 0.8,
        "procedure": 0.8,
        "table": 0.7,
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

    # 限制在0-1范围
    return max(0.0, min(1.0, score))


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
            "\n## ",      # 二级标题
            "\n### ",     # 三级标题
            "\n\n",       # 段落
            "\n- ",       # 列表项
            "\n* ",       # 列表项
            "\n1. ",      # 数字列表
            "\n",         # 换行
            ". ",         # 句子
            " ",          # 空格
            "",           # 字符
        ]

    # 代码文档
    if doc_type == "code":
        return [
            "\nclass ",   # 类定义
            "\ndef ",     # 函数定义
            "\n\n",       # 空行
            "\n",         # 换行
            ";",          # 语句结束
            " ",          # 空格
            "",           # 字符
        ]

    # PDF文档（可能包含多列）
    if doc_type == "pdf":
        if language == "zh":
            return [
                "\n\n",   # 段落
                "。\n",   # 句号+换行
                "。",     # 句号
                "；",     # 分号
                "，",     # 逗号
                "\n",     # 换行
                " ",      # 空格
                "",       # 字符
            ]
        else:
            return [
                "\n\n",   # 段落
                ". \n",   # 句号+换行
                ". ",     # 句号
                "; ",     # 分号
                ", ",     # 逗号
                "\n",     # 换行
                " ",      # 空格
                "",       # 字符
            ]

    # 默认：混合语言
    return [
        "\n\n",       # 段落
        "。\n",       # 中文句号+换行
        ". \n",       # 英文句号+换行
        "。",         # 中文句号
        ". ",         # 英文句号
        "！",         # 感叹号
        "？",         # 问号
        "；",         # 分号
        "\n",         # 换行
        " ",          # 空格
        "",           # 字符
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


def split_documents_enhanced(
    documents: list[Any],
    enable_classification: bool = True,
    enable_metadata_enhancement: bool = True,
) -> tuple[list[Any], list[dict[str, Any]]]:
    """
    Enhanced document splitting with intelligent classification and metadata enhancement

    Args:
        documents: List of documents
        enable_classification: Enable chunk classification
        enable_metadata_enhancement: Enable metadata enhancement

    Returns:
        (child_chunks, parent_records)
    """
    settings = get_settings()

    child_chunks = []
    parent_records: list[dict[str, Any]] = []

    for doc_idx, doc in enumerate(documents):
        base_metadata = dict(getattr(doc, "metadata", {}) or {})
        raw_text = str(getattr(doc, "page_content", "") or "").strip()
        if not raw_text:
            continue

        source = str(base_metadata.get("source", "") or "")
        doc_type = base_metadata.get("doc_type") or base_metadata.get("file_type")
        language = base_metadata.get("language", "mixed")

        # 智能选择分隔符
        separators = get_smart_separators(doc_type, language)

        parent_splitter = _build_splitter(
            chunk_size=settings.parent_chunk_size,
            chunk_overlap=settings.parent_chunk_overlap,
            separators=separators,
        )
        child_splitter = _build_splitter(
            chunk_size=settings.child_chunk_size,
            chunk_overlap=settings.child_chunk_overlap,
            separators=separators,
        )

        parent_texts = parent_splitter.split_text(raw_text) or [raw_text]
        total_parents = len(parent_texts)

        for parent_idx, parent_text in enumerate(parent_texts):
            parent_text = (parent_text or "").strip()
            if not parent_text:
                continue

            # 生成parent ID
            if source:
                text_hash = hashlib.sha1(parent_text.encode("utf-8")).hexdigest()[:12]
                parent_seed = f"{source}|{doc_idx}|{parent_idx}|{text_hash}"
                parent_id = f"parent-{hashlib.sha1(parent_seed.encode('utf-8')).hexdigest()[:16]}"
            else:
                parent_id = f"parent-{doc_idx}-{parent_idx}-{uuid.uuid4().hex[:8]}"

            parent_meta = dict(base_metadata)
            parent_meta.update({"parent_id": parent_id, "parent_index": parent_idx})

            # Parent元数据增强
            if enable_metadata_enhancement:
                prev_parent = parent_texts[parent_idx - 1] if parent_idx > 0 else None
                next_parent = parent_texts[parent_idx + 1] if parent_idx < total_parents - 1 else None
                parent_meta = enhance_chunk_metadata(
                    parent_text, parent_meta, parent_idx, total_parents, prev_parent, next_parent
                )

            parent_records.append({"id": parent_id, "text": parent_text, "metadata": parent_meta})

            # 切分子chunks
            child_texts = child_splitter.split_text(parent_text) or [parent_text]
            total_children = len(child_texts)

            for child_idx, child_text in enumerate(child_texts):
                child_text = (child_text or "").strip()
                if not child_text:
                    continue

                metadata = dict(base_metadata)
                metadata["parent_id"] = parent_id
                metadata["parent_index"] = parent_idx
                metadata["child_index"] = child_idx

                # Child元数据增强
                if enable_metadata_enhancement:
                    prev_child = child_texts[child_idx - 1] if child_idx > 0 else None
                    next_child = child_texts[child_idx + 1] if child_idx < total_children - 1 else None
                    metadata = enhance_chunk_metadata(
                        child_text, metadata, child_idx, total_children, prev_child, next_child
                    )

                child_chunks.append(_clone_document(doc, text=child_text, metadata=metadata))

    return child_chunks, parent_records


def split_documents(documents: list[Any]) -> tuple[list[Any], list[dict[str, Any]]]:
    """Backward compatible document splitting."""
    return split_documents_enhanced(documents, True, True)
