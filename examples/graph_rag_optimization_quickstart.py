"""
Quick Start Example: Graph RAG + PDF Optimization

This example demonstrates how to use the enhanced Graph RAG features
with your existing RAG pipeline.
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any


def _configure_stdio() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


_configure_stdio()

# Step 1: Import the enhanced modules
from app.agents.graph_rag_agent_enhanced import (
    analyze_pdf_quality,
    run_graph_rag_with_pdf_context,
    should_use_graph_rag,
)


async def example_basic_usage():
    """Example 1: Basic usage with document quality analysis."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Enhanced Graph RAG Usage")
    print("="*70)

    # Simulate retrieved documents from vector search
    retrieved_docs = [
        {
            "content": """
# Retrieval-Augmented Generation (RAG)

RAG is an AI framework that combines retrieval systems with
large language models (LLMs) to improve answer accuracy.

## Key Components

1. **Retrieval System**: Finds relevant documents
2. **Generator**: LLM that produces the final answer
3. **Knowledge Base**: Vector database or document store

## Benefits

- Reduces hallucination
- Provides source attribution
- Enables knowledge updates without retraining
""",
            "metadata": {
                "source": "docs/rag_overview.pdf",
                "page": 1,
                "format": "markdown",
                "total_pages": 5,
            }
        },
        {
            "content": """
Large language models can be enhanced with external knowledge
through various techniques. RAG is one approach that has shown
promising results in question-answering tasks.
""",
            "metadata": {
                "source": "docs/llm_techniques.pdf",
                "page": 3,
            }
        }
    ]

    # User query
    question = "How does RAG reduce hallucination in LLMs?"

    print(f"\nQuery: {question}")
    print(f"Retrieved Documents: {len(retrieved_docs)}")

    # Run enhanced Graph RAG
    result = run_graph_rag_with_pdf_context(
        question=question,
        retrieved_docs=retrieved_docs,
        allowed_sources=None,  # Use all sources
    )

    # Display results
    print(f"\n📊 Results:")
    print(f"  Graph Signal Score: {result['graph_signal_score']:.2f}")
    print(f"  Confidence: {result['confidence']}")
    print(f"  Entities Found: {len(result['entities'])}")
    print(f"  Entities: {', '.join(result['entities'][:5])}")

    if result.get('pdf_context'):
        pdf_ctx = result['pdf_context']
        print(f"\n📄 PDF Context:")
        print(f"  Quality Score: {pdf_ctx['quality_score']:.2f}")
        print(f"  Document Entities: {len(pdf_ctx['entities'])}")

    if result['context']:
        print(f"\n🔗 Graph Context Preview:")
        all_lines = result['context'].split('\n')
        context_lines = all_lines[:5]
        for line in context_lines:
            print(f"  {line}")
        if len(all_lines) > 5:
            remaining = len(all_lines) - 5
            print(f"  ... and {remaining} more lines")


async def example_quality_analysis():
    """Example 2: PDF quality analysis and decision making."""
    print("\n" + "="*70)
    print("EXAMPLE 2: PDF Quality Analysis & Smart Decisions")
    print("="*70)

    test_documents = [
        {
            "name": "High Quality Technical Doc",
            "content": """
# Machine Learning Pipeline Architecture

## 1. Data Ingestion
The pipeline begins with data collection from multiple sources.

| Stage | Component | Purpose |
|-------|-----------|---------|
| Extract | API/DB Connectors | Fetch raw data |
| Transform | ETL Pipeline | Clean and normalize |
| Load | Data Warehouse | Store processed data |

## 2. Feature Engineering
Feature engineering improves model performance through:
- Dimensionality reduction
- Feature scaling
- Encoding categorical variables

## References
[1] Smith et al. (2024). ML Pipeline Design Patterns.
""",
            "metadata": {"format": "markdown", "total_pages": 20}
        },
        {
            "name": "Low Quality Text Dump",
            "content": "some text here more words random content no structure",
            "metadata": {}
        },
        {
            "name": "Medium Quality Report",
            "content": """
Report on System Performance

The system showed good results in testing.
Key metrics include response time and accuracy.
Response time was 150ms on average.
Accuracy reached 95% on test dataset.
""",
            "metadata": {"total_pages": 3}
        }
    ]

    for doc_info in test_documents:
        print(f"\n📄 Document: {doc_info['name']}")

        # Analyze quality
        quality = analyze_pdf_quality(doc_info["content"], doc_info["metadata"])
        print(f"  Quality Score: {quality:.2f}")

        if quality >= 0.7:
            print(f"  ✅ Assessment: Excellent for graph extraction")
        elif quality >= 0.5:
            print(f"  ⚠️  Assessment: Good, usable quality")
        else:
            print(f"  ❌ Assessment: Poor, needs preprocessing")

        # Make decision
        question = "What are the key components?"
        should_use, reason = should_use_graph_rag(
            question=question,
            retrieved_docs=[doc_info],
            graph_signal_score=None
        )

        print(f"  Use Graph RAG: {'✅ YES' if should_use else '❌ NO'}")
        print(f"  Reason: {reason}")


async def example_integration_pattern():
    """Example 3: Integration pattern for existing RAG system."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Integration Pattern for Existing Systems")
    print("="*70)

    print("""
