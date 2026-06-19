"""
Test script for Graph RAG + PDF optimization features.

This script demonstrates the optimization capabilities without requiring
a live Neo4j connection.
"""

import sys
from pathlib import Path


def _configure_stdio() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


_configure_stdio()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.graph_rag_agent_enhanced import (
    analyze_pdf_quality,
    extract_document_entities,
    get_document_context_for_query,
    should_use_graph_rag,
)


# Sample PDF content for testing
SAMPLE_PDF_HIGH_QUALITY = """
# Introduction to Large Language Models

## 1. Overview

Large Language Models (LLMs) are a class of artificial intelligence systems
designed for natural language processing tasks. These models are trained on
massive text corpora and can perform various tasks including:

- Text generation
- Question answering
- Translation
- Summarization

## 2. Architecture

Modern LLMs are based on the Transformer architecture, which uses:

| Component | Description |
|-----------|-------------|
| Self-Attention | Allows tokens to attend to all other tokens |
| Feed-Forward | Processes representations independently |
| Layer Norm | Stabilizes training |

## 3. Training Process

The training of LLMs involves:

1. Pre-training on large corpora (unsupervised learning)
2. Fine-tuning on specific tasks (supervised learning)
3. Reinforcement learning from human feedback (RLHF)

## 4. Applications

LLMs power many modern AI applications:

- ChatGPT and Claude for conversational AI
- GitHub Copilot for code generation
- Retrieval-Augmented Generation (RAG) systems
- Automated content creation

## 5. Challenges

Key challenges in LLM development include:

- Hallucination and factual accuracy
- Computational cost and energy consumption
- Privacy and security concerns
- Bias and fairness issues

## References

Smith, J. et al. (2024). "Advances in Large Language Models."
Journal of AI Research, 45(3), 123-145.
"""

SAMPLE_PDF_LOW_QUALITY = """
text text text more text
some words here
random content
no structure
just plain text without formatting
more text here
"""

SAMPLE_PDF_CHINESE = """
# 大语言模型技术概述

## 1. 基本概念

大语言模型（LLM）是一种基于深度学习的自然语言处理系统。主要特点包括：

- 参数规模达到数十亿甚至千亿级别
- 采用Transformer架构
- 通过海量文本数据进行预训练

## 2. 关键技术

### 2.1 注意力机制

自注意力机制允许模型关注输入序列的不同位置，从而捕获长距离依赖关系。

### 2.2 检索增强生成（RAG）

RAG系统结合了信息检索和生成模型，能够：
- 提高回答的准确性
- 减少幻觉问题
- 支持知识更新

## 3. 应用场景

- 智能客服系统
- 代码生成工具
- 文档理解与分析
- 机器翻译

## 参考文献

张三等 (2024). "大语言模型在企业中的应用". 人工智能学报, 12(3), 45-67.
"""


def test_pdf_quality_analysis():
    """Test PDF quality analysis."""
    print("\n" + "="*70)
    print("TEST 1: PDF Quality Analysis")
    print("="*70)

    test_cases = [
        ("High Quality PDF", SAMPLE_PDF_HIGH_QUALITY, {}),
        ("Low Quality PDF", SAMPLE_PDF_LOW_QUALITY, {}),
        ("Chinese PDF", SAMPLE_PDF_CHINESE, {"format": "markdown"}),
    ]

    for name, content, metadata in test_cases:
        quality = analyze_pdf_quality(content, metadata)
        print(f"\n{name}:")
        print(f"  Quality Score: {quality:.2f}")

        if quality >= 0.7:
            print(f"  Assessment: ✅ Excellent - High confidence for graph extraction")
        elif quality >= 0.5:
            print(f"  Assessment: ⚠️  Good - Moderate confidence")
        else:
            print(f"  Assessment: ❌ Poor - Low confidence, may need preprocessing")


def test_entity_extraction():
    """Test entity extraction from PDFs."""
    print("\n" + "="*70)
    print("TEST 2: Entity Extraction")
    print("="*70)

    test_cases = [
        ("English Technical PDF", SAMPLE_PDF_HIGH_QUALITY),
        ("Chinese Technical PDF", SAMPLE_PDF_CHINESE),
    ]

    for name, content in test_cases:
        entities = extract_document_entities(content, limit=15)
        print(f"\n{name}:")
        print(f"  Extracted {len(entities)} entities:")
        for entity in entities[:10]:
            print(f"    - {entity}")
        if len(entities) > 10:
            print(f"    ... and {len(entities) - 10} more")


def test_document_context():
    """Test document context analysis for queries."""
    print("\n" + "="*70)
    print("TEST 3: Document Context Analysis")
    print("="*70)

    # Simulate retrieved documents
    retrieved_docs = [
        {
            "content": SAMPLE_PDF_HIGH_QUALITY,
            "metadata": {"format": "markdown", "page": 5, "total_pages": 10},
        },
        {
            "content": SAMPLE_PDF_CHINESE,
            "metadata": {"format": "markdown", "page": 3, "total_pages": 8},
        },
    ]

    questions = [
        "What is a Large Language Model?",
        "How does RAG work?",
        "什么是大语言模型？",
    ]

    for question in questions:
        context = get_document_context_for_query(question, retrieved_docs, top_k=2)

        print(f"\nQuery: {question}")
        print(f"  Quality Score: {context['quality_score']:.2f}")
        print(f"  Confidence: {context['confidence']}")
        print(f"  Entities Found: {len(context['entities'])}")
        print(f"  Sample Entities: {', '.join(context['entities'][:5])}")


