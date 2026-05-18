"""Test that streaming responses include detected_language field."""
import pytest
from unittest.mock import patch, MagicMock


def test_streaming_final_payload_includes_detected_language():
    """Test that run_query_stream includes detected_language in final payload."""
    from app.graph.streaming.stream_processor import run_query_stream

    # Mock all the dependencies
    with patch("app.graph.streaming.stream_processor.decide_route") as mock_route, \
         patch("app.graph.streaming.stream_processor.build_adaptive_plan") as mock_plan, \
         patch("app.graph.streaming.stream_processor.is_casual_chat_query") as mock_casual, \
         patch("app.graph.streaming.stream_processor.stream_synthesize_answer") as mock_stream_synth, \
         patch("app.graph.streaming.stream_processor.apply_sentence_grounding") as mock_grounding, \
         patch("app.graph.streaming.stream_processor.sanitize_answer") as mock_sanitize, \
         patch("app.graph.streaming.stream_processor.build_explainability_report") as mock_explain, \
         patch("app.graph.streaming.stream_processor.safe_vector_result") as mock_vector:

        # Setup mocks
        mock_route.return_value = MagicMock(
            route="vector",
            reason="test_reason",
            skill="answer_with_citations",
            agent_class="general"
        )
        mock_plan.return_value = MagicMock(
            route="vector",
            reason="test_plan",
            level="L1",
            min_vector_hits=2,
            prefer_graph=False,
            prefer_web=False
        )
        mock_casual.return_value = False

        # Mock vector result
        mock_vector.return_value = {
            "context": "test context",
            "citations": [],
            "retrieved_count": 3
        }

        # Mock streaming synthesis to emit metadata with detected_language
        def mock_stream_gen(*args, **kwargs):
            # Emit metadata event with detected_language
            yield {"type": "metadata", "detected_language": "zh"}
            # Emit answer chunks
            yield {"type": "chunk", "content": "这是"}
            yield {"type": "chunk", "content": "测试"}
            yield {"type": "chunk", "content": "答案"}

        mock_stream_synth.return_value = mock_stream_gen()

        # Mock grounding and sanitization
        mock_grounding.return_value = ("这是测试答案", {"support_ratio": 0.9})
        mock_sanitize.return_value = ("这是测试答案", {})
        mock_explain.return_value = {}

        # Run the streaming query
        events = list(run_query_stream(
            question="测试问题",
            use_web_fallback=False,
            use_reasoning=False,
            force_language=""
        ))

        # Find the final "done" event
        done_events = [e for e in events if e.get("type") == "done"]
        assert len(done_events) == 1, "Should have exactly one 'done' event"

        final_payload = done_events[0]["result"]

        # Verify detected_language is in the final payload
        assert "detected_language" in final_payload, "Final payload must include detected_language"
        assert final_payload["detected_language"] == "zh", "detected_language should be 'zh'"


def test_streaming_timeout_payload_includes_detected_language():
    """Test that timeout payload includes detected_language."""
    from app.graph.streaming.stream_processor import run_query_stream

    # Mock deadline_exceeded to return True immediately
    with patch("app.graph.streaming.stream_processor.deadline_exceeded") as mock_deadline:
        mock_deadline.return_value = True

        # Run the streaming query
        events = list(run_query_stream(
            question="测试问题",
            use_web_fallback=False,
            use_reasoning=False,
            force_language="en"
        ))

        # Find the final "done" event
        done_events = [e for e in events if e.get("type") == "done"]
        assert len(done_events) == 1, "Should have exactly one 'done' event"

        timeout_payload = done_events[0]["result"]

        # Verify detected_language is in the timeout payload
        assert "detected_language" in timeout_payload, "Timeout payload must include detected_language"
        assert timeout_payload["detected_language"] == "en", "Should use force_language when provided"


