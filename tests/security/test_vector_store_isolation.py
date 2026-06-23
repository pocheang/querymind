"""
向量存储安全测试

测试向量存储的用户隔离机制。
"""

from unittest.mock import Mock, patch

import pytest

from app.retrievers.vector_store import similarity_search


class TestVectorStoreIsolation:
    """测试向量存储的安全隔离"""

    def test_similarity_search_requires_allowed_sources_by_default(self):
        """测试默认情况下必须提供 allowed_sources"""
        with pytest.raises(ValueError) as exc:
            similarity_search("test query")

        assert "allowed_sources is required" in str(exc.value)

    def test_similarity_search_accepts_empty_allowed_sources(self):
        """测试允许空的 allowed_sources（用户无可访问文档）"""
        with patch("app.retrievers.vector_store.get_vector_store"):
            result = similarity_search("test query", allowed_sources=[])

        # 空列表应返回空结果
        assert result == []

    @patch("app.retrievers.vector_store.get_vector_store")
    def test_similarity_search_with_allowed_sources(self, mock_get_store):
        """测试提供 allowed_sources 时正常工作"""
        mock_store = Mock()
        mock_store.similarity_search_with_relevance_scores.return_value = [
            (Mock(page_content="test", metadata={"source": "doc1.pdf"}), 0.9)
        ]
        mock_get_store.return_value = mock_store

        similarity_search("test query", k=5, allowed_sources=["doc1.pdf", "doc2.pdf"])

        # 验证调用时使用了过滤器
        mock_store.similarity_search_with_relevance_scores.assert_called_once()
        call_kwargs = mock_store.similarity_search_with_relevance_scores.call_args[1]
        assert "filter" in call_kwargs
        assert call_kwargs["filter"] == {"source": {"$in": ["doc1.pdf", "doc2.pdf"]}}

    @patch("app.retrievers.vector_store.get_vector_store")
    def test_similarity_search_allows_unfiltered_when_explicitly_permitted(self, mock_get_store):
        """测试显式允许时可以不使用过滤器（系统操作）"""
        mock_store = Mock()
        mock_store.similarity_search_with_relevance_scores.return_value = []
        mock_get_store.return_value = mock_store

        # 显式设置 require_source_filter=False
        similarity_search("test query", k=5, require_source_filter=False)

        # 应该调用不带过滤器的搜索
        mock_store.similarity_search_with_relevance_scores.assert_called_once()
        call_kwargs = mock_store.similarity_search_with_relevance_scores.call_args[1]
        assert "filter" not in call_kwargs

    def test_similarity_search_user_isolation_scenario(self):
        """测试用户隔离场景"""
        # 场景：用户A只能访问自己的文档
        user_a_sources = ["uploads/user_a/doc1.pdf", "uploads/user_a/doc2.pdf"]

        with patch("app.retrievers.vector_store.get_vector_store") as mock_get_store:
            mock_store = Mock()
            mock_store.similarity_search_with_relevance_scores.return_value = [
                (Mock(metadata={"source": "uploads/user_a/doc1.pdf"}), 0.9)
            ]
            mock_get_store.return_value = mock_store

            # 用户A的搜索应该只包含他的文档
            similarity_search("test query", allowed_sources=user_a_sources)

            # 验证过滤器正确应用
            call_kwargs = mock_store.similarity_search_with_relevance_scores.call_args[1]
            assert call_kwargs["filter"]["source"]["$in"] == user_a_sources


class TestVectorStoreSecurityBestPractices:
    """测试向量存储安全最佳实践"""

    def test_system_operations_must_explicitly_disable_filter(self):
        """测试系统操作必须显式禁用过滤器"""
        # 这确保没有意外的不安全调用
        with pytest.raises(ValueError):
            # 即使是系统操作，如果忘记传参数也会失败
            similarity_search("rebuild index query")

        # 必须显式说明这是系统操作
        with patch("app.retrievers.vector_store.get_vector_store") as mock_get_store:
            mock_store = Mock()
            mock_store.similarity_search_with_relevance_scores.return_value = []
            mock_get_store.return_value = mock_store

            # 正确的系统操作方式
            similarity_search("rebuild index query", require_source_filter=False)

    @patch("app.retrievers.vector_store.get_vector_store")
    def test_filter_is_applied_before_search(self, mock_get_store):
        """测试过滤器在搜索前应用（而非搜索后）"""
        mock_store = Mock()
        mock_store.similarity_search_with_relevance_scores.return_value = []
        mock_get_store.return_value = mock_store

        allowed = ["doc1.pdf", "doc2.pdf"]
        similarity_search("query", allowed_sources=allowed)

        # 验证过滤器传递给了 ChromaDB
        # 这意味着过滤在数据库层面执行，而非在应用层
        call_args = mock_store.similarity_search_with_relevance_scores.call_args
        assert call_args[1]["filter"]["source"]["$in"] == allowed
