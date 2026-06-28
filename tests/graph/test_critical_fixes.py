"""
Tests for critical fixes: validation integration, retry mechanism, and vector RAG fallback.

These tests verify that:
1. Cypher validation is actually called during query execution
2. Retry mechanism works with simpler queries
3. Fallback to vector RAG happens automatically
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from neo4j.exceptions import CypherSyntaxError, ClientError

from app.graph.neo4j_client import Neo4jClient
from app.agents.graph_rag_agent import run_graph_rag, _run_basic_graph_rag


class TestValidationIntegration:
    """Test that validation is integrated into query execution."""

    @patch("app.graph.neo4j_client.Neo4jClient._shared_driver")
    @patch("app.graph.cypher_validation.validate_cypher_query")
    def test_validation_called_during_entity_neighbors(self, mock_validate, mock_driver):
        """Test that validation is called when executing entity_neighbors."""
        # Setup
        mock_session = Mock()
        mock_result = []
        mock_session.run.return_value = mock_result
        mock_driver.return_value.session.return_value.__enter__.return_value = mock_session

        from app.graph.cypher_validation import ValidationResult
        mock_validate.return_value = ValidationResult(is_valid=True)

        # Execute
        client = Neo4jClient()
        client.entity_neighbors("TestEntity", limit=10)

        # Verify validation was called
        assert mock_validate.call_count >= 1
        called_query = mock_validate.call_args[0][0]
        assert "MATCH" in called_query
        assert "Entity" in called_query

    @patch("app.graph.neo4j_client.Neo4jClient._shared_driver")
    @patch("app.graph.cypher_validation.validate_cypher_query")
    def test_validation_called_during_entity_paths_2hop(self, mock_validate, mock_driver):
        """Test that validation is called when executing entity_paths_2hop."""
        # Setup
        mock_session = Mock()
        mock_result = []
        mock_session.run.return_value = mock_result
        mock_driver.return_value.session.return_value.__enter__.return_value = mock_session

        from app.graph.cypher_validation import ValidationResult
        mock_validate.return_value = ValidationResult(is_valid=True)

        # Execute
        client = Neo4jClient()
        client.entity_paths_2hop("TestEntity", limit=8)

        # Verify validation was called
        assert mock_validate.call_count >= 1
        called_query = mock_validate.call_args[0][0]
        assert "MATCH" in called_query
        assert "RELATED" in called_query

    @patch("app.graph.neo4j_client.Neo4jClient._shared_driver")
    @patch("app.graph.cypher_validation.validate_cypher_query")
    def test_validation_called_during_batch_entity_neighbors(self, mock_validate, mock_driver):
        """Test that validation is called when executing batch_entity_neighbors."""
        # Setup
        mock_session = Mock()
        mock_result = []
        mock_session.run.return_value = mock_result
        mock_driver.return_value.session.return_value.__enter__.return_value = mock_session

        from app.graph.cypher_validation import ValidationResult
        mock_validate.return_value = ValidationResult(is_valid=True)

        # Execute
        client = Neo4jClient()
        client.batch_entity_neighbors(["Entity1", "Entity2"], limit_per_entity=10)

        # Verify validation was called
        assert mock_validate.call_count >= 1
        called_query = mock_validate.call_args[0][0]
        assert "UNWIND" in called_query
        assert "Entity" in called_query


class TestRetryMechanism:
    """Test that retry mechanism works with simpler queries."""

    @patch("app.graph.neo4j_client.Neo4jClient._shared_driver")
    @patch("app.graph.cypher_validation.validate_cypher_query")
    @patch("app.graph.cypher_validation.get_simpler_query")
    def test_retry_on_validation_failure(self, mock_get_simpler, mock_validate, mock_driver):
        """Test that simpler query is tried when validation fails."""
        # Setup
        mock_session = Mock()
        mock_driver.return_value.session.return_value.__enter__.return_value = mock_session

        from app.graph.cypher_validation import ValidationResult
        # First call: validation fails
        mock_validate.return_value = ValidationResult(
            is_valid=False,
            error="Syntax error",
            error_type="syntax_error"
        )

        # Simpler query
        simpler_query = "MATCH (e:Entity) RETURN e.name LIMIT 10"
        mock_get_simpler.return_value = simpler_query
        mock_session.run.return_value = []

        # Execute
        client = Neo4jClient()
        client.entity_paths_2hop("TestEntity", limit=8)

        # Verify simpler query was requested
        assert mock_get_simpler.called
        assert mock_get_simpler.call_args[0][0] == "entity_paths_2hop"

        # Verify session.run was called (with simpler query)
        assert mock_session.run.called

    @patch("app.graph.neo4j_client.Neo4jClient._shared_driver")
    @patch("app.graph.cypher_validation.validate_cypher_query")
    @patch("app.graph.cypher_validation.get_simpler_query")
    def test_retry_on_execution_failure(self, mock_get_simpler, mock_validate, mock_driver):
        """Test that simpler query is tried when execution fails."""
        # Setup
        mock_session = Mock()
        mock_driver.return_value.session.return_value.__enter__.return_value = mock_session

        from app.graph.cypher_validation import ValidationResult
        mock_validate.return_value = ValidationResult(is_valid=True)

        # First execution fails, second succeeds
        simpler_query = "MATCH (e:Entity {name: $entity})-[r:RELATED]-(o:Entity) RETURN e.name LIMIT 10"
        mock_get_simpler.return_value = simpler_query

        mock_session.run.side_effect = [
            CypherSyntaxError("Syntax error in query"),
            []  # Simpler query succeeds
        ]

        # Execute
        client = Neo4jClient()
        try:
            client.entity_paths_2hop("TestEntity", limit=8)
        except CypherSyntaxError:
            # It's okay if it still fails after retry
            pass

        # Verify simpler query was requested
        assert mock_get_simpler.called
        assert mock_get_simpler.call_args[0][0] == "entity_paths_2hop"

        # Verify session.run was called twice (original + retry)
        assert mock_session.run.call_count == 2

    @patch("app.graph.neo4j_client.Neo4jClient._shared_driver")
    @patch("app.graph.cypher_validation.validate_cypher_query")
    @patch("app.graph.cypher_validation.get_simpler_query")
    def test_no_retry_when_no_simpler_query_available(self, mock_get_simpler, mock_validate, mock_driver):
        """Test that retry doesn't happen when no simpler query is available."""
        # Setup
        mock_session = Mock()
        mock_driver.return_value.session.return_value.__enter__.return_value = mock_session

        from app.graph.cypher_validation import ValidationResult
        mock_validate.return_value = ValidationResult(
            is_valid=False,
            error="Syntax error",
            error_type="syntax_error"
        )

        # No simpler query available
        mock_get_simpler.return_value = None
        mock_session.run.return_value = []

        # Execute
        client = Neo4jClient()
        client.entity_neighbors("TestEntity", limit=10)

        # Verify get_simpler_query was called
        assert mock_get_simpler.called

        # Original query should still be executed despite validation failure
        assert mock_session.run.called


