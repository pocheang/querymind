"""
End-to-end workflow for advanced RAG processing.
"""

import logging
from typing import Optional, Dict, Any, List
from app.models.advanced_rag_models import AdvancedRAGResult, SubQueryResult
from app.agents.enhanced_router_agent import EnhancedRouterAgent
from app.agents.enhanced_vector_rag_agent import EnhancedVectorRAGAgent
from app.core.models import get_chat_model

logger = logging.getLogger(__name__)


class AdvancedRAGWorkflow:
    """Workflow for processing queries with advanced RAG techniques."""

    def __init__(
        self,
        enable_decomposition: bool = False,
        enable_self_rag: bool = False
    ):
        """
        Initialize advanced RAG workflow.

        Args:
            enable_decomposition: Enable query decomposition
            enable_self_rag: Enable Self-RAG evaluation
        """
        self.enable_decomposition = enable_decomposition
        self.enable_self_rag = enable_self_rag

        # Initialize LLM client
        self.llm_client = get_chat_model()

        # Initialize agents
        self.router_agent = EnhancedRouterAgent(
            self.llm_client,
            enable_query_decomposition=enable_decomposition
        )
        self.vector_rag_agent = EnhancedVectorRAGAgent(
            self.llm_client,
            enable_self_rag=enable_self_rag
        )

        logger.info(
            f"Advanced RAG workflow initialized: "
            f"decomposition={enable_decomposition}, self_rag={enable_self_rag}"
        )

    async def process_query(
        self,
        query: str,
        allowed_sources: Optional[List[str]] = None,
        retrieval_strategy: Optional[str] = None
    ) -> AdvancedRAGResult:
        """
        Process query with advanced RAG techniques.

        Args:
            query: User query
            allowed_sources: Optional list of allowed sources
            retrieval_strategy: Optional retrieval strategy

        Returns:
            AdvancedRAGResult with complete processing results
        """
        metadata = {
            "decomposition_enabled": self.enable_decomposition,
            "self_rag_enabled": self.enable_self_rag,
        }

        # Step 1: Route with optional decomposition
        routing_result = await self.router_agent.route_with_decomposition(query)
        decomposed_query = routing_result.get("decomposed_query")
        route_decisions = routing_result.get("route_decisions", [])

        metadata["route_decisions"] = [
            {
                "query": rd["query"],
                "route": rd["decision"].route,
                "skill": rd["decision"].skill,
            }
            for rd in route_decisions
        ]

        # Step 2: Process each query (or sub-query)
        sub_query_results = []
        for route_decision in route_decisions:
            sub_query = route_decision["query"]
            decision = route_decision["decision"]

            # Retrieve with Self-RAG evaluation
            retrieval_result = await self.vector_rag_agent.retrieve_with_evaluation(
                sub_query,
                allowed_sources=allowed_sources,
                retrieval_strategy=retrieval_strategy
            )

            # Use filtered context if available, otherwise use original
            context = retrieval_result.get("filtered_context") or retrieval_result.get("context")
            citations = retrieval_result.get("filtered_citations") or retrieval_result.get("citations")

            # Generate answer (simplified - in production, use proper generation)
            answer = await self._generate_answer(sub_query, context)

            # Create sub-query result
            sub_result = SubQueryResult(
                sub_query=sub_query,
                documents=[
                    {
                        "source": c["source"],
                        "content": c["content"],
                        "metadata": c.get("metadata", {})
                    }
                    for c in citations
                ],
                answer=answer,
                relevance_scores=retrieval_result.get("relevance_scores")
            )
            sub_query_results.append(sub_result)

        # Step 3: Synthesize final answer
        if len(sub_query_results) > 1:
            final_answer = await self._synthesize_answers(query, sub_query_results)
        else:
            final_answer = sub_query_results[0].answer if sub_query_results else "No answer generated."

        # Step 4: Evaluate final answer quality (if Self-RAG enabled)
        answer_quality = None
        if self.enable_self_rag:
            all_citations = []
            for sub_result in sub_query_results:
                all_citations.extend([
                    {
                        "source": doc["source"],
                        "content": doc["content"],
                        "metadata": doc.get("metadata", {})
                    }
                    for doc in sub_result.documents
                ])

            quality_dict = await self.vector_rag_agent.evaluate_answer_quality(
                query, final_answer, all_citations
            )
            if quality_dict:
                from app.models.advanced_rag_models import AnswerQuality
                answer_quality = AnswerQuality(**quality_dict)

        return AdvancedRAGResult(
            query=query,
            decomposed_query=decomposed_query,
            sub_query_results=sub_query_results,
            final_answer=final_answer,
            answer_quality=answer_quality,
            metadata=metadata
        )

    async def _generate_answer(self, query: str, context: str) -> str:
        """
        Generate answer from context.

        Args:
            query: User query
            context: Retrieved context

        Returns:
            Generated answer
        """
        if not context or not context.strip():
            return "I don't have enough information to answer this question."

        prompt = f"""Based on the following context, answer the question.

Context:
{context}

Question: {query}

Answer:"""

        try:
            response = await self.llm_client.ainvoke(prompt)
            answer = response.content if hasattr(response, "content") else str(response)
            return answer.strip()
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return f"Error generating answer: {str(e)}"

    async def _synthesize_answers(
        self, query: str, sub_results: List[SubQueryResult]
    ) -> str:
        """
        Synthesize final answer from sub-query results.

        Args:
            query: Original query
            sub_results: Results from sub-queries

        Returns:
            Synthesized final answer
        """
        # Combine sub-query answers
        combined = "\n\n".join([
            f"Sub-question: {sr.sub_query}\nAnswer: {sr.answer}"
            for sr in sub_results
        ])

        prompt = f"""Synthesize a comprehensive answer to the original question based on the following sub-answers.

Original Question: {query}

Sub-answers:
{combined}

Synthesized Answer:"""

        try:
            response = await self.llm_client.ainvoke(prompt)
            answer = response.content if hasattr(response, "content") else str(response)
            return answer.strip()
        except Exception as e:
            logger.error(f"Error synthesizing answer: {e}")
            # Fallback: concatenate sub-answers
            return "\n\n".join([sr.answer for sr in sub_results])
