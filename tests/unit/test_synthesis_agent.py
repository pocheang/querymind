"""
Synthesis Agent 单元测试

测试Synthesis Agent的核心功能
"""

from unittest.mock import Mock, patch

import pytest


class TestSynthesisAgent:
    """测试Synthesis Agent核心功能"""

    @pytest.fixture
    def mock_documents(self):
        """模拟检索到的文档"""
        return [
            {
                "page_content": "Python is a programming language.",
                "metadata": {"source": "doc1.pdf", "page": 1},
            },
            {
                "page_content": "It was created by Guido van Rossum.",
                "metadata": {"source": "doc2.pdf", "page": 3},
            },
        ]

    @pytest.fixture
    def mock_state(self, mock_documents):
        """模拟GraphState"""
        return {
            "question": "What is Python?",
            "vector_result": {
                "vector_documents": mock_documents,
                "vector_answer": "Python is a programming language created by Guido.",
            },
            "memory_context": "",
            "session_id": "test_session_123",
            "user_id": "test_user",
        }

    def test_synthesize_answer_basic(self, mock_state):
        """测试基本的答案合成功能"""
        from app.agents.synthesis_agent import synthesize_answer

        with patch("app.agents.synthesis_agent.get_chat_model") as mock_model:
            mock_llm = Mock()
            mock_llm.invoke.return_value.content = "Python is a high-level programming language."
            mock_model.return_value = mock_llm

            result = synthesize_answer(
                question=mock_state["question"],
                skill_name="test_skill",
                memory_context=mock_state.get("memory_context", ""),
                vector_context="Python is a programming language created by Guido.",
                session_id=mock_state.get("session_id", ""),
            )

            # 验证返回了结果
            assert result is not None
            assert isinstance(result, dict)
            assert "answer" in result
            assert "detected_language" in result

    def test_language_detection_english(self):
        """测试英文语言检测"""
        text = "This is an English sentence."

        # 简单检测：如果包含中文字符比例<20%则为英文
        chinese_chars = sum(1 for c in text if "一" <= c <= "鿿")
        is_chinese = chinese_chars / len(text) > 0.2

        assert not is_chinese  # 英文文本

    def test_language_detection_chinese(self):
        """测试中文语言检测"""
        text = "这是一句中文句子。"

        # 检测中文字符比例
        chinese_chars = sum(1 for c in text if "一" <= c <= "鿿")
        is_chinese = chinese_chars / len(text) > 0.2

        assert is_chinese  # 中文文本

    def test_synthesize_answer_with_graph_context(self, mock_state):
        """测试包含图谱上下文的答案合成"""
        from app.agents.synthesis_agent import synthesize_answer

        graph_context = "Python -> created_by -> Guido van Rossum"

        with patch("app.agents.synthesis_agent.get_chat_model") as mock_model:
            mock_llm = Mock()
            mock_llm.invoke.return_value.content = "Python is a programming language created by Guido van Rossum."
            mock_model.return_value = mock_llm

            result = synthesize_answer(
                question=mock_state["question"],
                skill_name="test_skill",
                memory_context=mock_state.get("memory_context", ""),
                vector_context="Python is a programming language.",
                graph_context=graph_context,
                session_id=mock_state.get("session_id", ""),
            )

            assert result is not None
            assert isinstance(result, dict)
            assert "answer" in result
            assert "detected_language" in result

    def test_synthesize_answer_empty_documents(self):
        """测试没有检索到文档时的答案合成"""
        from app.agents.synthesis_agent import synthesize_answer

        with patch("app.agents.synthesis_agent.get_chat_model") as mock_model:
            mock_llm = Mock()
            mock_llm.invoke.return_value.content = "I don't have enough information."
            mock_model.return_value = mock_llm

            result = synthesize_answer(
                question="What is Python?",
                skill_name="test_skill",
                vector_context="",
                session_id="test_session",
            )

            assert result is not None
            assert isinstance(result, dict)
            assert "answer" in result
            assert "detected_language" in result

    def test_synthesize_answer_llm_failure(self, mock_state):
        """测试LLM失败时的错误处理"""
        from app.agents.synthesis_agent import synthesize_answer

        with patch("app.agents.synthesis_agent.get_chat_model") as mock_model:
            mock_llm = Mock()
            mock_llm.invoke.side_effect = Exception("LLM error")
            mock_model.return_value = mock_llm

            # 应该优雅处理错误，返回fallback消息
            result = synthesize_answer(
                question=mock_state["question"],
                skill_name="test_skill",
                memory_context=mock_state.get("memory_context", ""),
                session_id=mock_state.get("session_id", ""),
            )

            # 验证返回了fallback消息
            assert result is not None
            assert isinstance(result, dict)
            assert "answer" in result
            assert "detected_language" in result