class TestVectorRAGFallback:
    """Test that fallback to vector RAG happens automatically."""

    @patch("app.agents.vector_rag_agent.run_vector_rag")
    @patch("app.tools.graph_tools.graph_lookup")
    def test_fallback_on_graph_error(self, mock_graph_lookup, mock_vector_rag):
        """Test that vector RAG is called when graph lookup fails."""
        # Setup
        mock_graph_lookup.side_effect = Exception("Neo4j connection error")
        mock_vector_rag.return_value = {
            "context": "Vector RAG context",
            "citations": [],
            "retrieved_count": 5,
        }

        # Execute
        result = _run_basic_graph_rag("Test question", allowed_sources=None)

        # Verify vector RAG was called
        assert mock_vector_rag.called
        assert result["fallback_used"] is True
        assert result["fallback_reason"] == "Exception"
        assert result["context"] == "Vector RAG context"

    @patch("app.agents.vector_rag_agent.run_vector_rag")
    @patch("app.tools.graph_tools.graph_lookup")
    def test_fallback_on_empty_results(self, mock_graph_lookup, mock_vector_rag):
        """Test that vector RAG is called when graph returns empty results."""
        # Setup
        mock_graph_lookup.return_value = {
            "entities": [],
            "neighbors": [],
            "paths": [],
            "graph_signal_score": 0.0,
        }
        mock_vector_rag.return_value = {
            "context": "Vector RAG context",
            "citations": [],
            "retrieved_count": 5,
        }

        # Execute
        result = _run_basic_graph_rag("Test question", allowed_sources=None)

        # Verify vector RAG was called
        assert mock_vector_rag.called
        assert result["fallback_used"] is True
        assert result["fallback_reason"] == "empty_results"
        assert result["context"] == "Vector RAG context"

    @patch("app.agents.vector_rag_agent.run_vector_rag")
    @patch("app.tools.graph_tools.graph_lookup")
    def test_no_fallback_on_successful_graph_results(self, mock_graph_lookup, mock_vector_rag):
        """Test that vector RAG is NOT called when graph returns results."""
        # Setup
        mock_graph_lookup.return_value = {
            "entities": [{"entity": "Python", "relations": []}],
            "neighbors": [{"entity": "Python", "relation": "is_a", "other": "Language"}],
            "paths": [],
            "graph_signal_score": 0.8,
        }

        # Execute
        result = _run_basic_graph_rag("Test question", allowed_sources=None)

        # Verify vector RAG was NOT called
        assert not mock_vector_rag.called
        assert "fallback_used" not in result
        assert len(result["entities"]) > 0
        assert len(result["neighbors"]) > 0

    @patch("app.agents.vector_rag_agent.run_vector_rag")
    @patch("app.tools.graph_tools.graph_lookup")
    def test_fallback_handles_vector_rag_failure(self, mock_graph_lookup, mock_vector_rag):
        """Test that fallback handles vector RAG failure gracefully."""
        # Setup
        mock_graph_lookup.return_value = {
            "entities": [],
            "neighbors": [],
            "paths": [],
            "graph_signal_score": 0.0,
        }
        mock_vector_rag.side_effect = Exception("Vector RAG failed")

        # Execute
        result = _run_basic_graph_rag("Test question", allowed_sources=None)

        # Verify fallback was attempted
        assert mock_vector_rag.called
        assert result["fallback_used"] is True
        assert "fallback_error" in result
        assert result["context"] == ""