# Integration Pattern: Wrapper Approach

This pattern allows you to gradually adopt the enhanced features
without modifying your existing codebase extensively.

```python
# Original RAG query function
async def original_rag_query(question: str, user_id: str):
    # 1. Retrieve documents
    docs = await vector_search(question, top_k=5)

    # 2. Run graph RAG (original)
    from app.agents.graph_rag_agent import run_graph_rag
    graph_result = run_graph_rag(question)

    # 3. Generate answer
    answer = await generate_answer(question, docs, graph_result)
    return answer

# Enhanced version with backward compatibility
async def enhanced_rag_query(question: str, user_id: str, use_enhanced: bool = True):
    # 1. Retrieve documents (same as before)
    docs = await vector_search(question, top_k=5)

    # 2. Run graph RAG (enhanced or original)
    if use_enhanced:
        from app.agents.graph_rag_agent_enhanced import run_graph_rag_with_pdf_context

        # Smart decision: should we use graph?
        from app.agents.graph_rag_agent_enhanced import should_use_graph_rag
        should_use, reason = should_use_graph_rag(question, docs)

        if should_use:
            graph_result = run_graph_rag_with_pdf_context(
                question=question,
                retrieved_docs=docs
            )
        else:
            # Skip graph RAG for low-value scenarios
            graph_result = {"context": "", "entities": [], "graph_signal_score": 0.0}
    else:
        # Fallback to original implementation
        from app.agents.graph_rag_agent import run_graph_rag
        graph_result = run_graph_rag(question)

    # 3. Generate answer (same as before)
    answer = await generate_answer(question, docs, graph_result)
    return answer
```

# Benefits:
- ✅ Backward compatible: Can toggle between old/new implementations
- ✅ Gradual rollout: Enable for specific users or query types
- ✅ Easy A/B testing: Compare accuracy metrics
- ✅ Safe fallback: Original code remains unchanged
""")


async def example_monitoring():
    """Example 4: Monitoring and metrics collection."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Monitoring & Metrics Collection")
    print("="*70)

    print("""
# Monitoring Best Practices

## 1. Track Quality Metrics

```python
from collections import defaultdict
import statistics

class GraphRAGMetrics:
    def __init__(self):
        self.quality_scores = []
        self.signal_scores = []
        self.decisions = defaultdict(int)
        self.latencies = []

    def record_query(self, result: dict, latency_ms: float):
        # Record PDF quality
        if 'pdf_context' in result:
            self.quality_scores.append(result['pdf_context']['quality_score'])

        # Record graph signal
        self.signal_scores.append(result['graph_signal_score'])

        # Record confidence
        self.decisions[result['confidence']] += 1

        # Record latency
        self.latencies.append(latency_ms)

    def get_summary(self):
        return {
            "avg_pdf_quality": statistics.mean(self.quality_scores) if self.quality_scores else 0,
            "avg_graph_signal": statistics.mean(self.signal_scores) if self.signal_scores else 0,
            "confidence_distribution": dict(self.decisions),
            "avg_latency_ms": statistics.mean(self.latencies) if self.latencies else 0,
            "total_queries": len(self.signal_scores)
        }

# Usage
metrics = GraphRAGMetrics()

# In your query handler
import time
start = time.time()
result = run_graph_rag_with_pdf_context(question, docs)
latency = (time.time() - start) * 1000

metrics.record_query(result, latency)

# Periodic summary
print(metrics.get_summary())
```

## 2. Log Key Events

```python
import logging

logger = logging.getLogger(__name__)

# Log quality assessments
if pdf_quality < 0.3:
    logger.warning(f"Low quality PDF detected: {pdf_quality:.2f} - {doc_source}")

# Log skipped graph queries
if not should_use:
    logger.info(f"Skipped graph RAG: {reason} - query: {question[:50]}")

# Log high-confidence results
if confidence == "high":
    logger.info(f"High confidence result: signal={signal_score:.2f}")
```

## 3. Alert on Anomalies

```python
# Example: Alert if quality drops suddenly
if len(quality_scores) >= 10:
    recent_avg = statistics.mean(quality_scores[-10:])
    historical_avg = statistics.mean(quality_scores[:-10])

    if recent_avg < historical_avg * 0.7:  # 30% drop
        alert("PDF quality degradation detected")
```
""")


async def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("GRAPH RAG + PDF OPTIMIZATION - QUICK START EXAMPLES")
    print("="*70)
    print("\nThese examples demonstrate the enhanced Graph RAG features")
    print("that improve accuracy when processing PDF documents.\n")

    try:
        await example_basic_usage()
        await example_quality_analysis()
        await example_integration_pattern()
        await example_monitoring()

        print("\n" + "="*70)
        print("✅ ALL EXAMPLES COMPLETED")
        print("="*70)
        print("\n📚 Next Steps:")
        print("  1. Review the full guide: docs/GRAPH_RAG_PDF_OPTIMIZATION_GUIDE.md")
        print("  2. Run live tests: python scripts/optimize_graph_rag_accuracy.py stats")
        print("  3. Integrate into your workflow using the patterns above")
        print("  4. Monitor metrics and tune parameters based on your data")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
