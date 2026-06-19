"""
PDF-aware Graph RAG integration module.

This module bridges PDF processing and Graph RAG to improve accuracy by:
1. Extracting document quality signals from PDFs
2. Applying adaptive graph lookup parameters
3. Enriching graph queries with PDF-derived context
"""

import logging
import re

from app.tools.graph_tools_enhanced import graph_lookup_enhanced

logger = logging.getLogger(__name__)

_ENGLISH_NOISE_TERMS = {
    "introduction",
    "overview",
    "description",
    "component",
    "components",
    "question",
    "translation",
    "modern",
    "these",
    "allows",
    "self",
    "references",
    "applications",
    "challenges",
}

_CHINESE_NOISE_TERMS = {
    "\u4e3b\u8981\u7279\u70b9\u5305\u62ec",
    "\u57fa\u672c\u6982\u5ff5",
    "\u5173\u952e\u6280\u672f",
    "\u5e94\u7528\u573a\u666f",
    "\u53c2\u8003\u6587\u732e",
}

_CHINESE_NOISE_PATTERNS = (
    "\u662f\u4e00\u79cd",
    "\u5305\u62ec",
    "\u901a\u8fc7",
    "\u5141\u8bb8",
    "\u80fd\u591f",
    "\u4ece\u800c",
    "\u8fdb\u884c",
    "\u63d0\u9ad8",
    "\u51cf\u5c11",
    "\u652f\u6301",
    "\u7ed3\u5408",
    "\u5e94\u7528\u4e8e",
)

_TECHNICAL_PHRASE_PATTERN = re.compile(
    r"\b(?:"
    r"large language models?|"
    r"retrieval[- ]augmented generation|"
    r"natural language processing|"
    r"machine learning|"
    r"deep learning|"
    r"artificial intelligence|"
    r"knowledge graph|"
    r"transformer architecture|"
    r"intelligent customer service systems?"
    r")\b",
    re.IGNORECASE,
)

_CHINESE_TECHNICAL_PHRASE_PATTERN = re.compile(
    r"(?:"
    r"\u5927\u8bed\u8a00\u6a21\u578b|"
    r"\u81ea\u7136\u8bed\u8a00\u5904\u7406|"
    r"\u68c0\u7d22\u589e\u5f3a\u751f\u6210|"
    r"\u667a\u80fd\u5ba2\u670d\u7cfb\u7edf|"
    r"\u673a\u5668\u7ffb\u8bd1|"
    r"\u77e5\u8bc6\u56fe\u8c31|"
    r"\u6ce8\u610f\u529b\u673a\u5236|"
    r"\u6587\u6863\u7406\u89e3\u4e0e\u5206\u6790|"
    r"\u4fe1\u606f\u68c0\u7d22"
    r")"
)

_ENGLISH_SINGLE_TERM_KEYWORDS = (
    "model",
    "models",
    "system",
    "systems",
    "framework",
    "retrieval",
    "generation",
    "language",
    "processing",
    "learning",
    "attention",
    "graph",
    "transformer",
    "chatgpt",
    "claude",
    "copilot",
    "docker",
    "kubernetes",
    "redis",
    "mongodb",
    "postgresql",
    "mysql",
    "neo4j",
)

_CHINESE_TERM_KEYWORDS = (
    "\u6a21\u578b",
    "\u7cfb\u7edf",
    "\u67b6\u6784",
    "\u673a\u5236",
    "\u751f\u6210",
    "\u68c0\u7d22",
    "\u5b66\u4e60",
    "\u8bed\u8a00",
    "\u5904\u7406",
    "\u6587\u6863",
    "\u5206\u6790",
    "\u7ffb\u8bd1",
    "\u6570\u636e\u5e93",
    "\u5b89\u5168",
    "\u667a\u80fd",
    "\u5ba2\u670d",
    "\u77e5\u8bc6\u56fe\u8c31",
)


