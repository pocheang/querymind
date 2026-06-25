"""
Enhanced RAG Workflow - Integration of all quality assurance agents.

This is the production-ready orchestration layer that combines:
- Task 2: Route Validator (validate routing decisions)
- Task 3: Retrieval Quality (async parallel evaluation)
- Task 4: Answer Validator (4-level validation cascade)
- Task 5: Quality Orchestrator (score fusion & reporting)
- Task 6: Context Tracker (multi-turn context awareness)

Performance targets:
- Average added latency: <250ms
- Fast path (high quality): <150ms
- Route retry: max 1 attempt
- Answer retry: max 1 attempt
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional

from app.agents.router_agent import decide_route, RouteDecision
from app.agents.route_validator_agent import validate_route_decision
from app.agents.retrieval_quality_agent import evaluate_retrieval_quality
from app.agents.answer_validator_agent import validate_answer
from app.agents.quality_orchestrator_agent import orchestrate_quality
from app.agents.context_tracker_agent import (
    get_context_aware_routing_hints,
    update_conversation_context,
)
from app.agents.vector_rag_agent import run_vector_rag
from app.agents.graph_rag_agent import run_graph_rag
from app.agents.quality_models import (
    QualityReport,
    RouteValidationResult,
    RetrievalQualityResult,
    AnswerValidationResult,
)
from app.core.models import get_chat_model

logger = logging.getLogger(__name__)


def _extract_entities(text: str) -> List[str]:
    """
    Simple entity extraction from text.

    Extracts capitalized words and common named entities.

    Args:
        text: Text to extract entities from

    Returns:
        List of extracted entity strings
    """
    import re

    # Extract capitalized words (potential entities)
    entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)

    # Extract Chinese entity-like patterns (2-4 characters)
    chinese_entities = re.findall(r'[一-鿿]{2,4}', text)

    # Combine and deduplicate
    all_entities = list(set(entities + chinese_entities))

    # Limit to top 10 entities
    return all_entities[:10]


class EnhancedRAGWorkflow:
    """
    Production RAG workflow with integrated quality assurance.

    Quality checkpoints:
    1. Route validation with retry (Task 2)
    2. Retrieval quality assessment (Task 3)
    3. Answer validation with regeneration (Task 4)
    4. Quality score fusion (Task 5)
    5. Context tracking for multi-turn (Task 6)
    """

    def __init__(
        self,
        max_route_retries: int = 1,
        max_answer_retries: int = 1,
        enable_context_tracking: bool = True,
    ):
        """
        Initialize Enhanced RAG Workflow.

        Args:
            max_route_retries: Maximum route retry attempts (default 1)
            max_answer_retries: Maximum answer regeneration attempts (default 1)
            enable_context_tracking: Enable multi-turn context tracking (default True)
        """
        self.max_route_retries = max_route_retries
        self.max_answer_retries = max_answer_retries
        self.enable_context_tracking = enable_context_tracking
        logger.info(
            f"EnhancedRAGWorkflow initialized: "
            f"route_retries={max_route_retries}, "
            f"answer_retries={max_answer_retries}, "
            f"context_tracking={enable_context_tracking}"
        )

    async def execute_query(
        self,
        query: str,
        user_id: str,
        session_id: str,
        allowed_sources: Optional[List[str]] = None,
        retrieval_strategy: Optional[str] = None,
        agent_class_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute complete quality-enhanced RAG pipeline.

        Args:
            query: User query text
            user_id: User identifier
            session_id: Conversation session identifier
            allowed_sources: Optional document source filter
            retrieval_strategy: Optional retrieval strategy
            agent_class_hint: Optional agent class hint

        Returns:
            Dictionary with:
            - answer: Final answer text
            - citations: List of citations
            - quality_report: Comprehensive quality assessment
            - route_used: Route that was used
            - execution_metadata: Performance metrics
        """
        start_time = time.time()
        execution_metadata = {
            "route_retry": 0,
            "answer_retry": 0,
            "retry_count": 0,
        }

        try:
            # Step 1: Get context hints from conversation history (Task 6)
            context_hints = None
            if self.enable_context_tracking:
                context_hints = get_context_aware_routing_hints(session_id, query)
                logger.debug(f"Context hints: {context_hints}")

            # Step 2: Route decision with validation and retry (Task 2)
            route_decision, route_validation = await self._route_with_validation(
                query=query,
                agent_class_hint=agent_class_hint,
                context_hints=context_hints,
                execution_metadata=execution_metadata,
            )

            # Step 3: Execute retrieval based on validated route
            retrieval_result = await self._execute_retrieval(
                query=query,
                route_decision=route_decision,
                allowed_sources=allowed_sources,
                retrieval_strategy=retrieval_strategy,
            )

            # Step 4: Assess retrieval quality in parallel (Task 3)
            retrieval_quality = await evaluate_retrieval_quality(
                query=query,
                chunks=retrieval_result["chunks"],
                metadata=retrieval_result["metadata"],
            )

            # Step 5: Generate answer with validation and retry (Task 4)
            answer, citations, answer_validation = await self._generate_answer_with_validation(
                query=query,
                context=retrieval_result["context"],
                citations=retrieval_result["citations"],
                route=route_decision.route,
                execution_metadata=execution_metadata,
            )

            # Step 6: Orchestrate quality scores (Task 5)
            total_time_ms = int((time.time() - start_time) * 1000)
            execution_metadata["total_time_ms"] = total_time_ms

            quality_report = orchestrate_quality(
                route_validation=route_validation,
                retrieval_quality=retrieval_quality,
                answer_validation=answer_validation,
                execution_metadata=execution_metadata,
            )

            # Step 7: Update conversation context (Task 6)
            if self.enable_context_tracking:
                entities = _extract_entities(query + " " + answer)
                await update_conversation_context(
                    session_id=session_id,
                    user_id=user_id,
                    query=query,
                    response=answer,
                    route=route_decision.route,
                    entities=entities,
                )

            logger.info(
                f"Enhanced RAG completed: "
                f"route={route_decision.route}, "
                f"quality={quality_report.quality_level}, "
                f"confidence={quality_report.overall_confidence:.3f}, "
                f"time={total_time_ms}ms, "
                f"retries={execution_metadata['retry_count']}"
            )

            return {
                "answer": answer,
                "citations": citations,
                "quality_report": quality_report,
                "route_used": route_decision.route,
                "route_reason": route_decision.reason,
                "skill_used": route_decision.skill,
                "agent_class": route_decision.agent_class,
                "execution_metadata": {
                    "total_time_ms": total_time_ms,
                    "validation_overhead_ms": quality_report.execution_stats.validation_overhead_ms,
                    "route_retry": execution_metadata["route_retry"],
                    "answer_retry": execution_metadata["answer_retry"],
                    "context_tracking_enabled": self.enable_context_tracking,
                },
            }

        except Exception as e:
            logger.exception(f"Enhanced RAG workflow failed: {e}")
            raise

    async def _route_with_validation(
        self,
        query: str,
        agent_class_hint: Optional[str],
        context_hints: Optional[Any],
        execution_metadata: Dict[str, Any],
    ) -> tuple[RouteDecision, RouteValidationResult]:
        """
        Route decision with validation and optional retry.

        Returns:
            Tuple of (RouteDecision, RouteValidationResult)
        """
        # Apply context hints if available
        if context_hints and context_hints.previous_route and context_hints.followup:
            logger.debug(f"Using previous route hint: {context_hints.previous_route}")
            # Context-aware routing could prefer previous route for follow-ups
            # For now, we let the router decide but log the hint

        # Initial routing decision
        route_decision = decide_route(
            question=query,
            use_reasoning=False,
            agent_class_hint=agent_class_hint,
            use_llm_intent=True,
        )

        # Validate route decision (Task 2)
        route_validation = await validate_route_decision(query, route_decision)

        # Retry logic: if validation fails and suggests alternative
        if (
            not route_validation.is_valid
            and route_validation.suggested_alternative
            and execution_metadata["route_retry"] < self.max_route_retries
        ):
            logger.warning(
                f"Route validation failed: {route_validation.validation_reason}. "
                f"Retrying with alternative: {route_validation.suggested_alternative}"
            )
            execution_metadata["route_retry"] += 1
            execution_metadata["retry_count"] += 1

            # Apply suggested alternative
            alt = route_validation.suggested_alternative
            route_decision = RouteDecision(
                route=alt["route"],
                skill=alt["skill"],
                agent_class=route_decision.agent_class,
                reason=f"retry_from_validation:{alt['reason']}",
                confidence=0.75,
            )

            # Re-validate the alternative
            route_validation = await validate_route_decision(query, route_decision)

        logger.info(
            f"Route validation: valid={route_validation.is_valid}, "
            f"confidence={route_validation.confidence:.3f}, "
            f"method={route_validation.validation_method}, "
            f"time={route_validation.execution_time_ms}ms"
        )

        return route_decision, route_validation

    async def _execute_retrieval(
        self,
        query: str,
        route_decision: RouteDecision,
        allowed_sources: Optional[List[str]],
        retrieval_strategy: Optional[str],
    ) -> Dict[str, Any]:
        """
        Execute retrieval based on route decision.

        Returns:
            Dictionary with context, citations, chunks, and metadata
        """
        route = route_decision.route

        if route == "graph":
            # Graph RAG retrieval
            graph_result = run_graph_rag(
                question=query,
                allowed_sources=allowed_sources,
            )
            return {
                "context": graph_result.get("context", ""),
                "citations": graph_result.get("citations", []),
                "chunks": self._extract_chunks_from_graph(graph_result),
                "metadata": {"route": "graph"},
            }

        elif route == "hybrid":
            # Hybrid: combine vector + graph
            vector_result = run_vector_rag(
                question=query,
                allowed_sources=allowed_sources,
                retrieval_strategy=retrieval_strategy,
                agent_class=route_decision.agent_class,
            )
            graph_result = run_graph_rag(
                question=query,
                allowed_sources=allowed_sources,
            )

            # Merge contexts
            combined_context = f"{vector_result.get('context', '')}\n\n{graph_result.get('context', '')}"
            combined_citations = vector_result.get("citations", []) + graph_result.get("citations", [])

            return {
                "context": combined_context,
                "citations": combined_citations,
                "chunks": self._extract_chunks_from_vector(vector_result),
                "metadata": {"route": "hybrid"},
            }

        else:
            # Default: vector RAG
            vector_result = run_vector_rag(
                question=query,
                allowed_sources=allowed_sources,
                retrieval_strategy=retrieval_strategy,
                agent_class=route_decision.agent_class,
            )
            return {
                "context": vector_result.get("context", ""),
                "citations": vector_result.get("citations", []),
                "chunks": self._extract_chunks_from_vector(vector_result),
                "metadata": {
                    "route": "vector",
                    "retrieved_count": vector_result.get("retrieved_count", 0),
                },
            }

    async def _generate_answer_with_validation(
        self,
        query: str,
        context: str,
        citations: List[Dict],
        route: str,
        execution_metadata: Dict[str, Any],
    ) -> tuple[str, List[Dict], AnswerValidationResult]:
        """
        Generate answer with validation and optional regeneration.

        Returns:
            Tuple of (answer, citations, AnswerValidationResult)
        """
        # Generate initial answer
        answer = await self._generate_answer(query, context, route)

        # Validate answer (Task 4)
        answer_validation = await validate_answer(
            query=query,
            answer=answer,
            source_docs=citations,
            citations=citations,
        )

        # Retry logic: regenerate if action is "regenerate"
        if (
            answer_validation.action == "regenerate"
            and execution_metadata["answer_retry"] < self.max_answer_retries
        ):
            logger.warning(
                f"Answer validation suggests regeneration: "
                f"score={answer_validation.overall_score:.3f}, "
                f"issues={len(answer_validation.issues)}"
            )
            execution_metadata["answer_retry"] += 1
            execution_metadata["retry_count"] += 1

            # Regenerate with explicit quality instructions
            answer = await self._generate_answer(
                query,
                context,
                route,
                regeneration_prompt=(
                    "Previous answer had quality issues. "
                    "Please ensure: (1) all claims are supported by context, "
                    "(2) citations are complete, (3) no speculation."
                ),
            )

            # Re-validate
            answer_validation = await validate_answer(
                query=query,
                answer=answer,
                source_docs=citations,
                citations=citations,
            )

        logger.info(
            f"Answer validation: score={answer_validation.overall_score:.3f}, "
            f"action={answer_validation.action}, "
            f"method={answer_validation.validation_method}, "
            f"time={answer_validation.execution_time_ms}ms"
        )

        return answer, citations, answer_validation

    async def _generate_answer(
        self,
        query: str,
        context: str,
        route: str,
        regeneration_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate answer using LLM.

        Args:
            query: User query
            context: Retrieved context
            route: Route used
            regeneration_prompt: Optional quality improvement instructions

        Returns:
            Generated answer text
        """
        model = get_chat_model()

        prompt = f"""You are a helpful RAG assistant. Answer the question based on the provided context.

Context:
{context}

Question: {query}

Instructions:
- Base your answer strictly on the context provided
- Cite sources when making factual claims
- If the context doesn't contain enough information, say so
- Be concise and direct
"""

        if regeneration_prompt:
            prompt += f"\n\nQuality Requirements:\n{regeneration_prompt}"

        response = await model.ainvoke(prompt)
        answer = response.content if hasattr(response, "content") else str(response)

        return answer.strip()

    def _extract_chunks_from_vector(self, vector_result: Dict[str, Any]) -> List[Dict]:
        """Extract chunks from vector RAG result for quality assessment."""
        chunks = []
        citations = vector_result.get("citations", [])

        for citation in citations:
            chunks.append({
                "content": citation.get("content", ""),
                "source": citation.get("source", ""),
                "score": citation.get("metadata", {}).get("hybrid_score", 0.5),
            })

        return chunks

    def _extract_chunks_from_graph(self, graph_result: Dict[str, Any]) -> List[Dict]:
        """Extract chunks from graph RAG result for quality assessment."""
        # Graph RAG returns entities and relations
        # Convert to chunk format for quality assessment
        chunks = []
        entities = graph_result.get("entities", [])

        for entity in entities[:10]:  # Limit to top 10
            # Handle both dict and string entities
            if isinstance(entity, dict):
                content = str(entity.get("description", entity.get("name", "")))
            else:
                content = str(entity)

            chunks.append({
                "content": content,
                "source": "graph",
                "score": 0.8,  # Graph results have implicit high relevance
            })

        return chunks
