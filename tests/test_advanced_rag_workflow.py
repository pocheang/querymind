from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.workflow import advanced_rag_workflow as workflow_mod


@pytest.mark.asyncio
async def test_advanced_workflow_uses_graph_route_agents(monkeypatch):
    workflow = workflow_mod.AdvancedRAGWorkflow.__new__(workflow_mod.AdvancedRAGWorkflow)
    workflow.enable_decomposition = False
    workflow.enable_self_rag = False
    workflow.llm_client = None
    workflow.router_agent = SimpleNamespace(
        route_with_decomposition=AsyncMock(
            return_value={
                "decomposed_query": None,
                "route_decisions": [
                    {
                        "query": "graph question",
                        "decision": SimpleNamespace(
                            route="graph",
                            skill="compare_entities",
                            agent_class="cybersecurity",
                        ),
                    }
                ],
            }
        )
    )
    workflow.vector_rag_agent = SimpleNamespace(
        retrieve_with_evaluation=AsyncMock(side_effect=AssertionError("vector path should not run")),
        evaluate_answer_quality=AsyncMock(return_value=None),
    )

    seen = {}

    def fake_graph(question, allowed_sources=None, agent_class=None, retrieved_docs=None, enable_enhancements=None):
        seen["graph"] = {
            "question": question,
            "allowed_sources": allowed_sources,
            "agent_class": agent_class,
        }
        return {"context": "graph context", "entities": ["APT28"], "neighbors": [], "paths": []}

    def fake_synthesize(**kwargs):
        seen["synthesize"] = kwargs
        return {"answer": "graph answer", "detected_language": "en"}

    monkeypatch.setattr(workflow_mod, "run_graph_rag", fake_graph)
    monkeypatch.setattr(workflow_mod, "synthesize_answer", fake_synthesize)

    result = await workflow.process_query("graph question", allowed_sources=["allowed.md"])

    assert result.final_answer == "graph answer"
    assert seen["graph"] == {
        "question": "graph question",
        "allowed_sources": ["allowed.md"],
        "agent_class": "cybersecurity",
    }
    assert seen["synthesize"]["graph_context"] == "graph context"
    assert result.sub_query_results[0].documents[0]["source"] == "graph_context"


@pytest.mark.asyncio
async def test_advanced_workflow_hybrid_route_uses_vector_and_graph(monkeypatch):
    workflow = workflow_mod.AdvancedRAGWorkflow.__new__(workflow_mod.AdvancedRAGWorkflow)
    workflow.enable_decomposition = False
    workflow.enable_self_rag = False
    workflow.llm_client = None
    workflow.router_agent = SimpleNamespace(
        route_with_decomposition=AsyncMock(
            return_value={
                "decomposed_query": None,
                "route_decisions": [
                    {
                        "query": "hybrid question",
                        "decision": SimpleNamespace(
                            route="hybrid",
                            skill="answer_with_citations",
                            agent_class="artificial_intelligence",
                        ),
                    }
                ],
            }
        )
    )
    workflow.vector_rag_agent = SimpleNamespace(
        retrieve_with_evaluation=AsyncMock(
            return_value={
                "context": "vector context",
                "citations": [
                    {
                        "source": "doc.md",
                        "content": "chunk",
                        "metadata": {"source": "doc.md"},
                    }
                ],
                "relevance_scores": None,
            }
        ),
        evaluate_answer_quality=AsyncMock(return_value=None),
    )

    seen = {}

    def fake_graph(question, allowed_sources=None, agent_class=None, retrieved_docs=None, enable_enhancements=None):
        seen["graph"] = {
            "question": question,
            "allowed_sources": allowed_sources,
            "agent_class": agent_class,
            "retrieved_docs": retrieved_docs,
        }
        return {"context": "graph context", "entities": [], "neighbors": [], "paths": []}

    def fake_synthesize(**kwargs):
        seen["synthesize"] = kwargs
        return {"answer": "hybrid answer", "detected_language": "en"}

    monkeypatch.setattr(workflow_mod, "run_graph_rag", fake_graph)
    monkeypatch.setattr(workflow_mod, "synthesize_answer", fake_synthesize)

    result = await workflow.process_query("hybrid question", allowed_sources=["doc.md"])

    workflow.vector_rag_agent.retrieve_with_evaluation.assert_awaited_once()
    assert result.final_answer == "hybrid answer"
    assert seen["graph"]["agent_class"] == "artificial_intelligence"
    assert seen["graph"]["retrieved_docs"] == [{"content": "chunk", "metadata": {"source": "doc.md"}}]
    assert seen["synthesize"]["vector_context"] == "vector context"
    assert seen["synthesize"]["graph_context"] == "graph context"