def _is_english_entity_candidate(term: str) -> bool:
    normalized = " ".join(term.split()).strip()
    if len(normalized) < 2:
        return False

    lowered = normalized.lower()
    if lowered in _ENGLISH_NOISE_TERMS:
        return False

    words = normalized.split()
    if len(words) > 4:
        return False

    if len(words) == 1:
        if normalized.isupper():
            return True
        return any(keyword in lowered for keyword in _ENGLISH_SINGLE_TERM_KEYWORDS)

    return True


def _is_chinese_entity_candidate(term: str) -> bool:
    normalized = term.strip()
    if not normalized or len(normalized) < 2 or len(normalized) > 12:
        return False

    if normalized in _CHINESE_NOISE_TERMS:
        return False

    if any(marker in normalized for marker in _CHINESE_NOISE_PATTERNS):
        return False

    if normalized.endswith(("\u7684", "\u4e86", "\u4eec", "\u53ca\u5176")):
        return False

    return any(keyword in normalized for keyword in _CHINESE_TERM_KEYWORDS)


def _append_unique_entity(
    entities: list[str],
    seen: set[str],
    term: str,
    limit: int,
) -> None:
    normalized = " ".join(term.split()).strip(" ,.;:()[]{}<>-_")
    if not normalized:
        return

    key = normalized.casefold()
    if key in seen:
        return

    seen.add(key)
    if len(entities) < limit:
        entities.append(normalized)


def analyze_pdf_quality(text: str, metadata: dict) -> float:
    """
    Analyze PDF content quality for graph extraction confidence.

    Quality indicators:
    - Clear structure (headers, sections)
    - Formatted content (tables, lists)
    - Reasonable density (not too sparse/dense)
    - Presence of key sections (references, index)

    Args:
        text: Extracted PDF text
        metadata: PDF metadata (pages, format, etc.)

    Returns:
        Quality score (0-1)
    """
    score = 0.0

    structure_score = 0.0
    if re.search(r"^#+\s+.+$|^\d+\.\s+[A-Z][^.]+$", text, re.MULTILINE):
        structure_score += 0.15
    if re.search(r"\|.+\|.+\||\t.+\t.+\t", text):
        structure_score += 0.10
    if re.search(r"^[-*\u2022]\s+.+$|^\d+\.\s+.+$", text, re.MULTILINE):
        structure_score += 0.10
    if re.search(r"(?i)(references?|bibliography|citations?|\u53c2\u8003\u6587\u732e)", text):
        structure_score += 0.05
    score += min(0.4, structure_score)

    content_score = 0.0
    words = text.split()
    word_count = len(words)
    char_count = len(text)
    if char_count > 0:
        density = word_count / (char_count / 100)
        if 3 <= density <= 20:
            content_score += 0.15
        elif 2 <= density <= 25:
            content_score += 0.08

    if word_count >= 500:
        content_score += 0.15
    elif word_count >= 200:
        content_score += 0.08

    tech_terms = len(
        re.findall(
            r"\b(?:AI|ML|API|system|process|data|algorithm|model|method|approach|"
            r"analysis|implementation|framework|architecture|optimization)\b",
            text,
            re.IGNORECASE,
        )
    )
    if tech_terms >= 10:
        content_score += 0.10
    elif tech_terms >= 5:
        content_score += 0.05
    score += min(0.4, content_score)

    metadata_score = 0.0
    page_count = metadata.get("page", 0) if isinstance(metadata.get("page"), int) else 1
    total_pages = metadata.get("total_pages", page_count)
    if total_pages >= 10:
        metadata_score += 0.10
    elif total_pages >= 5:
        metadata_score += 0.05
    if metadata.get("format") == "markdown":
        metadata_score += 0.05
    if metadata.get("enhanced") or metadata.get("converter") == "docling":
        metadata_score += 0.05
    score += min(0.2, metadata_score)

    return min(1.0, score)


