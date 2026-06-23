"""
Fast reranker for v0.4.4 accuracy improvements.

Single-model reranking optimized for speed:
- Uses BGE-reranker-base (faster than large variants)
- GPU acceleration when available
- Pre-filtering to reduce candidates
- Text truncation to 512 tokens
- Batch processing for efficiency

Target: 200ms for 30 candidates with GPU
"""

import logging
import time

from app.core.config import get_settings
from app.services.tracing import traced_span

logger = logging.getLogger(__name__)


class FastReranker:
    """
    Fast single-model reranker optimized for speed/accuracy balance.

    Optimizations:
    1. Pre-filter: Only rerank top 30 candidates (not all 50)
    2. Truncation: Limit text to 512 tokens
    3. GPU: Use GPU acceleration when available
    4. Batching: Process in batches of 32
    5. Model: Use base variant (faster than large)

    Performance target: 200ms for 30 candidates
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-base",
        batch_size: int = 32,
        max_length: int = 512,
        device: str | None = None,
    ):
        """
        Initialize fast reranker.

        Args:
            model_name: Model to use (default: bge-reranker-base)
            batch_size: Batch size for inference
            max_length: Maximum text length in tokens
            device: Device to use ('cuda', 'cpu', or None for auto)
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.max_length = max_length
        self.device = device or self._auto_detect_device()
        self.model = None
        self.relevance_threshold = 0.3  # Filter low-relevance docs

    def _auto_detect_device(self) -> str:
        """Auto-detect best available device."""
        try:
            import torch

            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    def _load_model(self):
        """Lazy load reranker model."""
        if self.model is not None:
            return self.model

        try:
            from sentence_transformers import CrossEncoder

            logger.info(f"Loading fast reranker: {self.model_name} on {self.device}")

            self.model = CrossEncoder(
                self.model_name,
                max_length=self.max_length,
                device=self.device,
                trust_remote_code=True,
            )

            logger.info(f"Fast reranker loaded successfully on {self.device}")
            return self.model

        except ImportError as e:
            logger.warning(f"sentence-transformers not installed: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load reranker model: {e}")
            return None

    def rerank(
        self,
        query: str,
        documents: list[dict],
        top_k: int = 10,
        pre_filter_k: int = 30,
    ) -> tuple[list[dict], dict]:
        """
        Fast rerank documents with optimizations.

        Args:
            query: Search query
            documents: Documents to rerank
            top_k: Number of results to return
            pre_filter_k: Pre-filter to this many candidates before reranking

        Returns:
            Tuple of (reranked documents, diagnostics)
        """
        start_time = time.time()

        if not documents:
            return [], {"status": "no_documents", "time_ms": 0}

        with traced_span("reranking.fast_rerank", {"candidates": len(documents), "top_k": top_k}):
            # Step 1: Pre-filter to top candidates (reduces computation)
            candidates = documents[:pre_filter_k]

            # Step 2: Load model
            model = self._load_model()

            if model is None:
                # Fallback to score-based ranking
                logger.warning("Reranker unavailable, using fallback ranking")
                return self._fallback_ranking(documents, top_k, start_time)

            # Step 3: Prepare pairs (query, truncated document text)
            pairs = []
            for doc in candidates:
                text = doc.get("text", "")
                # Truncate to max_length for speed (approximate by characters)
                # ~512 tokens ≈ 2048 characters for English, ~1024 for Chinese
                truncated = text[:2048] if text else ""
                pairs.append([query, truncated])

            # Step 4: Batch inference
            try:
                scores = model.predict(
                    pairs,
                    batch_size=self.batch_size,
                    show_progress_bar=False,
                )
            except Exception as e:
                logger.error(f"Reranking inference failed: {e}")
                return self._fallback_ranking(documents, top_k, start_time)

            # Step 5: Add rerank scores to documents
            for doc, score in zip(candidates, scores, strict=False):
                doc["rerank_score"] = float(score)

            # Step 6: Filter by relevance threshold
            filtered = [doc for doc in candidates if doc.get("rerank_score", 0) >= self.relevance_threshold]

            # If too few results, lower threshold
            if len(filtered) < 3:
                logger.info(f"Only {len(filtered)} docs above threshold, keeping top 3")
                sorted_candidates = sorted(candidates, key=lambda x: x.get("rerank_score", 0), reverse=True)
                filtered = sorted_candidates[: min(3, len(sorted_candidates))]
            else:
                # Sort filtered results
                filtered.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)

            # Step 7: Return top_k
            results = filtered[:top_k]

            elapsed_ms = (time.time() - start_time) * 1000

            diagnostics = {
                "status": "success",
                "time_ms": round(elapsed_ms, 2),
                "model": self.model_name,
                "device": self.device,
                "pre_filter_count": len(candidates),
                "filtered_count": len(filtered),
                "final_count": len(results),
                "avg_score": round(sum(d.get("rerank_score", 0) for d in results) / len(results), 3) if results else 0,
                "min_score": round(min((d.get("rerank_score", 0) for d in results), default=0), 3),
                "max_score": round(max((d.get("rerank_score", 0) for d in results), default=0), 3),
            }

            logger.info(
                f"Fast reranking completed in {diagnostics['time_ms']}ms: "
                f"{len(candidates)} candidates → {len(filtered)} filtered → {len(results)} final"
            )

            return results, diagnostics

    def _fallback_ranking(self, documents: list[dict], top_k: int, start_time: float) -> tuple[list[dict], dict]:
        """
        Fallback ranking when model is unavailable.
        Uses hybrid_score or score from retrieval.
        """
        # Sort by existing scores
        sorted_docs = sorted(documents, key=lambda x: x.get("hybrid_score", x.get("score", 0)), reverse=True)

        results = sorted_docs[:top_k]

        # Copy score to rerank_score for consistency
        for doc in results:
            doc["rerank_score"] = doc.get("hybrid_score", doc.get("score", 0))

        elapsed_ms = (time.time() - start_time) * 1000

        return results, {
            "status": "fallback",
            "time_ms": round(elapsed_ms, 2),
            "method": "score_based",
            "final_count": len(results),
        }


# Global instance for reuse
_fast_reranker: FastReranker | None = None


def get_fast_reranker(
    model_name: str | None = None,
    device: str | None = None,
) -> FastReranker:
    """
    Get or create global fast reranker instance.

    Args:
        model_name: Override default model name
        device: Override device selection

    Returns:
        FastReranker instance
    """
    global _fast_reranker

    settings = get_settings()

    # Use settings or provided values
    model = model_name or getattr(settings, "fast_reranker_model", "BAAI/bge-reranker-base")

    if _fast_reranker is None:
        _fast_reranker = FastReranker(
            model_name=model,
            device=device,
        )

    return _fast_reranker


def fast_rerank(
    query: str,
    documents: list[dict],
    top_k: int = 10,
) -> tuple[list[dict], dict]:
    """
    Convenience function for fast reranking.

    Args:
        query: Search query
        documents: Documents to rerank
        top_k: Number of results to return

    Returns:
        Tuple of (reranked documents, diagnostics)
    """
    reranker = get_fast_reranker()
    return reranker.rerank(query, documents, top_k)
