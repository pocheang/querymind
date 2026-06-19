import importlib
import sys
import types


def test_run_graph_rag_uses_enhanced_path(monkeypatch):
    import app.agents.graph_rag_agent as graph_rag_agent

    graph_rag_agent = importlib.reload(graph_rag_agent)

    monkeypatch.setattr(
        graph_rag_agent,
        "get_settings",
        lambda: types.SimpleNamespace(
            graph_rag_enhanced=True,
            graph_rag_min_pdf_quality=0.3,
        ),
    )

    fake_module = types.ModuleType("app.agents.graph_rag_agent_enhanced")
    fake_module.get_document_context_for_query = lambda question, docs: {
        "quality_score": 0.8,
        "entities": ["LLM"],
        "confidence": "high",
    }

    def fake_run_graph_rag_with_pdf_context(*args, **kwargs):
        return {
            "context": "enhanced",
            "entities": ["LLM"],
            "neighbors": [],
            "paths": [],
            "graph_signal_score": 0.7,
            "confidence": "high",
            "pdf_context": {"quality_score": 0.8},
        }

    fake_module.run_graph_rag_with_pdf_context = fake_run_graph_rag_with_pdf_context
    monkeypatch.setitem(sys.modules, "app.agents.graph_rag_agent_enhanced", fake_module)

    out = graph_rag_agent.run_graph_rag(
        "What is LLM?",
        retrieved_docs=[{"content": "Large Language Model", "metadata": {"format": "markdown"}}],
    )

    assert out["context"] == "enhanced"
    assert out["pdf_context"]["quality_score"] == 0.8


def test_run_graph_rag_skips_low_quality_documents(monkeypatch):
    import app.agents.graph_rag_agent as graph_rag_agent

    graph_rag_agent = importlib.reload(graph_rag_agent)

    monkeypatch.setattr(
        graph_rag_agent,
        "get_settings",
        lambda: types.SimpleNamespace(
            graph_rag_enhanced=True,
            graph_rag_min_pdf_quality=0.3,
        ),
    )

    fake_module = types.ModuleType("app.agents.graph_rag_agent_enhanced")
    fake_module.get_document_context_for_query = lambda question, docs: {
        "quality_score": 0.1,
        "entities": [],
        "confidence": "low",
    }
    fake_module.run_graph_rag_with_pdf_context = lambda *args, **kwargs: {
        "context": "should not run",
    }
    monkeypatch.setitem(sys.modules, "app.agents.graph_rag_agent_enhanced", fake_module)

    out = graph_rag_agent.run_graph_rag(
        "What is this?",
        retrieved_docs=[{"content": "noise", "metadata": {}}],
    )

    assert out["graph_signal_score"] == 0.0
    assert out["skipped_reason"] == "low_quality_documents"
    assert out["pdf_context"]["quality_score"] == 0.1
