"""
Golden Dataset Builder for A/B Testing

Creates a comprehensive 100-query test dataset with expected outcomes
for validating the enhanced RAG system against the baseline.

Dataset Composition:
- 25 concept queries with expected answers
- 20 relationship queries with expected entities  
- 15 comparison queries with expected structure
- 15 multi-hop reasoning queries
- 10 ambiguous queries with expected clarifications
- 10 follow-up queries with context
- 5 edge cases (empty, contradictory, time-sensitive)
"""

import json
from pathlib import Path
from typing import List, Dict, Any


GOLDEN_DATASET = [
    # Concept queries (1-25)
    {"id": 1, "category": "concept", "query": "What is machine learning?", "expected_route": "vector", "expected_skill": "ai_knowledge_assistant", "expected_answer_contains": ["algorithm", "data", "pattern"], "language": "en", "complexity": "simple"},
    {"id": 2, "category": "concept", "query": "Explain the transformer architecture in deep learning", "expected_route": "vector", "expected_skill": "ai_knowledge_assistant", "expected_answer_contains": ["attention", "encoder", "decoder"], "language": "en", "complexity": "medium"},
    {"id": 3, "category": "concept", "query": "What is a neural network?", "expected_route": "vector", "expected_skill": "ai_knowledge_assistant", "expected_answer_contains": ["neuron", "layer", "weight"], "language": "en", "complexity": "simple"},
    {"id": 4, "category": "concept", "query": "什么是自然语言处理？", "expected_route": "vector", "expected_skill": "ai_knowledge_assistant", "expected_answer_contains": ["语言", "文本"], "language": "zh", "complexity": "simple"},
    {"id": 5, "category": "concept", "query": "Define convolutional neural networks", "expected_route": "vector", "expected_skill": "ai_knowledge_assistant", "expected_answer_contains": ["convolution", "filter", "image"], "language": "en", "complexity": "medium"},
    {"id": 6, "category": "concept", "query": "What is reinforcement learning?", "expected_route": "vector", "expected_skill": "ai_knowledge_assistant", "expected_answer_contains": ["reward", "agent", "environment"], "language": "en", "complexity": "medium"},
    {"id": 7, "category": "concept", "query": "解释什么是深度学习", "expected_route": "vector", "expected_skill": "ai_knowledge_assistant", "expected_answer_contains": ["神经网络", "层"], "language": "zh", "complexity": "simple"},
    {"id": 8, "category": "concept", "query": "What is backpropagation?", "expected_route": "vector", "expected_skill": "ai_knowledge_assistant", "expected_answer_contains": ["gradient", "chain rule", "weight"], "language": "en", "complexity": "medium"},
    {"id": 9, "category": "concept", "query": "Define overfitting in machine learning", "expected_route": "vector", "expected_skill": "ai_knowledge_assistant", "expected_answer_contains": ["training", "generalization"], "language": "en", "complexity": "simple"},
    {"id": 10, "category": "concept", "query": "什么是词嵌入？", "expected_route": "vector", "expected_skill": "ai_knowledge_assistant", "expected_answer_contains": ["向量", "语义"], "language": "zh", "complexity": "medium"},
    {"id": 11, "category": "concept", "query": "What is gradient descent?", "expected_route": "vector", "expected_skill": "ai_knowledge_assistant", "expected_answer_contains": ["optimization", "gradient"], "language": "en", "complexity": "simple"},
    {"id": 12, "category": "concept", "query": "Explain recurrent neural networks", "expected_route": "vector", "expected_skill": "ai_knowledge_assistant", "expected_answer_contains": ["sequence", "hidden state"], "language": "en", "complexity": "medium"},
    {"id": 13, "category": "concept", "query": "What is transfer learning?", "expected_route": "vector", "expected_skill": "ai_knowledge_assistant", "expected_answer_contains": ["pretrained", "fine-tune"], "language": "en", "complexity": "medium"},
    {"id": 14, "category": "concept", "query": "什么是注意力机制？", "expected_route": "vector", "expected_skill": "ai_knowledge_assistant", "expected_answer_contains": ["注意力", "权重"], "language": "zh", "complexity": "medium"},
    {"id": 15, "category": "concept", "query": "Define batch normalization", "expected_route": "vector", "expected_skill": "ai_knowledge_assistant", "expected_answer_contains": ["normalize", "mean", "variance"], "language": "en", "complexity": "medium"},
    {"id": 16, "category": "concept", "query": "What is a GAN?", "expected_route": "vector", "expected_skill": "ai_knowledge_assistant", "expected_answer_contains": ["generator", "discriminator"], "language": "en", "complexity": "medium"},
    {"id": 17, "category": "concept", "query": "解释什么是迁移学习", "expected_route": "vector", "expected_skill": "ai_knowledge_assistant", "expected_answer_contains": ["预训练", "知识"], "language": "zh", "complexity": "medium"},
    {"id": 18, "category": "concept", "query": "What is dropout in neural networks?", "expected_route": "vector", "expected_skill": "ai_knowledge_assistant", "expected_answer_contains": ["regularization", "random"], "language": "en", "complexity": "simple"},
    {"id": 19, "category": "concept", "query": "Define precision and recall", "expected_route": "vector", "expected_skill": "ai_knowledge_assistant", "expected_answer_contains": ["true positive", "metric"], "language": "en", "complexity": "simple"},
    {"id": 20, "category": "concept", "query": "什么是卷积神经网络？", "expected_route": "vector", "expected_skill": "ai_knowledge_assistant", "expected_answer_contains": ["卷积", "图像"], "language": "zh", "complexity": "simple"},
    {"id": 21, "category": "concept", "query": "What is cross-entropy loss?", "expected_route": "vector", "expected_skill": "ai_knowledge_assistant", "expected_answer_contains": ["loss", "probability"], "language": "en", "complexity": "medium"},
    {"id": 22, "category": "concept", "query": "Explain LSTM networks", "expected_route": "vector", "expected_skill": "ai_knowledge_assistant", "expected_answer_contains": ["long short-term memory", "gate"], "language": "en", "complexity": "medium"},
    {"id": 23, "category": "concept", "query": "什么是批归一化？", "expected_route": "vector", "expected_skill": "ai_knowledge_assistant", "expected_answer_contains": ["归一化", "均值"], "language": "zh", "complexity": "medium"},
    {"id": 24, "category": "concept", "query": "What is feature extraction?", "expected_route": "vector", "expected_skill": "ai_knowledge_assistant", "expected_answer_contains": ["feature", "representation"], "language": "en", "complexity": "simple"},
    {"id": 25, "category": "concept", "query": "Define ensemble learning", "expected_route": "vector", "expected_skill": "ai_knowledge_assistant", "expected_answer_contains": ["combine", "model"], "language": "en", "complexity": "simple"},

    # Relationship queries (26-45)
    {"id": 26, "category": "relationship", "query": "Who reports to the CTO?", "expected_route": "graph", "expected_skill": "answer_with_citations", "expected_entities": ["CTO", "employee"], "language": "en", "complexity": "simple"},
    {"id": 27, "category": "relationship", "query": "What projects is Alice working on?", "expected_route": "graph", "expected_skill": "answer_with_citations", "expected_entities": ["Alice", "project"], "language": "en", "complexity": "simple"},
    {"id": 28, "category": "relationship", "query": "Show connections between OpenAI and Anthropic", "expected_route": "graph", "expected_skill": "answer_with_citations", "expected_entities": ["OpenAI", "Anthropic"], "language": "en", "complexity": "medium"},
    {"id": 29, "category": "relationship", "query": "Which teams depend on the auth service?", "expected_route": "graph", "expected_skill": "answer_with_citations", "expected_entities": ["team", "auth service"], "language": "en", "complexity": "medium"},
    {"id": 30, "category": "relationship", "query": "张三的直接下属有哪些？", "expected_route": "graph", "expected_skill": "answer_with_citations", "expected_entities": ["张三", "employee"], "language": "zh", "complexity": "simple"},
    {"id": 31, "category": "relationship", "query": "Who are the contributors to the ML pipeline project?", "expected_route": "graph", "expected_skill": "answer_with_citations", "expected_entities": ["contributor", "ML pipeline"], "language": "en", "complexity": "simple"},
    {"id": 32, "category": "relationship", "query": "What is the relationship between Python and Django?", "expected_route": "graph", "expected_skill": "answer_with_citations", "expected_entities": ["Python", "Django"], "language": "en", "complexity": "simple"},
    {"id": 33, "category": "relationship", "query": "哪些服务依赖于数据库？", "expected_route": "graph", "expected_skill": "answer_with_citations", "expected_entities": ["service", "database"], "language": "zh", "complexity": "medium"},
    {"id": 34, "category": "relationship", "query": "Who manages the DevOps team?", "expected_route": "graph", "expected_skill": "answer_with_citations", "expected_entities": ["manager", "DevOps team"], "language": "en", "complexity": "simple"},
    {"id": 35, "category": "relationship", "query": "What dependencies does the frontend have?", "expected_route": "graph", "expected_skill": "answer_with_citations", "expected_entities": ["frontend", "dependency"], "language": "en", "complexity": "medium"},
    {"id": 36, "category": "relationship", "query": "Find all colleagues of Bob in the AI department", "expected_route": "graph", "expected_skill": "answer_with_citations", "expected_entities": ["Bob", "AI department"], "language": "en", "complexity": "simple"},
    {"id": 37, "category": "relationship", "query": "产品经理和哪些团队协作？", "expected_route": "graph", "expected_skill": "answer_with_citations", "expected_entities": ["产品经理", "team"], "language": "zh", "complexity": "medium"},
    {"id": 38, "category": "relationship", "query": "Which APIs are used by the mobile app?", "expected_route": "graph", "expected_skill": "answer_with_citations", "expected_entities": ["mobile app", "API"], "language": "en", "complexity": "medium"},
    {"id": 39, "category": "relationship", "query": "Who are the stakeholders for Project X?", "expected_route": "graph", "expected_skill": "answer_with_citations", "expected_entities": ["stakeholder", "Project X"], "language": "en", "complexity": "simple"},
    {"id": 40, "category": "relationship", "query": "What technologies does the backend use?", "expected_route": "graph", "expected_skill": "answer_with_citations", "expected_entities": ["backend", "technology"], "language": "en", "complexity": "simple"},
    {"id": 41, "category": "relationship", "query": "谁负责安全审计？", "expected_route": "graph", "expected_skill": "answer_with_citations", "expected_entities": ["person", "security audit"], "language": "zh", "complexity": "simple"},
    {"id": 42, "category": "relationship", "query": "Which modules import the utils library?", "expected_route": "graph", "expected_skill": "answer_with_citations", "expected_entities": ["module", "utils library"], "language": "en", "complexity": "medium"},
    {"id": 43, "category": "relationship", "query": "What roles does Sarah have in the organization?", "expected_route": "graph", "expected_skill": "answer_with_citations", "expected_entities": ["Sarah", "role"], "language": "en", "complexity": "simple"},
    {"id": 44, "category": "relationship", "query": "研发部门有哪些子团队？", "expected_route": "graph", "expected_skill": "answer_with_citations", "expected_entities": ["研发部门", "team"], "language": "zh", "complexity": "simple"},
    {"id": 45, "category": "relationship", "query": "Who has access to the production database?", "expected_route": "graph", "expected_skill": "answer_with_citations", "expected_entities": ["person", "production database"], "language": "en", "complexity": "medium"},

    # Comparison queries (46-60)
    {"id": 46, "category": "comparison", "query": "Compare Python and Java for machine learning", "expected_route": "hybrid", "expected_skill": "compare_entities", "expected_structure": ["similarities", "differences"], "language": "en", "complexity": "medium"},
    {"id": 47, "category": "comparison", "query": "What are the differences between supervised and unsupervised learning?", "expected_route": "vector", "expected_skill": "compare_entities", "expected_structure": ["supervised", "unsupervised"], "language": "en", "complexity": "medium"},
    {"id": 48, "category": "comparison", "query": "比较React和Vue框架", "expected_route": "hybrid", "expected_skill": "compare_entities", "expected_structure": ["React", "Vue"], "language": "zh", "complexity": "medium"},
    {"id": 49, "category": "comparison", "query": "Compare REST and GraphQL APIs", "expected_route": "vector", "expected_skill": "compare_entities", "expected_structure": ["REST", "GraphQL"], "language": "en", "complexity": "medium"},
    {"id": 50, "category": "comparison", "query": "What's the difference between Docker and Kubernetes?", "expected_route": "vector", "expected_skill": "compare_entities", "expected_structure": ["Docker", "Kubernetes"], "language": "en", "complexity": "simple"},
    {"id": 51, "category": "comparison", "query": "比较SQL和NoSQL数据库", "expected_route": "vector", "expected_skill": "compare_entities", "expected_structure": ["SQL", "NoSQL"], "language": "zh", "complexity": "medium"},
    {"id": 52, "category": "comparison", "query": "Compare CNN and RNN architectures", "expected_route": "vector", "expected_skill": "compare_entities", "expected_structure": ["CNN", "RNN"], "language": "en", "complexity": "medium"},
    {"id": 53, "category": "comparison", "query": "What are the pros and cons of microservices vs monolithic?", "expected_route": "vector", "expected_skill": "compare_entities", "expected_structure": ["microservices", "monolithic"], "language": "en", "complexity": "medium"},
    {"id": 54, "category": "comparison", "query": "比较Git和SVN版本控制", "expected_route": "vector", "expected_skill": "compare_entities", "expected_structure": ["Git", "SVN"], "language": "zh", "complexity": "simple"},
    {"id": 55, "category": "comparison", "query": "Compare AWS and Azure cloud platforms", "expected_route": "hybrid", "expected_skill": "compare_entities", "expected_structure": ["AWS", "Azure"], "language": "en", "complexity": "medium"},
    {"id": 56, "category": "comparison", "query": "What's the difference between HTTP and HTTPS?", "expected_route": "vector", "expected_skill": "compare_entities", "expected_structure": ["HTTP", "HTTPS"], "language": "en", "complexity": "simple"},
    {"id": 57, "category": "comparison", "query": "比较敏捷和瀑布开发模式", "expected_route": "vector", "expected_skill": "compare_entities", "expected_structure": ["agile", "waterfall"], "language": "zh", "complexity": "medium"},
    {"id": 58, "category": "comparison", "query": "Compare TensorFlow and PyTorch frameworks", "expected_route": "hybrid", "expected_skill": "compare_entities", "expected_structure": ["TensorFlow", "PyTorch"], "language": "en", "complexity": "medium"},
    {"id": 59, "category": "comparison", "query": "What are the differences between authentication and authorization?", "expected_route": "vector", "expected_skill": "compare_entities", "expected_structure": ["authentication", "authorization"], "language": "en", "complexity": "simple"},
    {"id": 60, "category": "comparison", "query": "比较前端和后端开发", "expected_route": "vector", "expected_skill": "compare_entities", "expected_structure": ["frontend", "backend"], "language": "zh", "complexity": "simple"},

    # Multi-hop reasoning queries (61-75)
    {"id": 61, "category": "multi_hop", "query": "Find all Python experts, check their projects, and recommend who should lead the ML initiative", "expected_route": "react", "expected_skill": "answer_with_citations", "expected_hops": 3, "language": "en", "complexity": "complex"},
    {"id": 62, "category": "multi_hop", "query": "What technologies does Team A use and how do they compare to industry standards?", "expected_route": "react", "expected_skill": "answer_with_citations", "expected_hops": 2, "language": "en", "complexity": "complex"},
    {"id": 63, "category": "multi_hop", "query": "找到所有使用Python的项目，然后分析它们的依赖关系", "expected_route": "react", "expected_skill": "answer_with_citations", "expected_hops": 2, "language": "zh", "complexity": "complex"},
    {"id": 64, "category": "multi_hop", "query": "Who manages the frontend team and what skills do their team members have?", "expected_route": "react", "expected_skill": "answer_with_citations", "expected_hops": 2, "language": "en", "complexity": "medium"},
    {"id": 65, "category": "multi_hop", "query": "Compare database performance across services and identify bottlenecks", "expected_route": "react", "expected_skill": "answer_with_citations", "expected_hops": 3, "language": "en", "complexity": "complex"},
    {"id": 66, "category": "multi_hop", "query": "分析微服务架构的依赖关系并找出单点故障", "expected_route": "react", "expected_skill": "answer_with_citations", "expected_hops": 3, "language": "zh", "complexity": "complex"},
    {"id": 67, "category": "multi_hop", "query": "Find teams using deprecated APIs and suggest migration paths", "expected_route": "react", "expected_skill": "answer_with_citations", "expected_hops": 3, "language": "en", "complexity": "complex"},
    {"id": 68, "category": "multi_hop", "query": "What projects depend on Service X and what would be the impact if it fails?", "expected_route": "react", "expected_skill": "answer_with_citations", "expected_hops": 2, "language": "en", "complexity": "medium"},
    {"id": 69, "category": "multi_hop", "query": "查找Alice的同事，然后找出他们共同参与的项目", "expected_route": "react", "expected_skill": "answer_with_citations", "expected_hops": 2, "language": "zh", "complexity": "medium"},
    {"id": 70, "category": "multi_hop", "query": "Trace the data flow from user input to database storage", "expected_route": "react", "expected_skill": "answer_with_citations", "expected_hops": 3, "language": "en", "complexity": "complex"},
    {"id": 71, "category": "multi_hop", "query": "Find security vulnerabilities in dependencies and recommend fixes", "expected_route": "react", "expected_skill": "answer_with_citations", "expected_hops": 2, "language": "en", "complexity": "complex"},
    {"id": 72, "category": "multi_hop", "query": "分析团队技能分布并推荐培训计划", "expected_route": "react", "expected_skill": "answer_with_citations", "expected_hops": 2, "language": "zh", "complexity": "complex"},
    {"id": 73, "category": "multi_hop", "query": "Which services need updates and what is the testing strategy for each?", "expected_route": "react", "expected_skill": "answer_with_citations", "expected_hops": 2, "language": "en", "complexity": "medium"},
    {"id": 74, "category": "multi_hop", "query": "Find code duplication across repos and suggest refactoring", "expected_route": "react", "expected_skill": "answer_with_citations", "expected_hops": 2, "language": "en", "complexity": "complex"},
    {"id": 75, "category": "multi_hop", "query": "评估新技术栈的可行性并计算迁移成本", "expected_route": "react", "expected_skill": "answer_with_citations", "expected_hops": 3, "language": "zh", "complexity": "complex"},

    # Ambiguous queries (76-85)
    {"id": 76, "category": "ambiguous", "query": "Tell me about it", "expected_route": "vector", "expected_skill": "answer_with_citations", "expected_clarification": "What topic would you like to know about?", "language": "en", "complexity": "simple"},
    {"id": 77, "category": "ambiguous", "query": "How does that work?", "expected_route": "vector", "expected_skill": "answer_with_citations", "expected_clarification": "Which system or process are you asking about?", "language": "en", "complexity": "simple"},
    {"id": 78, "category": "ambiguous", "query": "它是什么？", "expected_route": "vector", "expected_skill": "answer_with_citations", "expected_clarification": "您想了解什么？", "language": "zh", "complexity": "simple"},
    {"id": 79, "category": "ambiguous", "query": "Can you explain more?", "expected_route": "vector", "expected_skill": "answer_with_citations", "expected_clarification": "What would you like me to explain?", "language": "en", "complexity": "simple"},
    {"id": 80, "category": "ambiguous", "query": "What about performance?", "expected_route": "vector", "expected_skill": "answer_with_citations", "expected_clarification": "Performance of which system or component?", "language": "en", "complexity": "simple"},
    {"id": 81, "category": "ambiguous", "query": "谁负责这个？", "expected_route": "graph", "expected_skill": "answer_with_citations", "expected_clarification": "您指的是哪个项目或任务？", "language": "zh", "complexity": "simple"},
    {"id": 82, "category": "ambiguous", "query": "Is it good?", "expected_route": "vector", "expected_skill": "answer_with_citations", "expected_clarification": "What are you referring to?", "language": "en", "complexity": "simple"},
    {"id": 83, "category": "ambiguous", "query": "Show me the data", "expected_route": "vector", "expected_skill": "answer_with_citations", "expected_clarification": "Which dataset or data source?", "language": "en", "complexity": "simple"},
    {"id": 84, "category": "ambiguous", "query": "这个怎么用？", "expected_route": "vector", "expected_skill": "answer_with_citations", "expected_clarification": "您指的是哪个工具或功能？", "language": "zh", "complexity": "simple"},
    {"id": 85, "category": "ambiguous", "query": "What are the alternatives?", "expected_route": "vector", "expected_skill": "answer_with_citations", "expected_clarification": "Alternatives to what?", "language": "en", "complexity": "simple"},

    # Follow-up queries with context (86-95)
    {"id": 86, "category": "follow_up", "query": "Can you elaborate on that?", "context": "Previous: What is machine learning?", "expected_route": "vector", "expected_skill": "answer_with_citations", "language": "en", "complexity": "simple"},
    {"id": 87, "category": "follow_up", "query": "What are some examples?", "context": "Previous: Explain neural networks", "expected_route": "vector", "expected_skill": "answer_with_citations", "language": "en", "complexity": "simple"},
    {"id": 88, "category": "follow_up", "query": "那它的优点是什么？", "context": "Previous: 什么是深度学习", "expected_route": "vector", "expected_skill": "answer_with_citations", "language": "zh", "complexity": "simple"},
    {"id": 89, "category": "follow_up", "query": "How is it different from the previous approach?", "context": "Previous: Compare CNN and RNN", "expected_route": "vector", "expected_skill": "compare_entities", "language": "en", "complexity": "medium"},
    {"id": 90, "category": "follow_up", "query": "Who else works on this?", "context": "Previous: Who manages Team A?", "expected_route": "graph", "expected_skill": "answer_with_citations", "language": "en", "complexity": "simple"},
    {"id": 91, "category": "follow_up", "query": "它有什么缺点？", "context": "Previous: 比较微服务和单体架构", "expected_route": "vector", "expected_skill": "answer_with_citations", "language": "zh", "complexity": "medium"},
    {"id": 92, "category": "follow_up", "query": "Can you show me the implementation?", "context": "Previous: Explain backpropagation", "expected_route": "vector", "expected_skill": "answer_with_citations", "language": "en", "complexity": "medium"},
    {"id": 93, "category": "follow_up", "query": "What about the performance implications?", "context": "Previous: Compare REST and GraphQL", "expected_route": "vector", "expected_skill": "answer_with_citations", "language": "en", "complexity": "medium"},
    {"id": 94, "category": "follow_up", "query": "还有其他相关的技术吗？", "context": "Previous: 什么是注意力机制", "expected_route": "vector", "expected_skill": "answer_with_citations", "language": "zh", "complexity": "medium"},
    {"id": 95, "category": "follow_up", "query": "How does this relate to our current architecture?", "context": "Previous: What is microservices?", "expected_route": "hybrid", "expected_skill": "answer_with_citations", "language": "en", "complexity": "medium"},

    # Edge cases (96-100)
    {"id": 96, "category": "edge_case", "query": "", "expected_route": "vector", "expected_skill": "answer_with_citations", "expected_behavior": "handle_empty_query", "language": "en", "complexity": "simple"},
    {"id": 97, "category": "edge_case", "query": "Tell me about AI in 2025", "expected_route": "vector", "expected_skill": "answer_with_citations", "expected_behavior": "time_sensitive_warning", "language": "en", "complexity": "medium"},
    {"id": 98, "category": "edge_case", "query": "Is Python better than Java? But also Java is more performant than Python.", "expected_route": "vector", "expected_skill": "answer_with_citations", "expected_behavior": "handle_contradiction", "language": "en", "complexity": "medium"},
    {"id": 99, "category": "edge_case", "query": "机器学习是不是不需要数据？", "expected_route": "vector", "expected_skill": "answer_with_citations", "expected_behavior": "correct_false_premise", "language": "zh", "complexity": "medium"},
    {"id": 100, "category": "edge_case", "query": "a" * 500, "expected_route": "vector", "expected_skill": "answer_with_citations", "expected_behavior": "handle_excessive_length", "language": "en", "complexity": "simple"},
]


