import threading
import importlib

from langgraph.graph import END, START, StateGraph

from app.agents.vector_rag_agent import run_vector_rag
from app.graph.nodes import (
    adaptive_planner_node,
    entry_decider_node,
    graph_decider_node,
    graph_node,
    route_by_next_step,
    router_node,
    synthesis_node,
    vector_decider_node,
    vector_node as _vector_node_impl,
    web_node,
)
from app.graph.routing.route_logic import route_after_graph, route_after_router, route_after_vector
from app.graph.state import GraphState
from app.services.hybrid_executor import submit_hybrid
from app.services.tracing import traced_span

_WORKFLOW_LOCK = threading.Lock()
_WORKFLOW_APP = None
_VECTOR_NODE_MODULE = importlib.import_module("app.graph.nodes.vector_node")


def vector_node(state: GraphState) -> GraphState:
    """Compatibility wrapper that keeps old workflow-level patch points working."""
    original_submit = _VECTOR_NODE_MODULE.submit_hybrid
    original_run_vector = _VECTOR_NODE_MODULE.run_vector_rag
    _VECTOR_NODE_MODULE.submit_hybrid = submit_hybrid
    _VECTOR_NODE_MODULE.run_vector_rag = run_vector_rag
    try:
        return _vector_node_impl(state)
    finally:
        _VECTOR_NODE_MODULE.submit_hybrid = original_submit
        _VECTOR_NODE_MODULE.run_vector_rag = original_run_vector


def build_workflow():
    graph = StateGraph(GraphState)
    graph.add_node("router", router_node)
    graph.add_node("adaptive_planner", adaptive_planner_node)
    graph.add_node("entry_decider", entry_decider_node)
    graph.add_node("vector", vector_node)
    graph.add_node("vector_decider", vector_decider_node)
    graph.add_node("graph", graph_node)
    graph.add_node("graph_decider", graph_decider_node)
    graph.add_node("web", web_node)
    graph.add_node("synthesis", synthesis_node)

    graph.add_edge(START, "router")
    graph.add_edge("router", "adaptive_planner")
    graph.add_edge("adaptive_planner", "entry_decider")
    graph.add_conditional_edges(
        "entry_decider",
        route_by_next_step,
        {
            "vector": "vector",
            "graph": "graph",
            "web": "web",
            "synthesis": "synthesis",
        },
    )
    graph.add_edge("vector", "vector_decider")
    graph.add_conditional_edges(
        "vector_decider",
        route_by_next_step,
        {"graph": "graph", "web": "web", "synthesis": "synthesis"},
    )
    graph.add_edge("graph", "graph_decider")
    graph.add_conditional_edges("graph_decider", route_by_next_step, {"web": "web", "synthesis": "synthesis"})
    graph.add_edge("web", "synthesis")
    graph.add_edge("synthesis", END)

    return graph.compile()


def run_query(
    question: str,
    use_web_fallback: bool = False,
    use_reasoning: bool = False,
    memory_context: str = "",
    allowed_sources: list[str] | None = None,
    agent_class_hint: str | None = None,
    retrieval_strategy: str | None = None,
) -> GraphState:
    global _WORKFLOW_APP
    if _WORKFLOW_APP is None:
        with _WORKFLOW_LOCK:
            if _WORKFLOW_APP is None:
                _WORKFLOW_APP = build_workflow()
    app = _WORKFLOW_APP

    if not question or not isinstance(question, str):
        raise ValueError("question is required and must be a non-empty string")

    with traced_span("workflow.run_query", {"strategy": str(retrieval_strategy or "default")}):
        return app.invoke(
            {
                "question": question,
                "memory_context": memory_context,
                "use_web_fallback": use_web_fallback,
                "use_reasoning": use_reasoning,
                "allowed_sources": allowed_sources,
                "agent_class_hint": agent_class_hint,
                "retrieval_strategy": retrieval_strategy,
            }
        )


def clear_workflow_cache() -> None:
    global _WORKFLOW_APP
    with _WORKFLOW_LOCK:
        _WORKFLOW_APP = None
