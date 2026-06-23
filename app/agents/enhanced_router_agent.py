"""
Enhanced router agent with query decomposition support.
"""

import logging
import os
from typing import Any

from app.agents.router_agent import RouteDecision, decide_route
from app.services.query_decomposer import QueryDecomposer

logger = logging.getLogger(__name__)


class EnhancedRouterAgent:
    """Router agent with query decomposition capability."""

    def __init__(self, llm_client, enable_query_decomposition: bool = None):
        """
        Initialize enhanced router agent.

        Args:
            llm_client: LLM client for query decomposition
            enable_query_decomposition: Whether to enable query decomposition
                                       (defaults to ENABLE_QUERY_DECOMPOSITION env var)
        """
        if enable_query_decomposition is None:
            enable_query_decomposition = os.getenv("ENABLE_QUERY_DECOMPOSITION", "false").lower() == "true"

        self.enable_query_decomposition = enable_query_decomposition
        self.query_decomposer = None

        if self.enable_query_decomposition:
            self.query_decomposer = QueryDecomposer(llm_client)
            logger.info("Query decomposition enabled")

    async def route_with_decomposition(
        self, question: str, use_reasoning: bool = False, agent_class_hint: str | None = None
    ) -> dict[str, Any]:
        """
        Route query with optional decomposition.

        Args:
            question: User query
            use_reasoning: Whether to use reasoning model for routing
            agent_class_hint: Optional hint for agent class

        Returns:
            Dictionary with routing decision and optional decomposed query
        """
        result = {
            "original_question": question,
            "decomposed_query": None,
            "route_decisions": [],
        }

        # Decompose query if enabled
        if self.enable_query_decomposition and self.query_decomposer:
            try:
                decomposed = await self.query_decomposer.decompose(question)
                result["decomposed_query"] = decomposed

                # If decomposed into multiple sub-queries, route each one
                if len(decomposed.sub_queries) > 1:
                    logger.info(f"Query decomposed into {len(decomposed.sub_queries)} sub-queries")
                    for sub_query in decomposed.sub_queries:
                        route_decision = decide_route(sub_query, use_reasoning, agent_class_hint)
                        result["route_decisions"].append({"query": sub_query, "decision": route_decision})
                    return result

            except Exception as e:
                logger.error(f"Error during query decomposition: {e}")
                # Fall through to normal routing on error

        # Normal routing (no decomposition or single query)
        route_decision = decide_route(question, use_reasoning, agent_class_hint)
        result["route_decisions"].append({"query": question, "decision": route_decision})

        return result


def route_with_decomposition_sync(
    question: str, use_reasoning: bool = False, agent_class_hint: str | None = None
) -> RouteDecision:
    """
    Synchronous wrapper for backward compatibility.

    This function maintains the original decide_route signature but can be
    extended in the future to support decomposition.

    Args:
        question: User query
        use_reasoning: Whether to use reasoning model
        agent_class_hint: Optional agent class hint

    Returns:
        RouteDecision
    """
    return decide_route(question, use_reasoning, agent_class_hint)