class TestEndToEndIntegration:
    """Test end-to-end integration of all three fixes."""

    @patch("app.agents.vector_rag_agent.run_vector_rag")
    @patch("app.graph.neo4j_client.Neo4jClient._shared_driver")
    @patch("app.graph.cypher_validation.validate_cypher_query")
    @patch("app.graph.cypher_validation.get_simpler_query")
    def test_full_workflow_with_retry_and_fallback(
        self, mock_get_simpler, mock_validate, mock_driver, mock_vector_rag
    ):
        """Test complete workflow: validation -> retry -> fallback."""
        # Setup: Validation fails, retry fails, fallback to vector RAG
        from app.graph.cypher_validation import ValidationResult

        mock_validate.return_value = ValidationResult(
            is_valid=False,
            error="Complex query error",
            error_type="syntax_error"
        )

        mock_get_simpler.return_value = None  # No simpler query available

        mock_session = Mock()
        mock_session.run.side_effect = CypherSyntaxError("Query failed")
        mock_driver.return_value.session.return_value.__enter__.return_value = mock_session

        mock_vector_rag.return_value = {
            "context": "Fallback context",
            "citations": [],
            "retrieved_count": 3,
        }

        # Execute through the full stack
        # This will: validate -> execute -> fail -> try simpler -> fail -> fallback to vector
        from app.tools.graph_tools import graph_lookup

        with patch("app.tools.graph_tools.Neo4jClient") as mock_client_class:
            mock_client_instance = Mock()
            mock_client_instance.search_entities.side_effect = CypherSyntaxError("Failed")
            mock_client_class.return_value = mock_client_instance

            result = _run_basic_graph_rag("Test question")

            # Verify fallback happened
            assert result["fallback_used"] is True
            assert result["context"] == "Fallback context"
