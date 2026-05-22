"""
测试查询改写功能。
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.query_rewriter import rewrite_query_for_retrieval, expand_query_with_synonyms


def test_query_rewrite():
    """测试查询改写功能。"""
    test_cases = [
        ("给我介绍一下有哪些知识", "general"),
        ("什么是SQL注入攻击？", "cybersecurity"),
        ("如何训练神经网络？", "artificial_intelligence"),
        ("零信任架构是什么", "cybersecurity"),
        ("Transformer模型的原理", "artificial_intelligence"),
    ]

    print("=" * 80)
    print("查询改写测试")
    print("=" * 80)

    for question, agent_class in test_cases:
        print(f"\n原始问题: {question}")
        print(f"领域: {agent_class}")

        # LLM改写
        rewritten = rewrite_query_for_retrieval(question, agent_class)
        print(f"\nLLM改写 ({len(rewritten)}个查询):")
        for i, query in enumerate(rewritten, 1):
            print(f"  {i}. {query}")

        # 同义词扩展
        expanded = expand_query_with_synonyms(question, agent_class)
        print(f"\n同义词扩展 ({len(expanded)}个查询):")
        for i, query in enumerate(expanded, 1):
            print(f"  {i}. {query}")

        print("-" * 80)


if __name__ == "__main__":
    test_query_rewrite()
