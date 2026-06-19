from scripts.optimize_graph_rag_accuracy import GraphRAGOptimizer


def test_get_graph_coverage_stats_reports_unavailable(monkeypatch):
    optimizer = GraphRAGOptimizer()

    class BrokenDriver:
        def session(self):
            raise ConnectionError("neo4j down")

    class BrokenClient:
        driver = BrokenDriver()

        def close(self):
            return None

    monkeypatch.setattr(optimizer, "_get_client", lambda: BrokenClient())

    stats = optimizer.get_graph_coverage_stats()

    assert stats["available"] is False
    assert stats["error"] == "ConnectionError"
    assert "Neo4j is unavailable" in stats["message"]


def test_suggest_optimizations_for_unavailable_graph():
    optimizer = GraphRAGOptimizer()

    suggestions = optimizer.suggest_optimizations(
        {
            "available": False,
            "error": "ConnectionError",
            "message": "Neo4j is unavailable. Start Neo4j to inspect graph coverage.",
        }
    )

    assert any("Start Neo4j" in item for item in suggestions)
    assert any("analyze" in item and "extract" in item for item in suggestions)
