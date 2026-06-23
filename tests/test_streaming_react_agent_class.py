"""Tests for streaming ReAct agent_class propagation."""

from unittest.mock import MagicMock, patch

from app.graph.streaming.stream_processor import run_query_stream


def test_stream_react_passes_agent_class():
    """Test that streaming ReAct path correctly passes agent_class to run_react_agent."""
    with patch("app.graph.streaming.stream_processor.decide_route") as mock_decide:
        with patch("app.graph.streaming.stream_processor.run_react_agent") as mock_react:
            with patch("app.graph.streaming.stream_processor.build_adaptive_plan") as mock_plan:
                with patch("app.graph.streaming.stream_processor.is_casual_chat_query", return_value=False):
                    with patch("app.graph.streaming.stream_processor.should_force_web_research", return_value=False):
                        # Mock router decision
                        mock_decision = MagicMock()
                        mock_decision.route = "react"
                        mock_decision.reason = "complex query"
                        mock_decision.skill = "reasoning"
                        mock_decision.agent_class = "pdf_text"  # Important: set agent_class
                        mock_decide.return_value = mock_decision

                        # Mock adaptive plan - MUST return react route
                        mock_plan_result = MagicMock()
                        mock_plan_result.route = "react"  # This is critical
                        mock_plan_result.reason = "adaptive reason"
                        mock_plan_result.level = "advanced"
                        mock_plan_result.min_vector_hits = 3
                        mock_plan_result.prefer_graph = False
                        mock_plan_result.prefer_web = False
                        mock_plan.return_value = mock_plan_result

                        # Mock react agent result
                        mock_react.return_value = {
                            "answer": "react answer",
                            "detected_language": "zh",
                            "vector_result": {"context": "", "citations": []},
                            "graph_result": {"context": "", "entities": []},
                            "web_result": {"used": False, "citations": []},
                            "react_history": [],
                            "iterations_used": 2,
                        }

                        # Run streaming query
                        list(
                            run_query_stream(
                                question="test pdf question",
                                agent_class_hint="pdf_text",
                                allowed_sources=["test.pdf"],
                                retrieval_strategy="advanced",
                            )
                        )

                        # Verify run_react_agent was called with agent_class
                        assert mock_react.called, "run_react_agent should have been called"
                        call_kwargs = mock_react.call_args[1]

                        # This is the key assertion: agent_class should be passed
                        assert "agent_class" in call_kwargs
                        assert call_kwargs["agent_class"] == "pdf_text"

                        # Also verify other important parameters are passed
                        assert call_kwargs["allowed_sources"] == ["test.pdf"]
                        assert call_kwargs["retrieval_strategy"] == "advanced"


def test_stream_react_propagates_allowed_sources():
    """Test that streaming ReAct path propagates allowed_sources."""
    with patch("app.graph.streaming.stream_processor.decide_route") as mock_decide:
        with patch("app.graph.streaming.stream_processor.run_react_agent") as mock_react:
            with patch("app.graph.streaming.stream_processor.build_adaptive_plan") as mock_plan:
                with patch("app.graph.streaming.stream_processor.is_casual_chat_query", return_value=False):
                    with patch("app.graph.streaming.stream_processor.should_force_web_research", return_value=False):
                        # Setup mocks
                        mock_decision = MagicMock()
                        mock_decision.route = "react"
                        mock_decision.reason = "test"
                        mock_decision.skill = "test"
                        mock_decision.agent_class = "general"
                        mock_decide.return_value = mock_decision

                        mock_plan_result = MagicMock()
                        mock_plan_result.route = "react"  # Must be react
                        mock_plan_result.reason = "test"
                        mock_plan_result.level = "baseline"
                        mock_plan_result.min_vector_hits = 1
                        mock_plan_result.prefer_graph = False
                        mock_plan_result.prefer_web = False
                        mock_plan.return_value = mock_plan_result

                        mock_react.return_value = {
                            "answer": "answer",
                            "detected_language": "zh",
                            "vector_result": {},
                            "graph_result": {},
                            "web_result": {"used": False},
                            "react_history": [],
                        }

                        # Run with specific allowed_sources
                        allowed = ["doc1.pdf", "doc2.pdf"]
                        list(
                            run_query_stream(
                                question="test",
                                allowed_sources=allowed,
                            )
                        )

                        # Verify allowed_sources was passed
                        assert mock_react.called, "run_react_agent should have been called"
                        call_kwargs = mock_react.call_args[1]
                        assert call_kwargs["allowed_sources"] == allowed


def test_stream_react_propagates_retrieval_strategy():
    """Test that streaming ReAct path propagates retrieval_strategy."""
    with patch("app.graph.streaming.stream_processor.decide_route") as mock_decide:
        with patch("app.graph.streaming.stream_processor.run_react_agent") as mock_react:
            with patch("app.graph.streaming.stream_processor.build_adaptive_plan") as mock_plan:
                with patch("app.graph.streaming.stream_processor.is_casual_chat_query", return_value=False):
                    with patch("app.graph.streaming.stream_processor.should_force_web_research", return_value=False):
                        # Setup mocks
                        mock_decision = MagicMock()
                        mock_decision.route = "react"
                        mock_decision.reason = "test"
                        mock_decision.skill = "test"
                        mock_decision.agent_class = "general"
                        mock_decide.return_value = mock_decision

                        mock_plan_result = MagicMock()
                        mock_plan_result.route = "react"  # Must be react
                        mock_plan_result.reason = "test"
                        mock_plan_result.level = "baseline"
                        mock_plan_result.min_vector_hits = 1
                        mock_plan_result.prefer_graph = False
                        mock_plan_result.prefer_web = False
                        mock_plan.return_value = mock_plan_result

                        mock_react.return_value = {
                            "answer": "answer",
                            "detected_language": "zh",
                            "vector_result": {},
                            "graph_result": {},
                            "web_result": {"used": False},
                            "react_history": [],
                        }

                        # Run with specific retrieval_strategy
                        list(
                            run_query_stream(
                                question="test",
                                retrieval_strategy="safe",
                            )
                        )

                        # Verify retrieval_strategy was passed
                        assert mock_react.called, "run_react_agent should have been called"
                        call_kwargs = mock_react.call_args[1]
                        assert call_kwargs["retrieval_strategy"] == "safe"


def test_non_stream_react_also_passes_agent_class():
    """Verify non-streaming ReAct path already passes agent_class (regression check)."""
    from app.graph.nodes.react_node import react_node
    from app.graph.state import GraphState

    with patch("app.graph.nodes.react_node.run_react_agent") as mock_react:
        mock_react.return_value = {
            "answer": "test",
            "detected_language": "zh",
            "vector_result": {},
            "graph_result": {},
            "web_result": {"used": False},
        }

        state = GraphState(
            question="test",
            agent_class="pdf_text",
            allowed_sources=["test.pdf"],
            retrieval_strategy="advanced",
        )

        react_node(state)

        # Verify non-streaming path also passes agent_class
        assert mock_react.called
        call_kwargs = mock_react.call_args[1]
        assert call_kwargs.get("agent_class") == "pdf_text"
