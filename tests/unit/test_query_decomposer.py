"""
Unit tests for query decomposer service.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.advanced_rag_models import DecomposedQuery
from app.services.query_decomposer import QueryDecomposer


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client."""
    client = MagicMock()
    client.generate = AsyncMock()
    return client


@pytest.fixture
def decomposer(mock_llm_client):
    """Create query decomposer instance."""
    return QueryDecomposer(mock_llm_client)


class TestQueryDecomposer:
    """Tests for QueryDecomposer class."""

    def test_needs_decomposition_comparison(self, decomposer):
        """Test detection of comparison queries."""
        query = "FastAPI和Flask的区别是什么？"
        assert decomposer._needs_decomposition(query) is True

    def test_needs_decomposition_long_query(self, decomposer):
        """Test detection of long queries."""
        query = "请详细说明如何在生产环境中部署FastAPI应用，包括服务器配置、监控设置和安全措施"
        assert decomposer._needs_decomposition(query) is True

    def test_needs_decomposition_multiple_questions(self, decomposer):
        """Test detection of multiple questions."""
        query = "年假政策是什么？病假政策是什么？"
        assert decomposer._needs_decomposition(query) is True

    def test_needs_decomposition_simple_query(self, decomposer):
        """Test simple query doesn't need decomposition."""
        query = "什么是FastAPI？"
        assert decomposer._needs_decomposition(query) is False

    def test_detect_strategy_comparison(self, decomposer):
        """Test strategy detection for comparison queries."""
        query = "FastAPI和Flask的区别"
        strategy = decomposer._detect_strategy(query)
        assert strategy == "comparison"

    def test_detect_strategy_sequential(self, decomposer):
        """Test strategy detection for sequential queries."""
        query = "如何部署FastAPI应用的步骤"
        strategy = decomposer._detect_strategy(query)
        assert strategy == "sequential"

    def test_detect_strategy_parallel(self, decomposer):
        """Test strategy detection for parallel queries."""
        query = "年假和病假政策"
        strategy = decomposer._detect_strategy(query)
        assert strategy == "parallel"

    def test_parse_sub_queries(self, decomposer):
        """Test parsing sub-queries from LLM response."""
        response = """1. FastAPI的特点
2. Flask的特点
3. FastAPI和Flask的性能对比"""

        sub_queries = decomposer._parse_sub_queries(response)
        assert len(sub_queries) == 3
        assert "FastAPI的特点" in sub_queries
        assert "Flask的特点" in sub_queries
        assert "FastAPI和Flask的性能对比" in sub_queries

    def test_parse_sub_queries_with_bullets(self, decomposer):
        """Test parsing sub-queries with bullet points."""
        response = """- What is FastAPI?
- What is Flask?
- How do they compare?"""

        sub_queries = decomposer._parse_sub_queries(response)
        assert len(sub_queries) == 3
        assert "What is FastAPI?" in sub_queries

    @pytest.mark.asyncio
    async def test_decompose_simple_query(self, decomposer):
        """Test decomposition of simple query (no decomposition needed)."""
        query = "什么是FastAPI？"
        result = await decomposer.decompose(query)

        assert isinstance(result, DecomposedQuery)
        assert result.original_query == query
        assert result.sub_queries == [query]
        assert result.decomposition_strategy == "none"

    @pytest.mark.asyncio
    async def test_decompose_complex_query(self, decomposer, mock_llm_client):
        """Test decomposition of complex query."""
        query = "FastAPI和Flask的区别是什么？"

        # Mock LLM response
        mock_llm_client.generate.return_value = """1. FastAPI的特点
2. Flask的特点
3. FastAPI和Flask的对比"""

        result = await decomposer.decompose(query)

        assert isinstance(result, DecomposedQuery)
        assert result.original_query == query
        assert len(result.sub_queries) == 3
        assert result.decomposition_strategy == "comparison"
        assert mock_llm_client.generate.called

    @pytest.mark.asyncio
    async def test_decompose_limits_sub_queries(self, decomposer, mock_llm_client):
        """Test that decomposition limits to max 4 sub-queries."""
        query = "请详细说明FastAPI的所有特性"

        # Mock LLM response with 6 sub-queries
        mock_llm_client.generate.return_value = """1. Query 1
2. Query 2
3. Query 3
4. Query 4
5. Query 5
6. Query 6"""

        result = await decomposer.decompose(query)

        assert len(result.sub_queries) <= 4

    @pytest.mark.asyncio
    async def test_decompose_handles_llm_error(self, decomposer, mock_llm_client):
        """Test decomposition handles LLM errors gracefully."""
        query = "FastAPI和Flask的区别"

        # Mock LLM error
        mock_llm_client.generate.side_effect = Exception("LLM error")

        result = await decomposer.decompose(query)

        # Should return original query on error
        assert result.sub_queries == [query]
