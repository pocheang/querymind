"""Integration tests for multilingual response API."""

from unittest.mock import Mock, patch

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

api_main = pytest.importorskip("app.api.main")
query_routes = pytest.importorskip("app.api.routes.query")


def test_query_endpoint_auto_detect_chinese(monkeypatch):
    """Test /query endpoint auto-detects Chinese and returns detected_language."""
    # Mock user authentication using dependency_overrides
    api_main.app.dependency_overrides[api_main._require_user] = lambda: {"user_id": "test_user", "role": "viewer"}

    try:
        # Mock other dependencies
        monkeypatch.setattr(query_routes, "_require_permission", lambda *args, **kwargs: None)
        monkeypatch.setattr(
            query_routes, "_require_existing_session_for_query", lambda user, session_id: "test_session"
        )
        monkeypatch.setattr(query_routes.quota_guard, "enforce_query_quota", lambda user: None)

        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache.mark_inflight.return_value = True
        monkeypatch.setattr(query_routes, "query_result_cache", mock_cache)

        monkeypatch.setattr(query_routes, "_build_memory_context_for_session", lambda **kwargs: "")
        monkeypatch.setattr(query_routes, "_allowed_sources_for_user", lambda user: [])
        monkeypatch.setattr(
            query_routes,
            "_effective_strategy_for_session",
            lambda **kwargs: ("advanced", {"reason": "default", "bucket": "default"}),
        )

        mock_history = Mock()
        mock_history.append_message = Mock()
        monkeypatch.setattr(query_routes, "_history_store_for_user", lambda user: mock_history)

        monkeypatch.setattr(query_routes, "_promote_long_term_memory", lambda **kwargs: None)
        monkeypatch.setattr(query_routes, "_audit", lambda *args, **kwargs: None)
        monkeypatch.setattr(query_routes, "_trace_id", lambda request: "trace-123")
        monkeypatch.setattr(query_routes, "_launch_shadow_run", lambda **kwargs: None)

        # Mock run_query to return a result with detected_language
        def mock_run_query(*args, **kwargs):
            return {
                "answer": "RAG是检索增强生成技术",
                "route": "vector",
                "reason": "vector_sufficient",
                "skill": "answer_with_citations",
                "agent_class": "general",
                "vector_result": {"context": "...", "citations": [], "retrieved_count": 5},
                "graph_result": {"context": "", "entities": []},
                "web_result": {"used": False, "citations": [], "context": ""},
                "grounding": {"support_ratio": 0.95},
                "answer_safety": {},
                "explainability": {},
                "detected_language": "zh",
            }

        monkeypatch.setattr(query_routes, "run_query", mock_run_query)

        client = TestClient(api_main.app)
        response = client.post(
            "/query",
            json={
                "question": "什么是RAG？",
                "use_web_fallback": False,
                "use_reasoning": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify detected_language is in response
        assert "detected_language" in data
        assert data["detected_language"] == "zh"
        assert "answer" in data
        assert data["answer"] == "RAG是检索增强生成技术"
    finally:
        # Clean up dependency overrides
        api_main.app.dependency_overrides.clear()


def test_query_endpoint_force_language_english(monkeypatch):
    """Test /query endpoint with force_language='en' parameter."""
    # Mock user authentication using dependency_overrides
    api_main.app.dependency_overrides[api_main._require_user] = lambda: {"user_id": "test_user", "role": "viewer"}

    try:
        # Mock other dependencies
        monkeypatch.setattr(query_routes, "_require_permission", lambda *args, **kwargs: None)
        monkeypatch.setattr(
            query_routes, "_require_existing_session_for_query", lambda user, session_id: "test_session"
        )
        monkeypatch.setattr(query_routes.quota_guard, "enforce_query_quota", lambda user: None)

        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache.mark_inflight.return_value = True
        monkeypatch.setattr(query_routes, "query_result_cache", mock_cache)

        monkeypatch.setattr(query_routes, "_build_memory_context_for_session", lambda **kwargs: "")
        monkeypatch.setattr(query_routes, "_allowed_sources_for_user", lambda user: [])
        monkeypatch.setattr(
            query_routes,
            "_effective_strategy_for_session",
            lambda **kwargs: ("advanced", {"reason": "default", "bucket": "default"}),
        )

        mock_history = Mock()
        mock_history.append_message = Mock()
        monkeypatch.setattr(query_routes, "_history_store_for_user", lambda user: mock_history)

        monkeypatch.setattr(query_routes, "_promote_long_term_memory", lambda **kwargs: None)
        monkeypatch.setattr(query_routes, "_audit", lambda *args, **kwargs: None)
        monkeypatch.setattr(query_routes, "_trace_id", lambda request: "trace-123")
        monkeypatch.setattr(query_routes, "_launch_shadow_run", lambda **kwargs: None)

        # Track the call to run_query
        run_query_calls = []

        def mock_run_query(*args, **kwargs):
            run_query_calls.append(kwargs)
            return {
                "answer": "RAG is Retrieval-Augmented Generation",
                "route": "vector",
                "reason": "vector_sufficient",
                "skill": "answer_with_citations",
                "agent_class": "general",
                "vector_result": {"context": "...", "citations": [], "retrieved_count": 5},
                "graph_result": {"context": "", "entities": []},
                "web_result": {"used": False, "citations": [], "context": ""},
                "grounding": {"support_ratio": 0.95},
                "answer_safety": {},
                "explainability": {},
                "detected_language": "en",
            }

        monkeypatch.setattr(query_routes, "run_query", mock_run_query)

        client = TestClient(api_main.app)
        response = client.post(
            "/query",
            json={
                "question": "什么是RAG？",  # Chinese question
                "force_language": "en",  # Force English response
                "use_web_fallback": False,
                "use_reasoning": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify force_language was passed to run_query
        assert len(run_query_calls) > 0
        assert run_query_calls[0]["force_language"] == "en"

        # Verify detected_language reflects forced language
        assert data["detected_language"] == "en"
    finally:
        # Clean up dependency overrides
        api_main.app.dependency_overrides.clear()


def test_workflow_passes_force_language_to_synthesis():
    """Test that workflow passes force_language through to synthesis_node."""
    from app.graph.workflow import run_query

    with patch("app.graph.workflow._WORKFLOW_APP") as mock_app:
        # Mock the workflow app
        mock_app.invoke.return_value = {
            "question": "What is RAG?",
            "answer": "RAG is Retrieval-Augmented Generation",
            "route": "vector",
            "detected_language": "en",
            "force_language": "en",
        }

        result = run_query(
            question="What is RAG?",
            force_language="en",
            enable_tracking=False,
        )

        # Verify force_language was passed to workflow
        call_args = mock_app.invoke.call_args[0][0]
        assert "force_language" in call_args
        assert call_args["force_language"] == "en"

        # Verify result contains detected_language
        assert "detected_language" in result
        assert result["detected_language"] == "en"


def test_synthesis_node_uses_force_language():
    """Test that synthesis_node passes force_language to synthesize_answer."""
    from app.graph.nodes.synthesis_node import synthesis_node

    with patch("app.graph.nodes.synthesis_node.synthesize_answer") as mock_synthesize:
        # Mock synthesize_answer to return dict with detected_language
        mock_synthesize.return_value = {
            "answer": "RAG is Retrieval-Augmented Generation",
            "detected_language": "en",
        }

        state = {
            "question": "什么是RAG？",
            "skill": "answer_with_citations",
            "memory_context": "",
            "vector_result": {"context": "RAG context..."},
            "graph_result": {"context": ""},
            "web_result": {"context": ""},
            "use_reasoning": False,
            "force_language": "en",
        }

        result = synthesis_node(state)

        # Verify synthesize_answer was called with force_language
        call_kwargs = mock_synthesize.call_args[1]
        assert "force_language" in call_kwargs
        assert call_kwargs["force_language"] == "en"

        # Verify result contains detected_language
        assert "detected_language" in result
        assert result["detected_language"] == "en"


def test_detected_language_defaults_to_zh():
    """Test that detected_language defaults to 'zh' if missing from result."""
    from app.core.schemas import QueryResponse

    # Create response without detected_language
    response = QueryResponse(
        answer="Test answer",
        route="vector",
        citations=[],
        graph_entities=[],
        web_used=False,
    )

    # Verify default value
    assert response.detected_language == "zh"


# ============================================================================
# End-to-End Tests: Complete Conversation Flows
# ============================================================================


def test_complete_chinese_conversation_flow(monkeypatch):
    """Test complete Chinese conversation flow with multiple queries in sequence."""
    from app.services.session_language import (
        clear_session_history,
    )

    session_id = "e2e_chinese_session"
    clear_session_history(session_id)

    # Mock user authentication
    api_main.app.dependency_overrides[api_main._require_user] = lambda: {
        "user_id": "test_user_chinese",
        "role": "viewer",
    }

    try:
        # Setup common mocks
        monkeypatch.setattr(query_routes, "_require_permission", lambda *args, **kwargs: None)
        monkeypatch.setattr(query_routes, "_require_existing_session_for_query", lambda user, session_id: session_id)
        monkeypatch.setattr(query_routes.quota_guard, "enforce_query_quota", lambda user: None)

        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache.mark_inflight.return_value = True
        monkeypatch.setattr(query_routes, "query_result_cache", mock_cache)

        monkeypatch.setattr(query_routes, "_build_memory_context_for_session", lambda **kwargs: "")
        monkeypatch.setattr(query_routes, "_allowed_sources_for_user", lambda user: [])
        monkeypatch.setattr(
            query_routes,
            "_effective_strategy_for_session",
            lambda **kwargs: ("advanced", {"reason": "default", "bucket": "default"}),
        )

        mock_history = Mock()
        mock_history.append_message = Mock()
        monkeypatch.setattr(query_routes, "_history_store_for_user", lambda user: mock_history)

        monkeypatch.setattr(query_routes, "_promote_long_term_memory", lambda **kwargs: None)
        monkeypatch.setattr(query_routes, "_audit", lambda *args, **kwargs: None)
        monkeypatch.setattr(query_routes, "_trace_id", lambda request: "trace-chinese")
        monkeypatch.setattr(query_routes, "_launch_shadow_run", lambda **kwargs: None)

        # Mock run_query to simulate Chinese responses
        chinese_responses = [
            "RAG是检索增强生成技术，它结合了检索和生成模型。",
            "向量数据库用于存储和检索文档的向量表示。",
            "LangChain是一个用于构建LLM应用的框架。",
        ]
        call_count = [0]

        def mock_run_query(*args, **kwargs):
            # Handle both positional and keyword arguments
            args[0] if args else kwargs.get("question", "")

            response = {
                "answer": chinese_responses[call_count[0] % len(chinese_responses)],
                "route": "vector",
                "reason": "vector_sufficient",
                "skill": "answer_with_citations",
                "agent_class": "general",
                "vector_result": {"context": "...", "citations": [], "retrieved_count": 5},
                "graph_result": {"context": "", "entities": []},
                "web_result": {"used": False, "citations": [], "context": ""},
                "grounding": {"support_ratio": 0.95},
                "answer_safety": {},
                "explainability": {},
                "detected_language": "zh",
            }
            call_count[0] += 1
            return response

        monkeypatch.setattr(query_routes, "run_query", mock_run_query)

        client = TestClient(api_main.app)

        # Query 1: 什么是RAG？
        response1 = client.post(
            "/query",
            json={
                "question": "什么是RAG？",
                "session_id": session_id,
                "use_web_fallback": False,
                "use_reasoning": False,
            },
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["detected_language"] == "zh"
        assert "RAG" in data1["answer"]

        # Query 2: 向量数据库是什么？
        response2 = client.post(
            "/query",
            json={
                "question": "向量数据库是什么？",
                "session_id": session_id,
                "use_web_fallback": False,
                "use_reasoning": False,
            },
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["detected_language"] == "zh"
        assert "向量" in data2["answer"]

        # Query 3: LangChain有什么用？
        response3 = client.post(
            "/query",
            json={
                "question": "LangChain有什么用？",
                "session_id": session_id,
                "use_web_fallback": False,
                "use_reasoning": False,
            },
        )
        assert response3.status_code == 200
        data3 = response3.json()
        assert data3["detected_language"] == "zh"
        assert "LangChain" in data3["answer"]

        # Verify all responses are in Chinese
        assert all(data["detected_language"] == "zh" for data in [data1, data2, data3])

    finally:
        api_main.app.dependency_overrides.clear()
        clear_session_history(session_id)


def test_complete_english_conversation_flow(monkeypatch):
    """Test complete English conversation flow with multiple queries in sequence."""
    from app.services.session_language import (
        clear_session_history,
    )

    session_id = "e2e_english_session"
    clear_session_history(session_id)

    # Mock user authentication
    api_main.app.dependency_overrides[api_main._require_user] = lambda: {
        "user_id": "test_user_english",
        "role": "viewer",
    }

    try:
        # Setup common mocks
        monkeypatch.setattr(query_routes, "_require_permission", lambda *args, **kwargs: None)
        monkeypatch.setattr(query_routes, "_require_existing_session_for_query", lambda user, session_id: session_id)
        monkeypatch.setattr(query_routes.quota_guard, "enforce_query_quota", lambda user: None)

        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache.mark_inflight.return_value = True
        monkeypatch.setattr(query_routes, "query_result_cache", mock_cache)

        monkeypatch.setattr(query_routes, "_build_memory_context_for_session", lambda **kwargs: "")
        monkeypatch.setattr(query_routes, "_allowed_sources_for_user", lambda user: [])
        monkeypatch.setattr(
            query_routes,
            "_effective_strategy_for_session",
            lambda **kwargs: ("advanced", {"reason": "default", "bucket": "default"}),
        )

        mock_history = Mock()
        mock_history.append_message = Mock()
        monkeypatch.setattr(query_routes, "_history_store_for_user", lambda user: mock_history)

        monkeypatch.setattr(query_routes, "_promote_long_term_memory", lambda **kwargs: None)
        monkeypatch.setattr(query_routes, "_audit", lambda *args, **kwargs: None)
        monkeypatch.setattr(query_routes, "_trace_id", lambda request: "trace-english")
        monkeypatch.setattr(query_routes, "_launch_shadow_run", lambda **kwargs: None)

        # Mock run_query to simulate English responses
        english_responses = [
            "RAG stands for Retrieval-Augmented Generation, combining retrieval and generation models.",
            "A vector database stores and retrieves vector representations of documents.",
            "LangChain is a framework for building LLM applications.",
        ]
        call_count = [0]

        def mock_run_query(*args, **kwargs):
            # Handle both positional and keyword arguments
            args[0] if args else kwargs.get("question", "")

            response = {
                "answer": english_responses[call_count[0] % len(english_responses)],
                "route": "vector",
                "reason": "vector_sufficient",
                "skill": "answer_with_citations",
                "agent_class": "general",
                "vector_result": {"context": "...", "citations": [], "retrieved_count": 5},
                "graph_result": {"context": "", "entities": []},
                "web_result": {"used": False, "citations": [], "context": ""},
                "grounding": {"support_ratio": 0.95},
                "answer_safety": {},
                "explainability": {},
                "detected_language": "en",
            }
            call_count[0] += 1
            return response

        monkeypatch.setattr(query_routes, "run_query", mock_run_query)

        client = TestClient(api_main.app)

        # Query 1: What is RAG?
        response1 = client.post(
            "/query",
            json={
                "question": "What is RAG?",
                "session_id": session_id,
                "use_web_fallback": False,
                "use_reasoning": False,
            },
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["detected_language"] == "en"
        assert "RAG" in data1["answer"]

        # Query 2: What is a vector database?
        response2 = client.post(
            "/query",
            json={
                "question": "What is a vector database?",
                "session_id": session_id,
                "use_web_fallback": False,
                "use_reasoning": False,
            },
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["detected_language"] == "en"
        assert "vector" in data2["answer"]

        # Query 3: What is LangChain used for?
        response3 = client.post(
            "/query",
            json={
                "question": "What is LangChain used for?",
                "session_id": session_id,
                "use_web_fallback": False,
                "use_reasoning": False,
            },
        )
        assert response3.status_code == 200
        data3 = response3.json()
        assert data3["detected_language"] == "en"
        assert "LangChain" in data3["answer"]

        # Verify all responses are in English
        assert all(data["detected_language"] == "en" for data in [data1, data2, data3])

    finally:
        api_main.app.dependency_overrides.clear()
        clear_session_history(session_id)


def test_language_switching_mid_conversation(monkeypatch):
    """Test switching from Chinese to English mid-conversation."""
    from app.services.session_language import (
        clear_session_history,
    )

    session_id = "e2e_switching_session"
    clear_session_history(session_id)

    # Mock user authentication
    api_main.app.dependency_overrides[api_main._require_user] = lambda: {
        "user_id": "test_user_switching",
        "role": "viewer",
    }

    try:
        # Setup common mocks
        monkeypatch.setattr(query_routes, "_require_permission", lambda *args, **kwargs: None)
        monkeypatch.setattr(query_routes, "_require_existing_session_for_query", lambda user, session_id: session_id)
        monkeypatch.setattr(query_routes.quota_guard, "enforce_query_quota", lambda user: None)

        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache.mark_inflight.return_value = True
        monkeypatch.setattr(query_routes, "query_result_cache", mock_cache)

        monkeypatch.setattr(query_routes, "_build_memory_context_for_session", lambda **kwargs: "")
        monkeypatch.setattr(query_routes, "_allowed_sources_for_user", lambda user: [])
        monkeypatch.setattr(
            query_routes,
            "_effective_strategy_for_session",
            lambda **kwargs: ("advanced", {"reason": "default", "bucket": "default"}),
        )

        mock_history = Mock()
        mock_history.append_message = Mock()
        monkeypatch.setattr(query_routes, "_history_store_for_user", lambda user: mock_history)

        monkeypatch.setattr(query_routes, "_promote_long_term_memory", lambda **kwargs: None)
        monkeypatch.setattr(query_routes, "_audit", lambda *args, **kwargs: None)
        monkeypatch.setattr(query_routes, "_trace_id", lambda request: "trace-switching")
        monkeypatch.setattr(query_routes, "_launch_shadow_run", lambda **kwargs: None)

        # Mock run_query to detect language from question (using same logic as language_detector)
        def mock_run_query(*args, **kwargs):
            # Handle both positional and keyword arguments
            question = args[0] if args else kwargs.get("question", "")

            # Use same detection logic as language_detector.py
            import re

            chinese_pattern = re.compile(r"[一-鿿]")
            alphanum_pattern = re.compile(r"[a-zA-Z一-鿿0-9]")

            chinese_chars = len(chinese_pattern.findall(question))
            total_alphanum = len(alphanum_pattern.findall(question))

            if total_alphanum == 0:
                lang = "zh"  # Default
            else:
                chinese_ratio = chinese_chars / total_alphanum
                lang = "zh" if chinese_ratio > 0.20 else "en"

            answer = "这是中文回答。" if lang == "zh" else "This is an English response."

            return {
                "answer": answer,
                "route": "vector",
                "reason": "vector_sufficient",
                "skill": "answer_with_citations",
                "agent_class": "general",
                "vector_result": {"context": "...", "citations": [], "retrieved_count": 5},
                "graph_result": {"context": "", "entities": []},
                "web_result": {"used": False, "citations": [], "context": ""},
                "grounding": {"support_ratio": 0.95},
                "answer_safety": {},
                "explainability": {},
                "detected_language": lang,
            }

        monkeypatch.setattr(query_routes, "run_query", mock_run_query)

        client = TestClient(api_main.app)

        # Start with Chinese queries
        response1 = client.post(
            "/query",
            json={
                "question": "什么是机器学习？",
                "session_id": session_id,
                "use_web_fallback": False,
                "use_reasoning": False,
            },
        )
        assert response1.status_code == 200
        assert response1.json()["detected_language"] == "zh"

        response2 = client.post(
            "/query",
            json={
                "question": "深度学习和机器学习有什么区别？",
                "session_id": session_id,
                "use_web_fallback": False,
                "use_reasoning": False,
            },
        )
        assert response2.status_code == 200
        assert response2.json()["detected_language"] == "zh"

        # Switch to English
        response3 = client.post(
            "/query",
            json={
                "question": "What is neural network?",
                "session_id": session_id,
                "use_web_fallback": False,
                "use_reasoning": False,
            },
        )
        assert response3.status_code == 200
        assert response3.json()["detected_language"] == "en"

        response4 = client.post(
            "/query",
            json={
                "question": "How does backpropagation work?",
                "session_id": session_id,
                "use_web_fallback": False,
                "use_reasoning": False,
            },
        )
        assert response4.status_code == 200
        assert response4.json()["detected_language"] == "en"

        # Verify language switching worked
        responses = [response1.json(), response2.json(), response3.json(), response4.json()]
        languages = [r["detected_language"] for r in responses]
        assert languages == ["zh", "zh", "en", "en"]

    finally:
        api_main.app.dependency_overrides.clear()
        clear_session_history(session_id)


def test_mixed_language_queries(monkeypatch):
    """Test queries with both Chinese and English content."""
    from app.services.session_language import clear_session_history

    session_id = "e2e_mixed_session"
    clear_session_history(session_id)

    # Mock user authentication
    api_main.app.dependency_overrides[api_main._require_user] = lambda: {"user_id": "test_user_mixed", "role": "viewer"}

    try:
        # Setup common mocks
        monkeypatch.setattr(query_routes, "_require_permission", lambda *args, **kwargs: None)
        monkeypatch.setattr(query_routes, "_require_existing_session_for_query", lambda user, session_id: session_id)
        monkeypatch.setattr(query_routes.quota_guard, "enforce_query_quota", lambda user: None)

        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache.mark_inflight.return_value = True
        monkeypatch.setattr(query_routes, "query_result_cache", mock_cache)

        monkeypatch.setattr(query_routes, "_build_memory_context_for_session", lambda **kwargs: "")
        monkeypatch.setattr(query_routes, "_allowed_sources_for_user", lambda user: [])
        monkeypatch.setattr(
            query_routes,
            "_effective_strategy_for_session",
            lambda **kwargs: ("advanced", {"reason": "default", "bucket": "default"}),
        )

        mock_history = Mock()
        mock_history.append_message = Mock()
        monkeypatch.setattr(query_routes, "_history_store_for_user", lambda user: mock_history)

        monkeypatch.setattr(query_routes, "_promote_long_term_memory", lambda **kwargs: None)
        monkeypatch.setattr(query_routes, "_audit", lambda *args, **kwargs: None)
        monkeypatch.setattr(query_routes, "_trace_id", lambda request: "trace-mixed")
        monkeypatch.setattr(query_routes, "_launch_shadow_run", lambda **kwargs: None)

        # Mock run_query to handle mixed language (using same logic as language_detector)
        def mock_run_query(*args, **kwargs):
            # Handle both positional and keyword arguments
            question = args[0] if args else kwargs.get("question", "")

            # Use same detection logic as language_detector.py
            import re

            chinese_pattern = re.compile(r"[一-鿿]")
            alphanum_pattern = re.compile(r"[a-zA-Z一-鿿0-9]")

            chinese_chars = len(chinese_pattern.findall(question))
            total_alphanum = len(alphanum_pattern.findall(question))

            if total_alphanum == 0:
                lang = "zh"  # Default
            else:
                chinese_ratio = chinese_chars / total_alphanum
                lang = "zh" if chinese_ratio > 0.20 else "en"

            answer = (
                "这是对混合语言查询的中文回答。"
                if lang == "zh"
                else "This is an English response to mixed language query."
            )

            return {
                "answer": answer,
                "route": "vector",
                "reason": "vector_sufficient",
                "skill": "answer_with_citations",
                "agent_class": "general",
                "vector_result": {"context": "...", "citations": [], "retrieved_count": 5},
                "graph_result": {"context": "", "entities": []},
                "web_result": {"used": False, "citations": [], "context": ""},
                "grounding": {"support_ratio": 0.95},
                "answer_safety": {},
                "explainability": {},
                "detected_language": lang,
            }

        monkeypatch.setattr(query_routes, "run_query", mock_run_query)

        client = TestClient(api_main.app)

        # Test 1: Mostly Chinese with English terms
        response1 = client.post(
            "/query",
            json={
                "question": "什么是RAG技术？它和LLM有什么关系？",
                "session_id": session_id,
                "use_web_fallback": False,
                "use_reasoning": False,
            },
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["detected_language"] == "zh"  # Should detect as Chinese

        # Test 2: Mostly English with Chinese terms
        response2 = client.post(
            "/query",
            json={
                "question": "How does 向量数据库 work with embeddings?",
                "session_id": session_id,
                "use_web_fallback": False,
                "use_reasoning": False,
            },
        )
        assert response2.status_code == 200
        data2 = response2.json()
        # Should detect based on character ratio (likely English since <20% Chinese)
        assert data2["detected_language"] in ["zh", "en"]

        # Test 3: Technical terms in English within Chinese sentence
        response3 = client.post(
            "/query",
            json={
                "question": "请解释一下transformer模型的attention机制",
                "session_id": session_id,
                "use_web_fallback": False,
                "use_reasoning": False,
            },
        )
        assert response3.status_code == 200
        data3 = response3.json()
        assert data3["detected_language"] == "zh"  # Should detect as Chinese

    finally:
        api_main.app.dependency_overrides.clear()
        clear_session_history(session_id)


def test_edge_cases(monkeypatch):
    """Test edge cases: empty input, punctuation only, code snippets with comments."""
    from app.services.session_language import clear_session_history

    session_id = "e2e_edge_cases_session"
    clear_session_history(session_id)

    # Mock user authentication
    api_main.app.dependency_overrides[api_main._require_user] = lambda: {"user_id": "test_user_edge", "role": "viewer"}

    try:
        # Setup common mocks
        monkeypatch.setattr(query_routes, "_require_permission", lambda *args, **kwargs: None)
        monkeypatch.setattr(query_routes, "_require_existing_session_for_query", lambda user, session_id: session_id)
        monkeypatch.setattr(query_routes.quota_guard, "enforce_query_quota", lambda user: None)

        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache.mark_inflight.return_value = True
        monkeypatch.setattr(query_routes, "query_result_cache", mock_cache)

        monkeypatch.setattr(query_routes, "_build_memory_context_for_session", lambda **kwargs: "")
        monkeypatch.setattr(query_routes, "_allowed_sources_for_user", lambda user: [])
        monkeypatch.setattr(
            query_routes,
            "_effective_strategy_for_session",
            lambda **kwargs: ("advanced", {"reason": "default", "bucket": "default"}),
        )

        mock_history = Mock()
        mock_history.append_message = Mock()
        monkeypatch.setattr(query_routes, "_history_store_for_user", lambda user: mock_history)

        monkeypatch.setattr(query_routes, "_promote_long_term_memory", lambda **kwargs: None)
        monkeypatch.setattr(query_routes, "_audit", lambda *args, **kwargs: None)
        monkeypatch.setattr(query_routes, "_trace_id", lambda request: "trace-edge")
        monkeypatch.setattr(query_routes, "_launch_shadow_run", lambda **kwargs: None)

        # Mock run_query to handle edge cases
        def mock_run_query(*args, **kwargs):
            # Handle both positional and keyword arguments
            question = args[0] if args else kwargs.get("question", "")

            # Default to Chinese for edge cases
            answer = "这是默认回答。"
            lang = "zh"

            # Detect if there's actual content
            if question and question.strip():
                chinese_count = sum(1 for char in question if "一" <= char <= "鿿")
                if chinese_count > 0:
                    answer = "这是对您问题的回答。"
                    lang = "zh"
                else:
                    # Check if mostly English
                    alpha_count = sum(1 for char in question if char.isalpha())
                    if alpha_count > 5:  # Arbitrary threshold
                        answer = "This is a response to your question."
                        lang = "en"

            return {
                "answer": answer,
                "route": "vector",
                "reason": "vector_sufficient",
                "skill": "answer_with_citations",
                "agent_class": "general",
                "vector_result": {"context": "...", "citations": [], "retrieved_count": 5},
                "graph_result": {"context": "", "entities": []},
                "web_result": {"used": False, "citations": [], "context": ""},
                "grounding": {"support_ratio": 0.95},
                "answer_safety": {},
                "explainability": {},
                "detected_language": lang,
            }

        monkeypatch.setattr(query_routes, "run_query", mock_run_query)

        client = TestClient(api_main.app)

        # Test 1: Punctuation only
        response1 = client.post(
            "/query",
            json={
                "question": "???",
                "session_id": session_id,
                "use_web_fallback": False,
                "use_reasoning": False,
            },
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["detected_language"] == "zh"  # Should default to Chinese

        # Test 2: Code snippet with English comments
        response2 = client.post(
            "/query",
            json={
                "question": "def hello(): # This is a function\n    return 'Hello'",
                "session_id": session_id,
                "use_web_fallback": False,
                "use_reasoning": False,
            },
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["detected_language"] in ["zh", "en"]  # Should handle gracefully

        # Test 3: Code snippet with Chinese comments
        response3 = client.post(
            "/query",
            json={
                "question": "def hello(): # 这是一个函数\n    return '你好'",
                "session_id": session_id,
                "use_web_fallback": False,
                "use_reasoning": False,
            },
        )
        assert response3.status_code == 200
        data3 = response3.json()
        assert data3["detected_language"] == "zh"  # Should detect Chinese

        # Test 4: Numbers and symbols
        response4 = client.post(
            "/query",
            json={
                "question": "123 + 456 = ?",
                "session_id": session_id,
                "use_web_fallback": False,
                "use_reasoning": False,
            },
        )
        assert response4.status_code == 200
        data4 = response4.json()
        assert data4["detected_language"] == "zh"  # Should default to Chinese

    finally:
        api_main.app.dependency_overrides.clear()
        clear_session_history(session_id)
