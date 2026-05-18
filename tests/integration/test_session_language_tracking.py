"""Integration tests for session language tracking."""
import pytest
from unittest.mock import MagicMock, patch
from app.graph.nodes.synthesis_node import synthesis_node
from app.graph.state import GraphState
from app.services.session_language import (
    get_language_preference,
    get_language_history,
    clear_all_history,
)


@pytest.fixture(autouse=True)
def clean_history():
    """Clear all history before and after each test."""
    clear_all_history()
    yield
    clear_all_history()


@patch('app.agents.synthesis_agent.synthesize_answer')
@patch('app.services.citation_grounding.apply_sentence_grounding')
@patch('app.services.answer_safety.sanitize_answer')
@patch('app.services.explainability.build_explainability_report')
def test_synthesis_node_updates_language_history(
    mock_explainability, mock_sanitize, mock_grounding, mock_synthesize
):
    """Test that synthesis_node updates session language history."""
    # Mock the synthesize_answer to return a controlled response
    mock_synthesize.return_value = {
        "answer": "这是一个测试答案。",
        "detected_language": "zh",
    }
    mock_grounding.return_value = ("这是一个测试答案。", {})
    mock_sanitize.return_value = ("这是一个测试答案。", {})
    mock_explainability.return_value = {}

    session_id = "test_session_integration_1"
    state: GraphState = {
        "question": "测试问题",
        "session_id": session_id,
        "vector_result": {"context": "", "citations": []},
        "graph_result": {"context": ""},
        "web_result": {"used": False, "citations": [], "context": ""},
    }

    result = synthesis_node(state)

    # Verify the language was tracked
    history = get_language_history(session_id)
    assert history == ["zh"]
    assert get_language_preference(session_id) == "zh"

    # Verify the result includes detected_language
    assert result["detected_language"] == "zh"


@patch('app.agents.synthesis_agent.synthesize_answer')
@patch('app.services.citation_grounding.apply_sentence_grounding')
@patch('app.services.answer_safety.sanitize_answer')
@patch('app.services.explainability.build_explainability_report')
def test_synthesis_node_tracks_multiple_queries(
    mock_explainability, mock_sanitize, mock_grounding, mock_synthesize
):
    """Test that synthesis_node tracks language across multiple queries."""
    mock_grounding.return_value = ("answer", {})
    mock_sanitize.return_value = ("answer", {})
    mock_explainability.return_value = {}

    session_id = "test_session_integration_2"

    # First query in Chinese
    mock_synthesize.return_value = {"answer": "中文答案", "detected_language": "zh"}
    state1: GraphState = {
        "question": "问题1",
        "session_id": session_id,
        "vector_result": {"context": "", "citations": []},
        "graph_result": {"context": ""},
        "web_result": {"used": False, "citations": [], "context": ""},
    }
    synthesis_node(state1)

    # Second query in English
    mock_synthesize.return_value = {"answer": "English answer", "detected_language": "en"}
    state2: GraphState = {
        "question": "question 2",
        "session_id": session_id,
        "vector_result": {"context": "", "citations": []},
        "graph_result": {"context": ""},
        "web_result": {"used": False, "citations": [], "context": ""},
    }
    synthesis_node(state2)

    # Third query in Chinese
    mock_synthesize.return_value = {"answer": "中文答案2", "detected_language": "zh"}
    state3: GraphState = {
        "question": "问题3",
        "session_id": session_id,
        "vector_result": {"context": "", "citations": []},
        "graph_result": {"context": ""},
        "web_result": {"used": False, "citations": [], "context": ""},
    }
    synthesis_node(state3)

    # Verify history
    history = get_language_history(session_id)
    assert history == ["zh", "en", "zh"]
    assert get_language_preference(session_id) == "zh"  # Majority is Chinese


@patch('app.agents.synthesis_agent.synthesize_answer')
@patch('app.services.citation_grounding.apply_sentence_grounding')
@patch('app.services.answer_safety.sanitize_answer')
@patch('app.services.explainability.build_explainability_report')
def test_synthesis_node_no_session_id(
    mock_explainability, mock_sanitize, mock_grounding, mock_synthesize
):
    """Test that synthesis_node handles missing session_id gracefully."""
    mock_synthesize.return_value = {
        "answer": "答案",
        "detected_language": "zh",
    }
    mock_grounding.return_value = ("答案", {})
    mock_sanitize.return_value = ("答案", {})
    mock_explainability.return_value = {}

    # State without session_id
    state: GraphState = {
        "question": "测试问题",
        "vector_result": {"context": "", "citations": []},
        "graph_result": {"context": ""},
        "web_result": {"used": False, "citations": [], "context": ""},
    }

    # Should not crash
    result = synthesis_node(state)
    assert result["detected_language"] == "zh"


@patch('app.agents.synthesis_agent.synthesize_answer')
@patch('app.services.citation_grounding.apply_sentence_grounding')
@patch('app.services.answer_safety.sanitize_answer')
@patch('app.services.explainability.build_explainability_report')
def test_synthesis_node_different_sessions_isolated(
    mock_explainability, mock_sanitize, mock_grounding, mock_synthesize
):
    """Test that different sessions maintain separate language histories."""
    mock_grounding.return_value = ("answer", {})
    mock_sanitize.return_value = ("answer", {})
    mock_explainability.return_value = {}

    session_1 = "test_session_integration_3"
    session_2 = "test_session_integration_4"

    # Session 1: Chinese queries
    mock_synthesize.return_value = {"answer": "中文", "detected_language": "zh"}
    for i in range(3):
        state: GraphState = {
            "question": f"问题{i}",
            "session_id": session_1,
            "vector_result": {"context": "", "citations": []},
            "graph_result": {"context": ""},
            "web_result": {"used": False, "citations": [], "context": ""},
        }
        synthesis_node(state)

    # Session 2: English queries
    mock_synthesize.return_value = {"answer": "English", "detected_language": "en"}
    for i in range(2):
        state: GraphState = {
            "question": f"question {i}",
            "session_id": session_2,
            "vector_result": {"context": "", "citations": []},
            "graph_result": {"context": ""},
            "web_result": {"used": False, "citations": [], "context": ""},
        }
        synthesis_node(state)

    # Verify isolation
    assert get_language_preference(session_1) == "zh"
    assert get_language_preference(session_2) == "en"
    assert get_language_history(session_1) == ["zh", "zh", "zh"]
    assert get_language_history(session_2) == ["en", "en"]


@patch('app.services.query_intent.is_casual_chat_query')
@patch('app.services.query_intent.quick_smalltalk_reply')
@patch('app.services.explainability.build_explainability_report')
def test_synthesis_node_fast_path_smalltalk(
    mock_explainability, mock_smalltalk, mock_is_casual
):
    """Test that fast path smalltalk doesn't break language tracking."""
    mock_is_casual.return_value = True
    mock_smalltalk.return_value = "你好"
    mock_explainability.return_value = {}

    session_id = "test_session_integration_5"
    state: GraphState = {
        "question": "你好",
        "session_id": session_id,
    }

    result = synthesis_node(state)

    # Fast path doesn't have detected_language, so no tracking should happen
    # This should not crash
    assert "你好" in result["answer"]  # Should contain greeting
    assert get_language_history(session_id) == []