def save_golden_dataset(output_path: str = "tests/golden_dataset.json"):
    """Save the golden dataset to JSON file."""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(GOLDEN_DATASET, f, indent=2, ensure_ascii=False)

    print(f"[OK] Golden dataset saved to {output_file}")
    print(f"[INFO] Total queries: {len(GOLDEN_DATASET)}")

    # Print category breakdown
    from collections import Counter
    categories = Counter(item["category"] for item in GOLDEN_DATASET)
    print("\n[INFO] Category breakdown:")
    for category, count in categories.items():
        print(f"  - {category}: {count}")


def validate_dataset():
    """Validate the dataset structure and completeness."""
    print("\n[INFO] Validating dataset...")

    errors = []

    # Check total count
    if len(GOLDEN_DATASET) != 100:
        errors.append(f"Expected 100 queries, got {len(GOLDEN_DATASET)}")

    # Check category counts
    from collections import Counter
    categories = Counter(item["category"] for item in GOLDEN_DATASET)
    expected = {
        "concept": 25,
        "relationship": 20,
        "comparison": 15,
        "multi_hop": 15,
        "ambiguous": 10,
        "follow_up": 10,
        "edge_case": 5,
    }

    for cat, expected_count in expected.items():
        actual_count = categories.get(cat, 0)
        if actual_count != expected_count:
            errors.append(f"Category '{cat}': expected {expected_count}, got {actual_count}")

    # Check IDs are sequential
    ids = [item["id"] for item in GOLDEN_DATASET]
    if ids != list(range(1, 101)):
        errors.append(f"IDs are not sequential 1-100")

    # Check required fields
    required_fields = ["id", "category", "query", "expected_route", "expected_skill", "language", "complexity"]
    for item in GOLDEN_DATASET:
        for field in required_fields:
            if field not in item:
                errors.append(f"Query {item.get('id', '?')} missing field: {field}")

    if errors:
        print("[ERROR] Validation errors:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("[OK] Validation passed!")
        return True


if __name__ == "__main__":
    print("[INFO] Creating Golden Dataset for A/B Testing...\n")

    if validate_dataset():
        save_golden_dataset()
        print("\n[OK] Golden dataset creation complete!")
    else:
        print("\n[ERROR] Dataset validation failed. Please fix errors before saving.")

