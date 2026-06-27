"""
Tests for Graph RAG agent with Cypher validation and fallback.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.agents.graph_rag_agent import run_graph_rag


class TestGraphRAGValidationAndFallback:
    """Test Graph RAG with validation and fallback to vector RAG."""

    @patch("app.tools.graph_tools.graph_lookup")
    def test_successful_graph_query(self, mock_graph_lookup):
        """Test successful graph query without errors."""
        mock_graph_lookup.return_value = {
            "entities": [{"entity": "Python", "relations": []}],
            "neighbors": [],
            "paths": [],
            "graph_signal_score": 0.8,
        }

        result = run_graph_rag("What is Python?")

        assert result["graph_signal_score"] == 0.8
        assert len(result["entities"]) == 1
        assert "error" not in result
        mock_graph_lookup.assert_called_once()

    @patch("app.tools.graph_tools.graph_lookup")
    def test_graph_query_with_neo4j_error(self, mock_graph_lookup):
        """Test graph query handles Neo4j errors gracefully."""
        from neo4j.exceptions import ServiceUnavailable

        mock_graph_lookup.side_effect = ServiceUnavailable("Connection failed")

        result = run_graph_rag("What is Python?")

        assert result["graph_signal_score"] == 0.0
        assert result["entities"] == []
        assert "error" in result
        assert "ServiceUnavailable" in result["error"]
        assert result.get("should_fallback_to_vector") is True

    @patch("app.tools.graph_tools.graph_lookup")
    def test_graph_query_empty_results(self, mock_graph_lookup):
        """Test graph query with empty results indicates fallback."""
        mock_graph_lookup.return_value = {
            "entities": [],
            "neighbors": [],
            "paths": [],
            "graph_signal_score": 0.0,
        }

        result = run_graph_rag("What is Python?")

        assert result["graph_signal_score"] == 0.0
        assert result["entities"] == []
        assert result["context"] == ""
        assert result.get("should_fallback_to_vector") is True

    @patch("app.tools.graph_tools.graph_lookup")
    def test_graph_query_with_syntax_error(self, mock_graph_lookup):
        """Test graph query handles syntax errors gracefully."""
        from neo4j.exceptions import CypherSyntaxError

        mock_graph_lookup.side_effect = CypherSyntaxError("Syntax error in query")

        result = run_graph_rag("What is Python?")

        assert result["graph_signal_score"] == 0.0
        assert "error" in result
        assert "CypherSyntaxError" in result["error"]
        assert result.get("should_fallback_to_vector") is True

    @patch("app.tools.graph_tools.graph_lookup")
    def test_graph_query_with_allowed_sources(self, mock_graph_lookup):
        """Test graph query respects allowed_sources parameter."""
        mock_graph_lookup.return_value = {
            "entities": [{"entity": "Python", "relations": []}],
            "neighbors": [],
            "paths": [],
            "graph_signal_score": 0.8,
        }

        allowed_sources = ["doc1.pdf", "doc2.pdf"]
        result = run_graph_rag("What is Python?", allowed_sources=allowed_sources)

        assert result["graph_signal_score"] == 0.8
        mock_graph_lookup.assert_called_once()
        call_kwargs = mock_graph_lookup.call_args[1]
        assert call_kwargs["allowed_sources"] == allowed_sources

    @patch("app.tools.graph_tools.graph_lookup")
    def test_graph_query_with_connection_error(self, mock_graph_lookup):
        """Test graph query handles connection errors gracefully."""
        mock_graph_lookup.side_effect = ConnectionError("Cannot connect to Neo4j")

        result = run_graph_rag("What is Python?")

        assert result["graph_signal_score"] == 0.0
        assert result["entities"] == []
        assert "error" in result
        assert "ConnectionError" in result["error"]
        assert result.get("should_fallback_to_vector") is True

    @patch("app.tools.graph_tools.graph_lookup")
    def test_graph_query_partial_results(self, mock_graph_lookup):
        """Test graph query with partial results."""
        mock_graph_lookup.return_value = {
            "entities": [
                {
                    "entity": "Python",
                    "relations": [
                        {"relation": "is_a", "other": "Programming Language", "weight": 1.0}
                    ]
                }
            ],
            "neighbors": [
                {"entity": "Python", "relation": "is_a", "other": "Programming Language", "weight": 1.0}
            ],
            "paths": [],
            "graph_signal_score": 0.6,
        }

        result = run_graph_rag("What is Python?")

        assert result["graph_signal_score"] == 0.6
        assert len(result["entities"]) == 1
        assert len(result["neighbors"]) == 1
        assert len(result["paths"]) == 0

    @patch("app.tools.graph_tools.graph_lookup")
    def test_graph_query_formats_context_correctly(self, mock_graph_lookup):
        """Test that graph context is formatted correctly."""
        mock_graph_lookup.return_value = {
            "entities": [
                {
                    "entity": "Python",
                    "relations": [
                        {"relation": "is_a", "other": "Language", "weight": 1.0}
                    ]
                }
            ],
            "neighbors": [
                {"entity": "Python", "relation": "uses", "other": "Interpreter", "weight": 0.8}
            ],
            "paths": [
                {
                    "source": "Python",
                    "rel1": "is_a",
                    "middle": "Language",
                    "rel2": "used_in",
                    "target": "AI",
                    "weight": 0.9
                }
            ],
            "graph_signal_score": 0.85,
        }

        result = run_graph_rag("What is Python?")

        context = result["context"]
        assert "Entity: Python" in context
        assert "is_a" in context
        assert "Language" in context
        assert "Neighbor:" in context
        assert "Path2Hop:" in context
        assert "AI" in context