def extract_document_entities(text: str, limit: int = 20) -> list[str]:
    """
    Extract potential entities from document text for query enrichment.

    Args:
        text: Document text
        limit: Maximum entities to extract

    Returns:
        List of entity strings
    """
    entities: list[str] = []
    seen: set[str] = set()

    for term in _TECHNICAL_PHRASE_PATTERN.findall(text):
        _append_unique_entity(entities, seen, term.title(), limit)

    proper_nouns = re.findall(r"\b[A-Z][a-z]+(?: [A-Z][a-z]+){0,3}\b", text)
    for term in proper_nouns:
        if _is_english_entity_candidate(term):
            _append_unique_entity(entities, seen, term, limit)

    acronyms = re.findall(r"\b[A-Z]{2,6}s?\b", text)
    for term in acronyms:
        _append_unique_entity(entities, seen, term, limit)

    camel_case_terms = re.findall(r"\b[A-Z][a-z]+(?:[A-Z][A-Za-z0-9]+)+\b", text)
    for term in camel_case_terms:
        _append_unique_entity(entities, seen, term, limit)

    for term in _CHINESE_TECHNICAL_PHRASE_PATTERN.findall(text):
        _append_unique_entity(entities, seen, term, limit)

    chinese_terms = re.findall(
        r"[\u4e00-\u9fff]{2,10}(?:\u6a21\u578b|\u7cfb\u7edf|\u673a\u5236|\u67b6\u6784|\u7ffb\u8bd1|\u5206\u6790|\u5904\u7406)",
        text,
    )
    for term in chinese_terms:
        if _is_chinese_entity_candidate(term):
            _append_unique_entity(entities, seen, term, limit)

    return entities[:limit]


def get_document_context_for_query(
    question: str,
    retrieved_docs: list[dict],
    top_k: int = 3,
) -> dict:
    """
    Analyze retrieved documents to build context for graph queries.

    Args:
        question: User query
        retrieved_docs: List of retrieved documents with content and metadata
        top_k: Number of top documents to analyze

    Returns:
        Context dictionary with quality scores and enrichment data
    """
    if not retrieved_docs:
        return {
            "quality_score": 0.5,
            "entities": [],
            "confidence": "low",
        }

    quality_scores = []
    all_entities = set()

    for doc in retrieved_docs[:top_k]:
        content = doc.get("content", "")
        metadata = doc.get("metadata", {})
        quality_scores.append(analyze_pdf_quality(content, metadata))
        all_entities.update(extract_document_entities(content, limit=10))

    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.5
    if avg_quality >= 0.7 and len(all_entities) >= 5:
        confidence = "high"
    elif avg_quality >= 0.5 or len(all_entities) >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "quality_score": avg_quality,
        "entities": list(all_entities)[:15],
        "document_count": len(retrieved_docs[:top_k]),
        "confidence": confidence,
    }


