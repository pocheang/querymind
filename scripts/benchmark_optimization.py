#!/usr/bin/env python3
"""
性能基准测试脚本

用于测试优化前后的性能对比
"""

import time
import statistics
from typing import List, Dict

def benchmark_cache_performance():
    """测试缓存性能"""
    from app.agents.graph_rag_cache import (
        analyze_pdf_quality,
        extract_document_entities,
        clear_all_caches
    )

    # 清空缓存
    clear_all_caches()

    test_text = """
    # Large Language Models

    Large Language Models (LLMs) are AI systems that use Transformer
    architecture for natural language processing, machine learning,
    deep learning tasks. They implement algorithms and methods for
    data analysis and system optimization.

    | Model | Parameters |
    |-------|-----------|
    | GPT-4 | 1.7T      |
    """

    metadata = {"format": "markdown", "total_pages": 10}

    # 测试第一次调用（缓存未命中）
    times_cold = []
    for _ in range(5):
        clear_all_caches()
        start = time.perf_counter()
        analyze_pdf_quality(test_text, metadata)
        elapsed = (time.perf_counter() - start) * 1000
        times_cold.append(elapsed)

    # 测试缓存命中
    clear_all_caches()
    analyze_pdf_quality(test_text, metadata)  # 预热

    times_hot = []
    for _ in range(100):
        start = time.perf_counter()
        analyze_pdf_quality(test_text, metadata)
        elapsed = (time.perf_counter() - start) * 1000
        times_hot.append(elapsed)

    return {
        "cold_mean": statistics.mean(times_cold),
        "cold_std": statistics.stdev(times_cold),
        "hot_mean": statistics.mean(times_hot),
        "hot_std": statistics.stdev(times_hot),
        "speedup": statistics.mean(times_cold) / statistics.mean(times_hot)
    }


def benchmark_router_cache():
    """测试路由决策缓存"""
    from app.agents.router_agent import decide_route
    from app.agents.shared_cache import clear_agent_caches

    clear_agent_caches()

    questions = [
        "What is a Large Language Model?",
        "How does RAG work?",
        "Explain transformer architecture",
    ]

    # 缓存未命中
    times_cold = []
    for q in questions:
        clear_agent_caches()
        start = time.perf_counter()
        decide_route(q, use_llm_intent=False)
        elapsed = (time.perf_counter() - start) * 1000
        times_cold.append(elapsed)

    # 缓存命中
    clear_agent_caches()
    for q in questions:
        decide_route(q, use_llm_intent=False)  # 预热

    times_hot = []
    for _ in range(50):
        for q in questions:
            start = time.perf_counter()
            decide_route(q, use_llm_intent=False)
            elapsed = (time.perf_counter() - start) * 1000
            times_hot.append(elapsed)

    return {
        "cold_mean": statistics.mean(times_cold),
        "hot_mean": statistics.mean(times_hot),
        "speedup": statistics.mean(times_cold) / statistics.mean(times_hot)
    }


def print_benchmark_results():
    """打印基准测试结果"""
    print("=" * 70)
    print("性能基准测试报告")
    print("=" * 70)
    print()

    # PDF质量分析缓存
    print("1. PDF质量分析缓存性能")
    print("-" * 70)
    try:
        results = benchmark_cache_performance()
        print(f"  缓存未命中 (冷启动): {results['cold_mean']:.2f}ms (±{results['cold_std']:.2f}ms)")
        print(f"  缓存命中 (热启动):   {results['hot_mean']:.4f}ms (±{results['hot_std']:.4f}ms)")
        print(f"  性能提升:            {results['speedup']:.1f}x")
        print(f"  延迟降低:            {(1 - 1/results['speedup']) * 100:.1f}%")
        print()
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        print()

    # 路由决策缓存
    print("2. 路由决策缓存性能")
    print("-" * 70)
    try:
        results = benchmark_router_cache()
        print(f"  缓存未命中: {results['cold_mean']:.2f}ms")
        print(f"  缓存命中:   {results['hot_mean']:.2f}ms")
        print(f"  性能提升:   {results['speedup']:.1f}x")
        print(f"  延迟降低:   {(1 - 1/results['speedup']) * 100:.1f}%")
        print()
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        print()

    # 缓存统计
    print("3. 缓存统计信息")
    print("-" * 70)
    try:
        from app.agents.graph_rag_cache import get_cache_stats
        from app.agents.shared_cache import get_agent_cache_stats

        graph_stats = get_cache_stats()
        agent_stats = get_agent_cache_stats()

        print("  Graph RAG 缓存:")
        for name, stats in graph_stats.items():
            print(f"    {name}: {stats['size']} 项, 命中率 {stats['hit_rate']:.1%}")

        print("  Agent 缓存:")
        for name, stats in agent_stats.items():
            print(f"    {name}: {stats['size']} 项, 命中率 {stats['hit_rate']:.1%}")
        print()
    except Exception as e:
        print(f"  ✗ 获取统计失败: {e}")
        print()

    print("=" * 70)
    print("✓ 基准测试完成")
    print("=" * 70)


if __name__ == "__main__":
    print_benchmark_results()