def test_streaming_smalltalk_includes_detected_language():
    """Test that smalltalk fast path includes detected_language."""
    from app.graph.streaming.stream_processor import run_query_stream

    # Mock dependencies
    with patch("app.graph.streaming.stream_processor.decide_route") as mock_route, \
         patch("app.graph.streaming.stream_processor.build_adaptive_plan") as mock_plan, \
         patch("app.graph.streaming.stream_processor.is_casual_chat_query") as mock_casual, \
         patch("app.graph.streaming.stream_processor.quick_smalltalk_reply") as mock_smalltalk, \
         patch("app.graph.streaming.stream_processor.build_explainability_report") as mock_explain:

        # Setup mocks
        mock_route.return_value = MagicMock(
            route="vector",
            reason="test_reason",
            skill="smalltalk",
            agent_class="general"
        )
        mock_plan.return_value = MagicMock(
            route="vector",
            reason="test_plan",
            level="L1",
            min_vector_hits=2,
            prefer_graph=False,
            prefer_web=False
        )
        mock_casual.return_value = True
        mock_smalltalk.return_value = "你好！"
        mock_explain.return_value = {}

        # Run the streaming query
        events = list(run_query_stream(
            question="你好",
            use_web_fallback=False,
            use_reasoning=False,
            force_language=""
        ))

        # Find the final "done" event
        done_events = [e for e in events if e.get("type") == "done"]
        assert len(done_events) == 1, "Should have exactly one 'done' event"

        smalltalk_payload = done_events[0]["result"]

        # Verify detected_language is in the smalltalk payload
        assert "detected_language" in smalltalk_payload, "Smalltalk payload must include detected_language"
        assert smalltalk_payload["detected_language"] == "zh", "Should default to 'zh'"


def test_streaming_detected_language_defaults_to_zh():
    """Test that detected_language defaults to 'zh' when not detected."""
    from app.graph.streaming.stream_processor import run_query_stream

    # Mock all the dependencies
    with patch("app.graph.streaming.stream_processor.decide_route") as mock_route, \
         patch("app.graph.streaming.stream_processor.build_adaptive_plan") as mock_plan, \
         patch("app.graph.streaming.stream_processor.is_casual_chat_query") as mock_casual, \
         patch("app.graph.streaming.stream_processor.stream_synthesize_answer") as mock_stream_synth, \
         patch("app.graph.streaming.stream_processor.apply_sentence_grounding") as mock_grounding, \
         patch("app.graph.streaming.stream_processor.sanitize_answer") as mock_sanitize, \
         patch("app.graph.streaming.stream_processor.build_explainability_report") as mock_explain, \
         patch("app.graph.streaming.stream_processor.safe_vector_result") as mock_vector:

        # Setup mocks
        mock_route.return_value = MagicMock(
            route="vector",
            reason="test_reason",
            skill="answer_with_citations",
            agent_class="general"
        )
        mock_plan.return_value = MagicMock(
            route="vector",
            reason="test_plan",
            level="L1",
            min_vector_hits=2,
            prefer_graph=False,
            prefer_web=False
        )
        mock_casual.return_value = False

        # Mock vector result
        mock_vector.return_value = {
            "context": "test context",
            "citations": [],
            "retrieved_count": 3
        }

        # Mock streaming synthesis WITHOUT detected_language metadata
        def mock_stream_gen(*args, **kwargs):
            # Only emit answer chunks, no metadata
            yield {"type": "chunk", "content": "这是"}
            yield {"type": "chunk", "content": "答案"}

        mock_stream_synth.return_value = mock_stream_gen()

        # Mock grounding and sanitization
        mock_grounding.return_value = ("这是答案", {"support_ratio": 0.9})
        mock_sanitize.return_value = ("这是答案", {})
        mock_explain.return_value = {}

        # Run the streaming query with Chinese question
        events = list(run_query_stream(
            question="什么是RAG？",
            use_web_fallback=False,
            use_reasoning=False,
            force_language=""
        ))

        # Find the final "done" event
        done_events = [e for e in events if e.get("type") == "done"]
        assert len(done_events) == 1, "Should have exactly one 'done' event"

        final_payload = done_events[0]["result"]

        # Verify detected_language defaults to 'zh'
        assert "detected_language" in final_payload, "Final payload must include detected_language"
        assert final_payload["detected_language"] == "zh", "Should default to 'zh' when not detected"
