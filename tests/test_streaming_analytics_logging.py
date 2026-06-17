from unittest.mock import patch

from app.graph.streaming.safe_wrappers import safe_graph_result, safe_vector_result
from app.services.retrieval_logger import RetrievalLogger


def test_streaming_vector_logs_analytics():
    logger = RetrievalLogger.get_instance()
    logger._logs.clear()

    with patch(
        "app.graph.streaming.safe_wrappers._agent_func",
        return_value=lambda *args, **kwargs: {
            "context": "vector context",
            "retrieved_count": 2,
            "effective_hit_count": 1,
            "citations": [
                {"source": "doc-a.md", "metadata": {"hybrid_score": 0.91}},
                {"source": "doc-b.md", "metadata": {"dense_score": 0.74}},
            ],
        },
    ):
        result = safe_vector_result("What is RAG?", agent_class="general")

    assert result["retrieved_count"] == 2
    overview = logger.get_overview()
    assert overview.total_queries == 1
    assert overview.route_distribution == {"vector": 1}
    assert overview.agent_distribution == {"general": 1}


def test_streaming_graph_logs_analytics():
    logger = RetrievalLogger.get_instance()
    logger._logs.clear()

    with patch(
        "app.graph.streaming.safe_wrappers._agent_func",
        return_value=lambda *args, **kwargs: {
            "context": "graph context",
            "entities": [{"source": "graph-a.md"}],
            "neighbors": [{"source": "graph-b.md"}],
        },
    ):
        result = safe_graph_result("Show related entities", agent_class="general")

    assert len(result["entities"]) == 1
    overview = logger.get_overview()
    assert overview.total_queries == 1
    assert overview.route_distribution == {"graph": 1}
    assert overview.agent_distribution == {"general": 1}