def run_graph_rag_with_pdf_context(
    question: str,
    retrieved_docs: list[dict] | None = None,
    allowed_sources: list[str] | None = None,
    agent_class: str | None = None,
) -> dict:
    """
    Enhanced Graph RAG with PDF-aware optimizations.

    This is a drop-in replacement for run_graph_rag that applies
    PDF quality analysis and adaptive parameters.

    Args:
        question: User query
        retrieved_docs: Retrieved documents (for quality analysis)
        allowed_sources: Optional source filter
        agent_class: Agent class for document filtering

    Returns:
        Graph RAG results with enhanced accuracy
    """
    from app.services.agent_document_filter import get_sources_by_agent_class

    if allowed_sources is None and agent_class:
        allowed_sources = get_sources_by_agent_class(agent_class)

    if retrieved_docs:
        context = get_document_context_for_query(question, retrieved_docs)
        context_quality = context["quality_score"]
        logger.info(
            "PDF context analysis: quality=%.2f, entities=%s, confidence=%s",
            context_quality,
            len(context["entities"]),
            context["confidence"],
        )
    else:
        context_quality = 0.5
        context = {"quality_score": 0.5, "entities": [], "confidence": "medium"}

    if context_quality >= 0.7:
        max_entities = 12
        max_neighbors = 20
        max_paths = 12
    elif context_quality >= 0.5:
        max_entities = 10
        max_neighbors = 15
        max_paths = 10
    else:
        max_entities = 8
        max_neighbors = 12
        max_paths = 8

    try:
        graph_result = graph_lookup_enhanced(
            question=question,
            allowed_sources=allowed_sources,
            context_quality=context_quality,
            max_entities=max_entities,
            max_neighbors=max_neighbors,
            max_paths=max_paths,
        )
    except Exception as e:
        if type(e).__name__ in {"ServiceUnavailable", "ConnectionError"}:
            logger.warning(
                "Enhanced graph lookup unavailable for question '%s': %s",
                question,
                type(e).__name__,
            )
        else:
            logger.exception("Enhanced graph lookup failed for question: %s", question)
        return {
            "context": "",
            "entities": [],
            "neighbors": [],
            "paths": [],
            "graph_signal_score": 0.0,
            "confidence": "low",
            "error": f"graph_lookup_error:{type(e).__name__}",
        }

    entities = graph_result.get("entities", [])
    neighbors = graph_result.get("neighbors", [])
    paths = graph_result.get("paths", [])
    graph_signal_score = float(graph_result.get("graph_signal_score", 0.0) or 0.0)
    confidence = graph_result.get("confidence", "medium")

    lines = []
    for item in entities:
        name = item.get("entity", "")
        if not name:
            continue
        lines.append(f"Entity: {name}")
        for rel in item.get("relations", []):
            if rel.get("other"):
                lines.append(
                    f"  - {rel.get('relation')} ({rel.get('weight', 0):.2f}) -> {rel.get('other')}"
                )

    for row in neighbors:
        if row.get("entity") and row.get("relation") and row.get("other"):
            lines.append(
                f"Neighbor: {row['entity']} -[{row['relation']}|{float(row.get('weight', 0)):.2f}]- {row['other']}"
            )

    for row in paths:
        if row.get("source") and row.get("middle") and row.get("target"):
            lines.append(
                f"Path2Hop: {row['source']} -[{row.get('rel1', '')}]- {row['middle']} "
                f"-[{row.get('rel2', '')}]- {row['target']} | w={float(row.get('weight', 0)):.2f}"
            )

    return {
        "context": "\n".join(lines),
        "entities": [item.get("entity") for item in entities if item.get("entity")],
        "neighbors": neighbors,
        "paths": paths,
        "graph_signal_score": graph_signal_score,
        "confidence": confidence,
        "pdf_context": context,
    }


def should_use_graph_rag(
    question: str,
    retrieved_docs: list[dict] | None = None,
    graph_signal_score: float | None = None,
) -> tuple[bool, str]:
    """
    Decide whether to use Graph RAG based on context.

    Decision factors:
    - Graph signal strength
    - Document quality
    - Query characteristics

    Args:
        question: User query
        retrieved_docs: Retrieved documents
        graph_signal_score: Pre-computed graph signal (if available)

    Returns:
        Tuple of (should_use, reason)
    """
    if graph_signal_score is not None and graph_signal_score >= 0.6:
        return True, f"strong_graph_signal:{graph_signal_score:.2f}"

    if retrieved_docs:
        context = get_document_context_for_query(question, retrieved_docs)
        if context["quality_score"] >= 0.7 and len(context["entities"]) >= 5:
            return True, "high_quality_documents_with_entities"
        if context["quality_score"] < 0.3:
            return False, "low_quality_documents"

    potential_entities = len(
        re.findall(
            r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b|[A-Z]{2,5}\b|[\u4e00-\u9fff]{2,}",
            question,
        )
    )
    if potential_entities >= 3:
        return True, f"multi_entity_query:{potential_entities}_entities"

    relation_keywords = [
        "relationship",
        "\u5173\u7cfb",
        "connect",
        "\u8fde\u63a5",
        "relate",
        "\u5173\u8054",
        "between",
        "\u4e4b\u95f4",
        "link",
        "\u94fe\u63a5",
        "impact",
        "\u5f71\u54cd",
        "cause",
        "\u5bfc\u81f4",
        "depend",
        "\u4f9d\u8d56",
    ]
    if any(keyword in question.lower() for keyword in relation_keywords):
        return True, "relationship_query"

    return True, "default_strategy"
