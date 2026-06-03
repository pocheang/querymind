"""
Test script for v0.4.4 optimized RAG pipeline.

Tests and validates:
- 3-path retrieval performance
- Fast reranking speed
- Rule-based compression efficiency
- Adaptive strategy routing
- Overall pipeline accuracy and speed

Run with: python -m pytest tests/test_optimized_pipeline.py -v
Or directly: python scripts/test_optimized_pipeline.py
"""

import asyncio
import time
import logging
from typing import List, Dict
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.optimized_rag_pipeline import OptimizedRAGPipeline
from app.services.adaptive_strategy import QueryComplexityAnalyzer, analyze_query_complexity
from app.retrievers.multi_path_retriever import MultiPathRetriever
from app.retrievers.fast_reranker import FastReranker
from app.services.rule_compressor import RuleBasedCompressor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OptimizedPipelineValidator:
    """Validates optimized pipeline performance."""

    def __init__(self):
        self.test_queries = self._load_test_queries()

    def _load_test_queries(self) -> List[Dict]:
        """Load test queries with expected complexity."""
        return [
            # Simple queries (target: <400ms)
            {
                "query": "What is RAG?",
                "expected_complexity": "simple",
                "target_time_ms": 400,
                "language": "en",
            },
            {
                "query": "什么是向量数据库？",
                "expected_complexity": "simple",
                "target_time_ms": 400,
                "language": "zh",
            },
            # Medium queries (target: <800ms)
            {
                "query": "How does hybrid retrieval work in RAG systems?",
                "expected_complexity": "medium",
                "target_time_ms": 800,
                "language": "en",
            },
            {
                "query": "RAG系统如何处理中文查询？",
                "expected_complexity": "medium",
                "target_time_ms": 800,
                "language": "zh",
            },
            # Complex queries (target: <1500ms)
            {
                "query": "Compare and contrast vector search and BM25 retrieval, "
                        "and explain when to use each approach in a production RAG system.",
                "expected_complexity": "complex",
                "target_time_ms": 1500,
                "language": "en",
            },
            {
                "query": "详细解释RAG系统中的检索、重排序和生成三个阶段，"
                        "并说明如何优化每个阶段的性能和准确率。",
                "expected_complexity": "complex",
                "target_time_ms": 1500,
                "language": "zh",
            },
        ]

    async def test_complexity_analysis(self) -> Dict:
        """Test query complexity analysis."""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 1: Query Complexity Analysis")
        logger.info("=" * 60)

        analyzer = QueryComplexityAnalyzer()
        results = []
        correct = 0

        for test_case in self.test_queries:
            query = test_case["query"]
            expected = test_case["expected_complexity"]

            level, analysis = analyzer.analyze(query)

            is_correct = level == expected
            if is_correct:
                correct += 1

            result = {
                "query": query[:50] + "..." if len(query) > 50 else query,
                "expected": expected,
                "detected": level,
                "score": analysis["score"],
                "correct": is_correct,
            }
            results.append(result)

            logger.info(
                f"Query: {result['query']}\n"
                f"  Expected: {expected}, Detected: {level}, "
                f"Score: {analysis['score']:.1f} - {'✓' if is_correct else '✗'}"
            )

        accuracy = correct / len(self.test_queries) * 100

        summary = {
            "test": "complexity_analysis",
            "total": len(self.test_queries),
            "correct": correct,
            "accuracy": f"{accuracy:.1f}%",
            "passed": accuracy >= 80,  # Target: 80%+ accuracy
            "results": results,
        }

        logger.info(f"\nComplexity Analysis Accuracy: {accuracy:.1f}% ({correct}/{len(self.test_queries)})")
        logger.info(f"Result: {'PASS' if summary['passed'] else 'FAIL'} (target: 80%+)")

        return summary

    async def test_multi_path_retrieval(self) -> Dict:
        """Test multi-path retrieval speed."""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 2: Multi-Path Retrieval Performance")
        logger.info("=" * 60)

        retriever = MultiPathRetriever()
        results = []

        # Test with 3 different queries
        test_queries = [
            "What is machine learning?",
            "Explain neural networks",
            "How does backpropagation work?",
        ]

        for query in test_queries:
            start = time.time()
            docs, diagnostics = await retriever.retrieve(query, top_k=50)
            elapsed_ms = (time.time() - start) * 1000

            result = {
                "query": query,
                "time_ms": round(elapsed_ms, 2),
                "retrieved": len(docs),
                "target_ms": 300,
                "within_target": elapsed_ms <= 300,
            }
            results.append(result)

            logger.info(
                f"Query: {query}\n"
                f"  Time: {elapsed_ms:.0f}ms, Retrieved: {len(docs)}, "
                f"Target: 300ms - {'✓' if result['within_target'] else '✗'}"
            )

        avg_time = sum(r["time_ms"] for r in results) / len(results)
        within_target_count = sum(1 for r in results if r["within_target"])

        summary = {
            "test": "multi_path_retrieval",
            "avg_time_ms": round(avg_time, 2),
            "target_ms": 300,
            "within_target": within_target_count,
            "total": len(results),
            "passed": avg_time <= 300,
            "results": results,
        }

        logger.info(f"\nAverage Retrieval Time: {avg_time:.0f}ms (target: ≤300ms)")
        logger.info(f"Within Target: {within_target_count}/{len(results)}")
        logger.info(f"Result: {'PASS' if summary['passed'] else 'FAIL'}")

        return summary

    async def test_fast_reranking(self) -> Dict:
        """Test fast reranking speed."""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 3: Fast Reranking Performance")
        logger.info("=" * 60)

        reranker = FastReranker()

        # Create mock documents
        mock_docs = [
            {
                "text": f"This is document {i} about machine learning and AI.",
                "score": 0.5 + (i * 0.01),
                "metadata": {"source": f"doc_{i}.pdf"},
            }
            for i in range(30)
        ]

        query = "What is machine learning?"

        start = time.time()
        reranked, diagnostics = reranker.rerank(query, mock_docs, top_k=10)
        elapsed_ms = (time.time() - start) * 1000

        summary = {
            "test": "fast_reranking",
            "time_ms": round(elapsed_ms, 2),
            "target_ms": 200,
            "candidates": len(mock_docs),
            "output": len(reranked),
            "within_target": elapsed_ms <= 200,
            "passed": elapsed_ms <= 250,  # Allow 250ms tolerance
            "device": diagnostics.get("device", "cpu"),
        }

        logger.info(
            f"Reranking Time: {elapsed_ms:.0f}ms (target: ≤200ms)\n"
            f"  Device: {summary['device']}, Candidates: {len(mock_docs)} → {len(reranked)}\n"
            f"  Result: {'✓' if summary['within_target'] else '✗ (within tolerance)' if summary['passed'] else '✗ FAIL'}"
        )

        return summary

    async def test_rule_compression(self) -> Dict:
        """Test rule-based compression speed."""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 4: Rule-Based Compression Performance")
        logger.info("=" * 60)

        compressor = RuleBasedCompressor()

        # Create mock documents with realistic content
        mock_docs = [
            {
                "text": "Machine learning is a subset of artificial intelligence. "
                        "It enables systems to learn and improve from experience. "
                        "The main types include supervised, unsupervised, and reinforcement learning. "
                        "Each type has different use cases and applications.",
                "metadata": {"source": "ml_intro.pdf"},
            },
            {
                "text": "Neural networks are computing systems inspired by biological neural networks. "
                        "They consist of layers of interconnected nodes. "
                        "Deep learning uses multiple layers to extract features. "
                        "This approach has revolutionized AI applications.",
                "metadata": {"source": "neural_nets.pdf"},
            },
        ]

        query = "What is machine learning?"

        start = time.time()
        compressed, diagnostics = compressor.compress(query, mock_docs, max_length=200)
        elapsed_ms = (time.time() - start) * 1000

        summary = {
            "test": "rule_compression",
            "time_ms": round(elapsed_ms, 2),
            "target_ms": 50,
            "original_chars": diagnostics.get("original_chars", 0),
            "compressed_chars": diagnostics.get("compressed_chars", 0),
            "compression_ratio": diagnostics.get("overall_compression_ratio", 0),
            "within_target": elapsed_ms <= 50,
            "passed": elapsed_ms <= 100,  # Allow 100ms tolerance
        }

        logger.info(
            f"Compression Time: {elapsed_ms:.0f}ms (target: ≤50ms)\n"
            f"  Original: {summary['original_chars']} chars → "
            f"Compressed: {summary['compressed_chars']} chars "
            f"({summary['compression_ratio']:.0%})\n"
            f"  Result: {'✓' if summary['within_target'] else '✗ (within tolerance)' if summary['passed'] else '✗ FAIL'}"
        )

        return summary

    async def test_full_pipeline(self) -> Dict:
        """Test full optimized pipeline."""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 5: Full Pipeline Performance")
        logger.info("=" * 60)

        pipeline = OptimizedRAGPipeline(
            enable_3_path=True,
            enable_fast_rerank=True,
            enable_compression=True,
            enable_dynamic_routing=True,
            enable_cache=True,
        )

        results = []

        for test_case in self.test_queries[:3]:  # Test first 3 queries
            query = test_case["query"]
            target_time = test_case["target_time_ms"]

            try:
                result = await pipeline.query(query, strategy="auto", top_k=5)

                total_time = result["diagnostics"]["total_time_ms"]
                within_target = total_time <= target_time

                test_result = {
                    "query": query[:50] + "..." if len(query) > 50 else query,
                    "strategy": result["strategy_used"],
                    "time_ms": total_time,
                    "target_ms": target_time,
                    "retrieved": result["retrieved_count"],
                    "final": result["final_count"],
                    "within_target": within_target,
                }
                results.append(test_result)

                logger.info(
                    f"Query: {test_result['query']}\n"
                    f"  Strategy: {test_result['strategy']}, Time: {total_time:.0f}ms, "
                    f"Target: {target_time}ms - {'✓' if within_target else '✗'}"
                )

            except Exception as e:
                logger.error(f"Pipeline test failed for query '{query}': {e}")
                results.append({
                    "query": query,
                    "error": str(e),
                    "within_target": False,
                })

        avg_time = sum(r.get("time_ms", 0) for r in results if "time_ms" in r) / len(results)
        within_target_count = sum(1 for r in results if r.get("within_target", False))

        summary = {
            "test": "full_pipeline",
            "avg_time_ms": round(avg_time, 2),
            "within_target": within_target_count,
            "total": len(results),
            "success_rate": f"{within_target_count / len(results) * 100:.1f}%",
            "passed": within_target_count >= len(results) * 0.7,  # 70% should meet targets
            "results": results,
        }

        logger.info(f"\nAverage Pipeline Time: {avg_time:.0f}ms")
        logger.info(f"Within Target: {within_target_count}/{len(results)} ({summary['success_rate']})")
        logger.info(f"Result: {'PASS' if summary['passed'] else 'FAIL'} (target: 70%+)")

        return summary

    async def run_all_tests(self) -> Dict:
        """Run all validation tests."""
        logger.info("\n" + "=" * 60)
        logger.info("STARTING V0.4.4 OPTIMIZED PIPELINE VALIDATION")
        logger.info("=" * 60)

        results = {
            "complexity_analysis": await self.test_complexity_analysis(),
            "multi_path_retrieval": await self.test_multi_path_retrieval(),
            "fast_reranking": await self.test_fast_reranking(),
            "rule_compression": await self.test_rule_compression(),
            "full_pipeline": await self.test_full_pipeline(),
        }

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)

        passed_count = sum(1 for r in results.values() if r.get("passed", False))
        total_count = len(results)

        for test_name, result in results.items():
            status = "PASS" if result.get("passed", False) else "FAIL"
            logger.info(f"{test_name}: {status}")

        logger.info(f"\nOverall: {passed_count}/{total_count} tests passed")

        results["summary"] = {
            "total_tests": total_count,
            "passed": passed_count,
            "failed": total_count - passed_count,
            "success_rate": f"{passed_count / total_count * 100:.1f}%",
            "all_passed": passed_count == total_count,
        }

        return results


async def main():
    """Main test runner."""
    validator = OptimizedPipelineValidator()
    results = await validator.run_all_tests()

    # Exit with appropriate code
    if results["summary"]["all_passed"]:
        logger.info("\n✓ ALL TESTS PASSED")
        sys.exit(0)
    else:
        logger.error("\n✗ SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