def test_graph_rag_decision():
    """Test Graph RAG usage decision logic."""
    print("\n" + "="*70)
    print("TEST 4: Graph RAG Usage Decision")
    print("="*70)

    # Simulate retrieved documents
    high_quality_docs = [
        {
            "content": SAMPLE_PDF_HIGH_QUALITY,
            "metadata": {"format": "markdown"},
        },
    ]

    low_quality_docs = [
        {
            "content": SAMPLE_PDF_LOW_QUALITY,
            "metadata": {},
        },
    ]

    test_cases = [
        ("Single entity query", "What is LLM?", high_quality_docs, None),
        ("Multi-entity query", "What is the relationship between LLM and RAG?", high_quality_docs, None),
        ("Low quality docs", "What is this about?", low_quality_docs, None),
        ("Strong graph signal", "What is AI?", high_quality_docs, 0.75),
        ("Weak graph signal", "Random question", low_quality_docs, 0.2),
    ]

    for name, question, docs, signal in test_cases:
        should_use, reason = should_use_graph_rag(question, docs, signal)
        status = "✅ YES" if should_use else "❌ NO"
        print(f"\n{name}:")
        print(f"  Query: {question}")
        print(f"  Use Graph RAG: {status}")
        print(f"  Reason: {reason}")


def test_enhanced_scoring():
    """Test enhanced graph signal scoring."""
    print("\n" + "="*70)
    print("TEST 5: Enhanced Graph Signal Scoring")
    print("="*70)

    from app.tools.graph_tools_enhanced import _calculate_enhanced_signal_score

    # Simulate graph data
    test_scenarios = [
        {
            "name": "Strong Coverage (High Quality PDF)",
            "entities": [
                {"entity": "llm", "relations": [{"relation": "uses", "other": "transformer", "weight": 1.0}], "relevance": 0.9},
                {"entity": "rag", "relations": [{"relation": "improves", "other": "accuracy", "weight": 0.9}], "relevance": 0.8},
                {"entity": "transformer", "relations": [], "relevance": 0.7},
            ],
            "neighbors": [
                {"entity": "llm", "relation": "uses", "other": "attention", "weight": 1.0},
                {"entity": "rag", "relation": "combines", "other": "retrieval", "weight": 0.9},
            ],
            "paths": [
                {"source": "llm", "rel1": "uses", "middle": "transformer", "rel2": "contains", "target": "attention", "weight": 0.95},
            ],
            "context_quality": 0.8,
        },
        {
            "name": "Moderate Coverage (Medium Quality PDF)",
            "entities": [
                {"entity": "ai", "relations": [], "relevance": 0.6},
            ],
            "neighbors": [
                {"entity": "ai", "relation": "related", "other": "ml", "weight": 0.6},
            ],
            "paths": [],
            "context_quality": 0.5,
        },
        {
            "name": "Weak Coverage (Low Quality PDF)",
            "entities": [],
            "neighbors": [],
            "paths": [],
            "context_quality": 0.3,
        },
    ]

    for scenario in test_scenarios:
        score = _calculate_enhanced_signal_score(
            scenario["entities"],
            scenario["neighbors"],
            scenario["paths"],
            scenario["context_quality"],
        )

        print(f"\n{scenario['name']}:")
        print(f"  Entities: {len(scenario['entities'])}")
        print(f"  Neighbors: {len(scenario['neighbors'])}")
        print(f"  Paths: {len(scenario['paths'])}")
        print(f"  Context Quality: {scenario['context_quality']:.2f}")
        print(f"  → Enhanced Signal Score: {score:.2f}")

        if score >= 0.7:
            print(f"  → Assessment: ✅ High confidence - Graph knowledge is strong")
        elif score >= 0.5:
            print(f"  → Assessment: ⚠️  Medium confidence - Useful but not definitive")
        else:
            print(f"  → Assessment: ❌ Low confidence - Limited graph coverage")


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("GRAPH RAG + PDF OPTIMIZATION TEST SUITE")
    print("="*70)
    print("\nThis test suite demonstrates the optimization features for")
    print("improving Graph RAG accuracy after PDF processing.")

    try:
        test_pdf_quality_analysis()
        test_entity_extraction()
        test_document_context()
        test_graph_rag_decision()
        test_enhanced_scoring()

        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print("\n✅ All tests completed successfully!")
        print("\nKey Improvements:")
        print("  1. PDF quality analysis for adaptive graph parameters")
        print("  2. Enhanced entity extraction with cross-language support")
        print("  3. Document context enrichment for better graph queries")
        print("  4. Intelligent Graph RAG usage decisions")
        print("  5. Enhanced signal scoring with context awareness")

        print("\nNext Steps:")
        print("  • Start Neo4j: docker compose up -d neo4j")
        print("  • Run with live data: python scripts/optimize_graph_rag_accuracy.py stats")
        print("  • Integrate enhanced modules into production workflow")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
