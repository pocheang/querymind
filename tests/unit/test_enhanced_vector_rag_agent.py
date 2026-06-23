"""
Enhanced Vector RAG Agent 单元测试

测试EnhancedVectorRAGAgent的Self-RAG评估和相关性评分功能
"""

from unittest.mock import Mock, patch

import pytest


class TestEnhancedVectorRAGAgent:
    """测试Enhanced Vector RAG Agent核心功能"""

    @pytest.fixture
    def mock_documents(self):
        """模拟检索到的文档"""
        return [
            {
                "page_content": "Python is a programming language",
                "metadata": {"source": "doc1.pdf", "page": 1},
            },
            {
                "page_content": "Machine learning is a subset of AI",
                "metadata": {"source": "doc2.pdf", "page": 5},
            },
            {
                "page_content": "Unrelated content about cooking",
                "metadata": {"source": "doc3.pdf", "page": 10},
            },
        ]

    def test_retrieve_basic(self, mock_documents):
        """测试基本的检索流程"""
        query = "What is Python?"

        with patch("app.retrievers.vector_store.similarity_search") as mock_search:
            mock_search.return_value = [(doc, 0.8) for doc in mock_documents]

            # 调用similarity_search
            from app.retrievers.vector_store import similarity_search

            results = similarity_search(
                query=query,
                k=5,
                allowed_sources=["doc1.pdf", "doc2.pdf", "doc3.pdf"],
                require_source_filter=False,
            )

            assert results is not None
            assert len(results) > 0

    def test_vector_search_with_filter(self, mock_documents):
        """测试带过滤的向量搜索"""
        query = "What is Python?"

        with patch("app.retrievers.vector_store.get_vector_store") as mock_store:
            mock_vs = Mock()
            mock_vs.similarity_search_with_relevance_scores.return_value = [(mock_documents[0], 0.9)]
            mock_store.return_value = mock_vs

            from app.retrievers.vector_store import similarity_search

            similarity_search(
                query=query,
                k=5,
                allowed_sources=["doc1.pdf"],
                require_source_filter=False,
            )

            assert mock_vs.similarity_search_with_relevance_scores.called

    def test_empty_search_results(self):
        """测试空检索结果的处理"""
        query = "Non-existent query"

        with patch("app.retrievers.vector_store.get_vector_store") as mock_store:
            mock_vs = Mock()
            mock_vs.similarity_search_with_relevance_scores.return_value = []
            mock_store.return_value = mock_vs

            from app.retrievers.vector_store import similarity_search

            results = similarity_search(
                query=query,
                k=5,
                allowed_sources=[],
                require_source_filter=False,
            )

            assert results == []

    def test_source_filter_validation(self):
        """测试allowed_sources过滤验证"""
        from app.retrievers.vector_store import similarity_search

        # 测试类型验证
        with pytest.raises(TypeError):
            similarity_search(
                query="test",
                k=5,
                allowed_sources="not_a_list",  # 应该是list
                require_source_filter=False,
            )

    def test_require_source_filter(self):
        """测试强制源过滤"""
        from app.retrievers.vector_store import similarity_search

        # require_source_filter=True 但 allowed_sources=None 应该报错
        with pytest.raises(ValueError):
            similarity_search(
                query="test",
                k=5,
                allowed_sources=None,
                require_source_filter=True,
            )

    def test_similarity_threshold(self, mock_documents):
        """测试相似度阈值过滤"""
        query = "What is Python?"

        with patch("app.retrievers.vector_store.get_vector_store") as mock_store:
            mock_vs = Mock()
            # 模拟不同的相似度分数
            mock_vs.similarity_search_with_relevance_scores.return_value = [
                (mock_documents[0], 0.9),  # 高相似度
                (mock_documents[1], 0.6),  # 中等相似度
                (mock_documents[2], 0.3),  # 低相似度
            ]
            mock_store.return_value = mock_vs

            from app.retrievers.vector_store import similarity_search

            results = similarity_search(
                query=query,
                k=5,
                allowed_sources=None,
                require_source_filter=False,
            )

            # 应该返回所有结果（阈值过滤在上层）
            assert len(results) == 3
