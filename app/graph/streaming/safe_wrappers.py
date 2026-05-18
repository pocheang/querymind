"""Safe wrapper functions for agent calls with resilience patterns."""

import logging
import sys
from typing import Any

from app.services.bulkhead import bulkhead
from app.services.resilience import CircuitBreakerOpenError, call_with_circuit_breaker
from app.services.retry_policy import call_with_retry

logger = logging.getLogger(__name__)


def _agent_func(module_name: str, func_name: str):
    module = sys.modules.get(module_name)
    if module is None:
        module = __import__(module_name, fromlist=[func_name])
    return getattr(module, func_name)


def _call_with_supported_kwargs(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except TypeError:
        compact = {k: v for k, v in kwargs.items() if v is not None}
        if compact != kwargs:
            try:
                return fn(*args, **compact)
            except TypeError:
                pass
        return fn(*args)


def safe_vector_result(
    question: str,
    allowed_sources: list[str] | None = None,
    retrieval_strategy: str | None = None,
    agent_class: str | None = None,
) -> dict[str, Any]:
    """Execute vector RAG with resilience patterns."""
    try:
        run_vector_rag = _agent_func("app.agents.vector_rag_agent", "run_vector_rag")
        with bulkhead("retrieval"):
            return call_with_retry(
                "stream.vector_rag",
                lambda: call_with_circuit_breaker(
                    "vector_rag.run",
                    lambda: _call_with_supported_kwargs(
                        run_vector_rag,
                        question,
                        allowed_sources=allowed_sources,
                        retrieval_strategy=retrieval_strategy,
                        agent_class=agent_class,
                    ),
                ),
            )
    except CircuitBreakerOpenError:
        run_vector_rag = _agent_func("app.agents.vector_rag_agent", "run_vector_rag")
        return _call_with_supported_kwargs(
            run_vector_rag,
            question,
            allowed_sources=allowed_sources,
            retrieval_strategy=retrieval_strategy,
            agent_class=agent_class,
        )
    except Exception as e:
        logger.exception(f"Vector RAG failed for question: {question}")
        return {"context": "", "citations": [], "retrieved_count": 0, "error": f"vector_error:{type(e).__name__}"}


def safe_graph_result(question: str, allowed_sources: list[str] | None = None, agent_class: str | None = None) -> dict[str, Any]:
    """Execute graph RAG with resilience patterns."""
    try:
        run_graph_rag = _agent_func("app.agents.graph_rag_agent", "run_graph_rag")
        with bulkhead("neo4j"):
            return call_with_retry(
                "stream.graph_rag",
                lambda: call_with_circuit_breaker(
                    "graph_rag.run",
                    lambda: _call_with_supported_kwargs(run_graph_rag, question, allowed_sources=allowed_sources, agent_class=agent_class),
                ),
            )
    except CircuitBreakerOpenError:
        run_graph_rag = _agent_func("app.agents.graph_rag_agent", "run_graph_rag")
        return _call_with_supported_kwargs(run_graph_rag, question, allowed_sources=allowed_sources, agent_class=agent_class)
    except Exception as e:
        logger.exception(f"Graph RAG failed for question: {question}")
        return {"context": "", "entities": [], "neighbors": [], "error": f"graph_error:{type(e).__name__}"}


def safe_web_result(question: str) -> dict[str, Any]:
    """Execute web research with resilience patterns."""
    try:
        run_web_research = _agent_func("app.agents.web_research_agent", "run_web_research")
        with bulkhead("web"):
            return call_with_retry(
                "stream.web_research",
                lambda: call_with_circuit_breaker("web_research.run", lambda: run_web_research(question)),
            )
    except CircuitBreakerOpenError:
        run_web_research = _agent_func("app.agents.web_research_agent", "run_web_research")
        return run_web_research(question)
    except Exception as e:
        logger.exception(f"Web research failed for question: {question}")
        return {"used": False, "citations": [], "context": "", "error": f"web_error:{type(e).__name__}"}
