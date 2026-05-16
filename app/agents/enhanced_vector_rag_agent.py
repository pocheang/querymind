"""
Enhanced vector RAG agent with Self-RAG evaluation support.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from app.agents.vector_rag_agent import run_vector_rag
from app.services.self_rag_evaluator import SelfRAGEvaluator
from app.models.advanced_rag_models import RelevanceScore, AnswerQuality

logger = logging.getLogger(__name__)


class EnhancedVectorRAGAgent:
    """Vector RAG agent with Self-RAG evaluation capability."""

    def __init__(self, llm_client, enable_self_rag: bool = None):
        """
        Initialize enhanced vector RAG agent.

        Args:
            llm_client: LLM client for Self-RAG evaluation
            enable_self_rag: Whether to enable Self-RAG evaluation
                            (defaults to ENABLE_SELF_RAG env var)
        """
        if enable_self_rag is None:
            enable_self_rag = os.getenv("ENABLE_SELF_RAG", "false").lower() == "true"

        self.enable_self_rag = enable_self_rag
        self.self_rag_evaluator = None

        if self.enable_self_rag:
            self.self_rag_evaluator = SelfRAGEvaluator(llm_client)
            logger.info("Self-RAG evaluation enabled")

    async def retrieve_with_evaluation(
        self,
        question: str,
        allowed_sources: Optional[List[str]] = None,
        retrieval_strategy: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve documents with optional Self-RAG evaluation.

        Args:
            question: User query
            allowed_sources: Optional list of allowed sources
            retrieval_strategy: Optional retrieval strategy

        Returns:
            Dictionary with retrieval results and optional evaluation
        """
        # Run standard vector RAG retrieval
        rag_result = run_vector_rag(question, allowed_sources, retrieval_strategy)

        result = {
            "question": question,
            "context": rag_result["context"],
            "citations": rag_result["citations"],
            "retrieved_count": rag_result["retrieved_count"],
            "effective_hit_count": rag_result["effective_hit_count"],
            "retrieval_diagnostics": rag_result["retrieval_diagnostics"],
            "relevance_scores": None,
            "filtered_citations": None,
        }

        # Evaluate retrieval relevance if Self-RAG is enabled
        if self.enable_self_rag and self.self_rag_evaluator:
            try:
                # Convert citations to document format for evaluation
                documents = self._citations_to_documents(rag_result["citations"])

                # Evaluate relevance
                relevance_scores = await self.self_rag_evaluator.evaluate_retrieval_relevance(
                    question, documents
                )
                result["relevance_scores"] = [score.model_dump() for score in relevance_scores]

                # Filter documents based on relevance
                filtered_docs = self.self_rag_evaluator.filter_relevant_documents(
                    documents, relevance_scores
                )

                # Convert back to citations format
                filtered_citations = self._documents_to_citations(filtered_docs)
                result["filtered_citations"] = filtered_citations
                result["filtered_count"] = len(filtered_citations)

                # Update context with filtered documents
                if filtered_citations:
                    context_blocks = []
                    for citation in filtered_citations:
                        src = citation["source"]
                        chunk = citation["content"]
                        retrieval_sources = citation["metadata"].get("retrieval_sources", [])
                        context_blocks.append(
                            f"[SOURCE: {src}]\n"
                            f"[RETRIEVAL: {','.join(retrieval_sources)}]\n"
                            f"{chunk}"
                        )
                    result["filtered_context"] = "\n\n".join(context_blocks)

                logger.info(
                    f"Self-RAG filtered {result['retrieved_count']} documents to "
                    f"{result['filtered_count']} relevant documents"
                )

            except Exception as e:
                logger.error(f"Error during Self-RAG evaluation: {e}")
                # Continue with unfiltered results on error

        return result

    async def evaluate_answer_quality(
        self,
        question: str,
        answer: str,
        citations: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate quality of generated answer.

        Args:
            question: User query
            answer: Generated answer
            citations: Source citations used for generation

        Returns:
            Dictionary with quality evaluation or None if Self-RAG disabled
        """
        if not self.enable_self_rag or not self.self_rag_evaluator:
            return None

        try:
            # Convert citations to document format
            documents = self._citations_to_documents(citations)

            # Evaluate answer quality
            quality = await self.self_rag_evaluator.evaluate_answer_quality(
                question, answer, documents
            )

            return quality.model_dump()

        except Exception as e:
            logger.error(f"Error evaluating answer quality: {e}")
            return None

    def _citations_to_documents(self, citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert citations to document format for evaluation."""
        documents = []
        for i, citation in enumerate(citations):
            doc = {
                "id": citation.get("metadata", {}).get("id", f"doc_{i}"),
                "content": citation.get("content", ""),
                "metadata": citation.get("metadata", {}),
            }
            documents.append(doc)
        return documents

    def _documents_to_citations(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert documents back to citations format."""
        citations = []
        for doc in documents:
            citation = {
                "source": doc.get("metadata", {}).get("source", "unknown"),
                "content": doc.get("content", ""),
                "metadata": doc.get("metadata", {}),
            }
            citations.append(citation)
        return citations


def run_vector_rag_with_evaluation(
    question: str,
    allowed_sources: Optional[List[str]] = None,
    retrieval_strategy: Optional[str] = None
) -> Dict[str, Any]:
    """
    Synchronous wrapper for backward compatibility.

    This function maintains the original run_vector_rag signature.

    Args:
        question: User query
        allowed_sources: Optional list of allowed sources
        retrieval_strategy: Optional retrieval strategy

    Returns:
        Dictionary with retrieval results
    """
    return run_vector_rag(question, allowed_sources, retrieval_strategy)
