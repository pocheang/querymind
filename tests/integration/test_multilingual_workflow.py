"""Integration tests for multilingual response API."""
import pytest
from unittest.mock import Mock, patch, MagicMock

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

api_main = pytest.importorskip("app.api.main")
query_routes = pytest.importorskip("app.api.routes.query")


def test_query_endpoint_auto_detect_chinese(monkeypatch):
    """Test /query endpoint auto-detects Chinese and returns detected_language."""
    # Mock user authentication using dependency_overrides
    api_main.app.dependency_overrides[api_main._require_user] = lambda: {
        "user_id": "test_user",
        "role": "viewer"
    }

    try:
        # Mock other dependencies
        monkeypatch.setattr(query_routes, "_require_permission", lambda *args, **kwargs: None)
        monkeypatch.setattr(query_routes, "_require_existing_session_for_query", lambda user, session_id: "test_session")
        monkeypatch.setattr(query_routes.quota_guard, "enforce_query_quota", lambda user: None)

        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache.mark_inflight.return_value = True
        monkeypatch.setattr(query_routes, "query_result_cache", mock_cache)

        monkeypatch.setattr(query_routes, "_build_memory_context_for_session", lambda **kwargs: "")
        monkeypatch.setattr(query_routes, "_allowed_sources_for_user", lambda user: [])
        monkeypatch.setattr(query_routes, "_effective_strategy_for_session", lambda **kwargs: ("advanced", {"reason": "default", "bucket": "default"}))

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
            }
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
    api_main.app.dependency_overrides[api_main._require_user] = lambda: {
        "user_id": "test_user",
        "role": "viewer"
    }

    try:
        # Mock other dependencies
        monkeypatch.setattr(query_routes, "_require_permission", lambda *args, **kwargs: None)
        monkeypatch.setattr(query_routes, "_require_existing_session_for_query", lambda user, session_id: "test_session")
        monkeypatch.setattr(query_routes.quota_guard, "enforce_query_quota", lambda user: None)

        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache.mark_inflight.return_value = True
        monkeypatch.setattr(query_routes, "query_result_cache", mock_cache)

        monkeypatch.setattr(query_routes, "_build_memory_context_for_session", lambda **kwargs: "")
        monkeypatch.setattr(query_routes, "_allowed_sources_for_user", lambda user: [])
        monkeypatch.setattr(query_routes, "_effective_strategy_for_session", lambda **kwargs: ("advanced", {"reason": "default", "bucket": "default"}))

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
            }
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
