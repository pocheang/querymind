"""Safe wrapper functions for agent calls with resilience patterns."""

import logging
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from app.services.bulkhead import bulkhead
from app.services.resilience import CircuitBreakerOpenError, call_with_circuit_breaker
from app.services.retrieval_logger import RetrievalLogger, RetrievalLog
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
    start_time = time.time()
    try:
        run_vector_rag = _agent_func("app.agents.vector_rag_agent", "run_vector_rag")
        with bulkhead("retrieval"):
            result = call_with_retry(
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

        # Log successful retrieval
        retrieval_time = time.time() - start_time
        try:
            retrieval_logger = RetrievalLogger.get_instance()

            # Extract metrics from result
            citations = result.get("citations", [])
            retrieved_count = result.get("retrieved_count", 0)
            effective_hit_count = result.get("effective_hit_count", 0)

            # Extract top 3 scores from citations
            top_scores = []
            for c in citations[:3]:
                metadata = c.get("metadata", {})
                score = metadata.get("hybrid_score") or metadata.get("rerank_score") or metadata.get("dense_score") or 0.0
                top_scores.append(float(score))

            # Extract source filenames from citations
            retrieved_sources = []
            for c in citations:
                source = c.get("source", "")
                if source and source not in retrieved_sources:
                    retrieved_sources.append(source)

            retrieval_logger.log_retrieval(RetrievalLog(
                query_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                route="vector",
                query=question,
                retrieval_time=retrieval_time,
                retrieved_count=retrieved_count,
                effective_hit_count=effective_hit_count,
                top_scores=top_scores,
                retrieved_sources=retrieved_sources,
                filters={"allowed_sources": allowed_sources, "retrieval_strategy": retrieval_strategy, "agent_class": agent_class},
                success=True
            ))
        except Exception as log_error:
            logger.warning(f"Failed to log retrieval: {log_error}")

        return result
    except CircuitBreakerOpenError:
        run_vector_rag = _agent_func("app.agents.vector_rag_agent", "run_vector_rag")
        result = _call_with_supported_kwargs(
            run_vector_rag,
            question,
            allowed_sources=allowed_sources,
            retrieval_strategy=retrieval_strategy,
            agent_class=agent_class,
        )

        # Log successful retrieval (circuit breaker open path)
        retrieval_time = time.time() - start_time
        try:
            retrieval_logger = RetrievalLogger.get_instance()

            citations = result.get("citations", [])
            retrieved_count = result.get("retrieved_count", 0)
            effective_hit_count = result.get("effective_hit_count", 0)

            top_scores = []
            for c in citations[:3]:
                metadata = c.get("metadata", {})
                score = metadata.get("hybrid_score") or metadata.get("rerank_score") or metadata.get("dense_score") or 0.0
                top_scores.append(float(score))

            retrieved_sources = []
            for c in citations:
                source = c.get("source", "")
                if source and source not in retrieved_sources:
                    retrieved_sources.append(source)

            retrieval_logger.log_retrieval(RetrievalLog(
                query_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                route="vector",
                query=question,
                retrieval_time=retrieval_time,
                retrieved_count=retrieved_count,
                effective_hit_count=effective_hit_count,
                top_scores=top_scores,
                retrieved_sources=retrieved_sources,
                filters={"allowed_sources": allowed_sources, "retrieval_strategy": retrieval_strategy, "agent_class": agent_class},
                success=True
            ))
        except Exception as log_error:
            logger.warning(f"Failed to log retrieval: {log_error}")

        return result
    except Exception as e:
        logger.exception(f"Vector RAG failed for question: {question}")

        # Log failed retrieval
        retrieval_time = time.time() - start_time
        try:
            retrieval_logger = RetrievalLogger.get_instance()
            retrieval_logger.log_retrieval(RetrievalLog(
                query_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                route="vector",
                query=question,
                retrieval_time=retrieval_time,
                retrieved_count=0,
                effective_hit_count=0,
                top_scores=[],
                retrieved_sources=[],
                filters={"allowed_sources": allowed_sources, "retrieval_strategy": retrieval_strategy, "agent_class": agent_class},
                success=False,
                error_type=type(e).__name__
            ))
        except Exception as log_error:
            logger.warning(f"Failed to log retrieval: {log_error}")

        return {"context": "", "citations": [], "retrieved_count": 0, "error": f"vector_error:{type(e).__name__}"}


def safe_graph_result(question: str, allowed_sources: list[str] | None = None, agent_class: str | None = None) -> dict[str, Any]:
    """Execute graph RAG with resilience patterns."""
    start_time = time.time()
    try:
        run_graph_rag = _agent_func("app.agents.graph_rag_agent", "run_graph_rag")
        with bulkhead("neo4j"):
            result = call_with_retry(
                "stream.graph_rag",
                lambda: call_with_circuit_breaker(
                    "graph_rag.run",
                    lambda: _call_with_supported_kwargs(run_graph_rag, question, allowed_sources=allowed_sources, agent_class=agent_class),
                ),
            )

        # Log successful retrieval
        retrieval_time = time.time() - start_time
        try:
            retrieval_logger = RetrievalLogger.get_instance()

            # Extract metrics from result
            entities = result.get("entities", [])
            neighbors = result.get("neighbors", [])
            retrieved_count = len(entities) + len(neighbors)
            effective_hit_count = retrieved_count

            # Extract sources from entities and neighbors
            retrieved_sources = []
            for entity in entities:
                source = entity.get("source", "")
                if source and source not in retrieved_sources:
                    retrieved_sources.append(source)
            for neighbor in neighbors:
                source = neighbor.get("source", "")
                if source and source not in retrieved_sources:
                    retrieved_sources.append(source)

            retrieval_logger.log_retrieval(RetrievalLog(
                query_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                route="graph",
                query=question,
                retrieval_time=retrieval_time,
                retrieved_count=retrieved_count,
                effective_hit_count=effective_hit_count,
                top_scores=[],  # Graph doesn't have relevance scores
                retrieved_sources=retrieved_sources,
                filters={"allowed_sources": allowed_sources, "agent_class": agent_class},
                success=True
            ))
        except Exception as log_error:
            logger.warning(f"Failed to log retrieval: {log_error}")

        return result
    except CircuitBreakerOpenError:
        run_graph_rag = _agent_func("app.agents.graph_rag_agent", "run_graph_rag")
        result = _call_with_supported_kwargs(run_graph_rag, question, allowed_sources=allowed_sources, agent_class=agent_class)

        # Log successful retrieval (circuit breaker open path)
        retrieval_time = time.time() - start_time
        try:
            retrieval_logger = RetrievalLogger.get_instance()

            entities = result.get("entities", [])
            neighbors = result.get("neighbors", [])
            retrieved_count = len(entities) + len(neighbors)
            effective_hit_count = retrieved_count

            retrieved_sources = []
            for entity in entities:
                source = entity.get("source", "")
                if source and source not in retrieved_sources:
                    retrieved_sources.append(source)
            for neighbor in neighbors:
                source = neighbor.get("source", "")
                if source and source not in retrieved_sources:
                    retrieved_sources.append(source)

            retrieval_logger.log_retrieval(RetrievalLog(
                query_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                route="graph",
                query=question,
                retrieval_time=retrieval_time,
                retrieved_count=retrieved_count,
                effective_hit_count=effective_hit_count,
                top_scores=[],
                retrieved_sources=retrieved_sources,
                filters={"allowed_sources": allowed_sources, "agent_class": agent_class},
                success=True
            ))
        except Exception as log_error:
            logger.warning(f"Failed to log retrieval: {log_error}")

        return result
    except Exception as e:
        logger.exception(f"Graph RAG failed for question: {question}")

        # Log failed retrieval
        retrieval_time = time.time() - start_time
        try:
            retrieval_logger = RetrievalLogger.get_instance()
            retrieval_logger.log_retrieval(RetrievalLog(
                query_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                route="graph",
                query=question,
                retrieval_time=retrieval_time,
                retrieved_count=0,
                effective_hit_count=0,
                top_scores=[],
                retrieved_sources=[],
                filters={"allowed_sources": allowed_sources, "agent_class": agent_class},
                success=False,
                error_type=type(e).__name__
            ))
        except Exception as log_error:
            logger.warning(f"Failed to log retrieval: {log_error}")

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
