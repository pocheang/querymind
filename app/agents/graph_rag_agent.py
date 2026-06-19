import logging

from app.core.config import get_settings
from app.tools.graph_tools import graph_lookup
from app.services.agent_document_filter import get_sources_by_agent_class

logger = logging.getLogger(__name__)


def run_graph_rag(
    question: str,
    allowed_sources: list[str] | None = None,
    agent_class: str | None = None,
    retrieved_docs: list[dict] | None = None,
) -> dict:
    # 自动应用 agent 文档过滤
    if allowed_sources is None and agent_class:
        allowed_sources = get_sources_by_agent_class(agent_class)

    settings = get_settings()
    if settings.graph_rag_enhanced:
        from app.agents.graph_rag_agent_enhanced import (
            get_document_context_for_query,
            run_graph_rag_with_pdf_context,
        )

        pdf_context = None
        if retrieved_docs:
            pdf_context = get_document_context_for_query(question, retrieved_docs)
            if pdf_context["quality_score"] < settings.graph_rag_min_pdf_quality:
                return {
                    "context": "",
                    "entities": [],
                    "neighbors": [],
                    "paths": [],
                    "graph_signal_score": 0.0,
                    "confidence": "low",
                    "pdf_context": pdf_context,
                    "skipped_reason": "low_quality_documents",
                }

        result = run_graph_rag_with_pdf_context(
            question,
            retrieved_docs=retrieved_docs,
            allowed_sources=allowed_sources,
            agent_class=agent_class,
        )
        if pdf_context is not None and "pdf_context" not in result:
            result["pdf_context"] = pdf_context
        return result

    try:
        graph_result = graph_lookup(question, allowed_sources=allowed_sources)
    except Exception as e:
        if type(e).__name__ in {"ServiceUnavailable", "ConnectionError"}:
            logger.warning("Graph lookup unavailable for question '%s': %s", question, type(e).__name__)
        else:
            logger.exception(f"Graph lookup failed for question: {question}")
        return {
            "context": "",
            "entities": [],
            "neighbors": [],
            "paths": [],
            "graph_signal_score": 0.0,
            "error": f"graph_lookup_error:{type(e).__name__}",
        }

    entities = graph_result.get("entities", [])
    neighbors = graph_result.get("neighbors", [])
    paths = graph_result.get("paths", [])
    graph_signal_score = float(graph_result.get("graph_signal_score", 0.0) or 0.0)

    lines = []
    for item in entities:
        name = item.get("entity", "")
        if not name:
            continue
        lines.append(f"Entity: {name}")
        for rel in item.get("relations", []):
            if rel.get("other"):
                lines.append(f"  - {rel.get('relation')} ({rel.get('weight', 0):.2f}) -> {rel.get('other')}")

    for row in neighbors:
        if row.get("entity") and row.get("relation") and row.get("other"):
            lines.append(
                f"Neighbor: {row['entity']} -[{row['relation']}|{float(row.get('weight', 0)):.2f}]- {row['other']}"
            )
    for row in paths:
        if row.get("source") and row.get("middle") and row.get("target"):
            lines.append(
                "Path2Hop: "
                f"{row['source']} -[{row.get('rel1', '')}]- {row['middle']} -[{row.get('rel2', '')}]- {row['target']}"
                f" | w={float(row.get('weight', 0)):.2f}"
            )

    return {
        "context": "\n".join(lines),
        "entities": [x.get("entity") for x in entities if x.get("entity")],
        "neighbors": neighbors,
        "paths": paths,
        "graph_signal_score": graph_signal_score,
    }
