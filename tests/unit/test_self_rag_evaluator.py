"""
Unit tests for Self-RAG evaluator service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.self_rag_evaluator import SelfRAGEvaluator
from app.models.advanced_rag_models import RelevanceScore, AnswerQuality


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client."""
    client = MagicMock()
    client.generate = AsyncMock()
    return client


@pytest.fixture
def evaluator(mock_llm_client):
    """Create Self-RAG evaluator instance."""
    return SelfRAGEvaluator(mock_llm_client)


@pytest.fixture
def sample_documents():
    """Create sample documents for testing."""
    return [
        {
            "id": "doc1",
            "content": "FastAPI is a modern web framework for building APIs with Python.",
            "metadata": {"source": "fastapi_docs.md"}
        },
        {
            "id": "doc2",
            "content": "Flask is a lightweight WSGI web application framework.",
            "metadata": {"source": "flask_docs.md"}
        },
        {
            "id": "doc3",
            "content": "Django is a high-level Python web framework.",
            "metadata": {"source": "django_docs.md"}
        }
    ]


class TestSelfRAGEvaluator:
    """Tests for SelfRAGEvaluator class."""

    def test_parse_relevance_score_fraction(self, evaluator):
        """Test parsing relevance score in fraction format."""
        response = "Score: 8/10\nReasoning: Highly relevant"
        score = evaluator._parse_relevance_score(response)
        assert score == 0.8

    def test_parse_relevance_score_decimal(self, evaluator):
        """Test parsing relevance score in decimal format."""
        response = "Score: 0.75\nReasoning: Partially relevant"
        score = evaluator._parse_relevance_score(response)
        assert score == 0.75

    def test_parse_relevance_score_out_of_ten(self, evaluator):
        """Test parsing relevance score when given as integer out of 10."""
        response = "Score: 9\nReasoning: Very relevant"
        score = evaluator._parse_relevance_score(response)
        assert score == 0.9

    def test_parse_relevance_score_default(self, evaluator):
        """Test default score when parsing fails."""
        response = "No score found"
        score = evaluator._parse_relevance_score(response)
        assert score == 0.5

    def test_parse_quality_evaluation(self, evaluator):
        """Test parsing quality evaluation."""
        response = """Completeness: 0.8
Accuracy: 0.9
Relevance: 0.85
Overall Score: 0.85
Feedback: Good answer"""

        quality = evaluator._parse_quality_evaluation(response)
        assert quality["completeness"] == 0.8
        assert quality["accuracy"] == 0.9
        assert quality["relevance"] == 0.85
        assert quality["score"] == 0.85

    def test_parse_quality_evaluation_calculates_average(self, evaluator):
        """Test that overall score is calculated if not provided."""
        response = """Completeness: 0.8
Accuracy: 0.9
Relevance: 0.7"""

        quality = evaluator._parse_quality_evaluation(response)
        expected_avg = (0.8 + 0.9 + 0.7) / 3
        assert abs(quality["score"] - expected_avg) < 0.01

    @pytest.mark.asyncio
    async def test_evaluate_retrieval_relevance(self, evaluator, mock_llm_client, sample_documents):
        """Test evaluation of retrieval relevance."""
        query = "What is FastAPI?"

        # Mock LLM responses
        mock_llm_client.generate.side_effect = [
            "Score: 9/10\nReasoning: Directly answers the question",
            "Score: 3/10\nReasoning: About Flask, not FastAPI",
            "Score: 2/10\nReasoning: About Django, not relevant"
        ]

        scores = await evaluator.evaluate_retrieval_relevance(query, sample_documents)

        assert len(scores) == 3
        assert all(isinstance(s, RelevanceScore) for s in scores)
        assert scores[0].score == 0.9
        assert scores[1].score == 0.3
        assert scores[2].score == 0.2

    @pytest.mark.asyncio
    async def test_evaluate_retrieval_relevance_handles_error(
        self, evaluator, mock_llm_client, sample_documents
    ):
        """Test that evaluation handles errors gracefully."""
        query = "What is FastAPI?"

        # Mock LLM error
        mock_llm_client.generate.side_effect = Exception("LLM error")

        scores = await evaluator.evaluate_retrieval_relevance(query, sample_documents)

        # Should return default scores on error
        assert len(scores) == 3
        assert all(s.score == 0.5 for s in scores)

    def test_filter_relevant_documents(self, evaluator, sample_documents):
        """Test filtering documents by relevance threshold."""
        relevance_scores = [
            RelevanceScore(document_id="doc1", score=0.9, reasoning="Highly relevant"),
            RelevanceScore(document_id="doc2", score=0.4, reasoning="Not very relevant"),
            RelevanceScore(document_id="doc3", score=0.7, reasoning="Somewhat relevant")
        ]

        # Default threshold is 0.6
        filtered = evaluator.filter_relevant_documents(sample_documents, relevance_scores)

        assert len(filtered) == 2
        assert filtered[0]["id"] == "doc1"
        assert filtered[1]["id"] == "doc3"

    @pytest.mark.asyncio
    async def test_evaluate_answer_quality(self, evaluator, mock_llm_client, sample_documents):
        """Test evaluation of answer quality."""
        query = "What is FastAPI?"
        answer = "FastAPI is a modern web framework for building APIs with Python."

        # Mock LLM response
        mock_llm_client.generate.return_value = """Completeness: 0.9
Accuracy: 1.0
Relevance: 0.95
Overall Score: 0.95
Feedback: Excellent answer, directly addresses the question"""

        quality = await evaluator.evaluate_answer_quality(query, answer, sample_documents)

        assert isinstance(quality, AnswerQuality)
        assert quality.score == 0.95
        assert quality.completeness == 0.9
        assert quality.accuracy == 1.0
        assert quality.relevance == 0.95
        assert quality.needs_refinement is False

    @pytest.mark.asyncio
    async def test_evaluate_answer_quality_low_score(self, evaluator, mock_llm_client, sample_documents):
        """Test that low quality scores trigger refinement flag."""
        query = "What is FastAPI?"
        answer = "It's a framework."

        # Mock LLM response with low scores
        mock_llm_client.generate.return_value = """Completeness: 0.3
Accuracy: 0.5
Relevance: 0.4
Overall Score: 0.4
Feedback: Answer is too brief and lacks detail"""

        quality = await evaluator.evaluate_answer_quality(query, answer, sample_documents)

        assert quality.score == 0.4
        assert quality.needs_refinement is True

    @pytest.mark.asyncio
    async def test_evaluate_answer_quality_handles_error(
        self, evaluator, mock_llm_client, sample_documents
    ):
        """Test that answer quality evaluation handles errors gracefully."""
        query = "What is FastAPI?"
        answer = "FastAPI is a framework."

        # Mock LLM error
        mock_llm_client.generate.side_effect = Exception("LLM error")

        quality = await evaluator.evaluate_answer_quality(query, answer, sample_documents)

        # Should return default quality on error
        assert quality.score == 0.5
        assert quality.needs_refinement is True

    def test_format_documents(self, evaluator, sample_documents):
        """Test formatting documents for prompt."""
        formatted = evaluator._format_documents(sample_documents)

        assert "Document 1:" in formatted
        assert "Document 2:" in formatted
        assert "Document 3:" in formatted
        assert "FastAPI" in formatted
