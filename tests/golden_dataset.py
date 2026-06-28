"""
Golden dataset with 100 annotated queries for quality weight optimization.

Each entry contains:
- query: User question (English/Chinese)
- expected_route: Expected routing decision
- human_quality_score: Human-judged quality [0.0, 1.0]
- complexity: Query complexity (simple/medium/complex)
- category: Query type (factual/analytical/procedural/comparative)
"""

from typing import List, Dict, Any


GOLDEN_DATASET: List[Dict[str, Any]] = [
    # Simple factual queries (high quality expected)
    {
        "query": "What is Python?",
        "expected_route": "vector",
        "human_quality_score": 0.95,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "什么是机器学习？",
        "expected_route": "vector",
        "human_quality_score": 0.93,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "Define REST API",
        "expected_route": "vector",
        "human_quality_score": 0.94,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "解释什么是Docker",
        "expected_route": "vector",
        "human_quality_score": 0.92,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "What is Git?",
        "expected_route": "vector",
        "human_quality_score": 0.96,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "什么是深度学习？",
        "expected_route": "vector",
        "human_quality_score": 0.91,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "Explain microservices",
        "expected_route": "vector",
        "human_quality_score": 0.90,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "什么是Kubernetes？",
        "expected_route": "vector",
        "human_quality_score": 0.92,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "What is SQL?",
        "expected_route": "vector",
        "human_quality_score": 0.95,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "解释什么是NoSQL数据库",
        "expected_route": "vector",
        "human_quality_score": 0.89,
        "complexity": "simple",
        "category": "factual"
    },

    # Medium complexity queries
    {
        "query": "How do transformers work in NLP?",
        "expected_route": "hybrid",
        "human_quality_score": 0.85,
        "complexity": "medium",
        "category": "analytical"
    },
    {
        "query": "Transformer模型的注意力机制是如何工作的？",
        "expected_route": "hybrid",
        "human_quality_score": 0.84,
        "complexity": "medium",
        "category": "analytical"
    },
    {
        "query": "Compare MongoDB and PostgreSQL",
        "expected_route": "hybrid",
        "human_quality_score": 0.82,
        "complexity": "medium",
        "category": "comparative"
    },
    {
        "query": "比较React和Vue框架的优缺点",
        "expected_route": "hybrid",
        "human_quality_score": 0.80,
        "complexity": "medium",
        "category": "comparative"
    },
    {
        "query": "How to implement authentication in Flask?",
        "expected_route": "hybrid",
        "human_quality_score": 0.83,
        "complexity": "medium",
        "category": "procedural"
    },
    {
        "query": "如何在Django中实现用户认证？",
        "expected_route": "hybrid",
        "human_quality_score": 0.81,
        "complexity": "medium",
        "category": "procedural"
    },
    {
        "query": "What are the trade-offs between REST and GraphQL?",
        "expected_route": "hybrid",
        "human_quality_score": 0.79,
        "complexity": "medium",
        "category": "comparative"
    },
    {
        "query": "微服务架构的优缺点是什么？",
        "expected_route": "hybrid",
        "human_quality_score": 0.78,
        "complexity": "medium",
        "category": "analytical"
    },
    {
        "query": "Explain CAP theorem with examples",
        "expected_route": "hybrid",
        "human_quality_score": 0.86,
        "complexity": "medium",
        "category": "analytical"
    },
    {
        "query": "解释分布式系统中的一致性协议",
        "expected_route": "hybrid",
        "human_quality_score": 0.84,
        "complexity": "medium",
        "category": "analytical"
    },

    # Complex queries requiring reasoning
    {
        "query": "Design a scalable architecture for real-time chat application",
        "expected_route": "react",
        "human_quality_score": 0.75,
        "complexity": "complex",
        "category": "analytical"
    },
    {
        "query": "设计一个支持百万并发的实时推荐系统架构",
        "expected_route": "react",
        "human_quality_score": 0.73,
        "complexity": "complex",
        "category": "analytical"
    },
    {
        "query": "How would you debug a memory leak in a production system?",
        "expected_route": "react",
        "human_quality_score": 0.77,
        "complexity": "complex",
        "category": "procedural"
    },
    {
        "query": "如何诊断和解决分布式系统中的性能瓶颈？",
        "expected_route": "react",
        "human_quality_score": 0.74,
        "complexity": "complex",
        "category": "procedural"
    },
    {
        "query": "What are the best practices for securing a cloud-native application?",
        "expected_route": "react",
        "human_quality_score": 0.76,
        "complexity": "complex",
        "category": "analytical"
    },
    {
        "query": "云原生应用的安全最佳实践有哪些？",
        "expected_route": "react",
        "human_quality_score": 0.72,
        "complexity": "complex",
        "category": "analytical"
    },
    {
        "query": "How to migrate a monolith to microservices without downtime?",
        "expected_route": "react",
        "human_quality_score": 0.78,
        "complexity": "complex",
        "category": "procedural"
    },
    {
        "query": "如何实现零停机的数据库迁移？",
        "expected_route": "react",
        "human_quality_score": 0.75,
        "complexity": "complex",
        "category": "procedural"
    },
    {
        "query": "Compare different approaches to handling eventual consistency",
        "expected_route": "react",
        "human_quality_score": 0.74,
        "complexity": "complex",
        "category": "comparative"
    },
    {
        "query": "分析不同的缓存策略及其适用场景",
        "expected_route": "react",
        "human_quality_score": 0.73,
        "complexity": "complex",
        "category": "analytical"
    },

    # Edge cases and ambiguous queries (lower quality)
    {
        "query": "Best programming language?",
        "expected_route": "vector",
        "human_quality_score": 0.45,
        "complexity": "simple",
        "category": "comparative"
    },
    {
        "query": "最好的数据库是什么？",
        "expected_route": "vector",
        "human_quality_score": 0.42,
        "complexity": "simple",
        "category": "comparative"
    },
    {
        "query": "How to code?",
        "expected_route": "vector",
        "human_quality_score": 0.38,
        "complexity": "simple",
        "category": "procedural"
    },
    {
        "query": "怎么学编程？",
        "expected_route": "vector",
        "human_quality_score": 0.40,
        "complexity": "simple",
        "category": "procedural"
    },
    {
        "query": "Tell me about AI",
        "expected_route": "vector",
        "human_quality_score": 0.50,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "讲讲人工智能",
        "expected_route": "vector",
        "human_quality_score": 0.48,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "Why is Python slow?",
        "expected_route": "hybrid",
        "human_quality_score": 0.65,
        "complexity": "medium",
        "category": "analytical"
    },
    {
        "query": "为什么JavaScript这么流行？",
        "expected_route": "hybrid",
        "human_quality_score": 0.63,
        "complexity": "medium",
        "category": "analytical"
    },
    {
        "query": "What's wrong with my code?",
        "expected_route": "react",
        "human_quality_score": 0.30,
        "complexity": "complex",
        "category": "procedural"
    },
    {
        "query": "我的程序为什么不工作？",
        "expected_route": "react",
        "human_quality_score": 0.28,
        "complexity": "complex",
        "category": "procedural"
    },

    # Additional factual queries
    {
        "query": "What is ACID in databases?",
        "expected_route": "vector",
        "human_quality_score": 0.93,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "解释HTTP和HTTPS的区别",
        "expected_route": "vector",
        "human_quality_score": 0.91,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "What is OAuth2?",
        "expected_route": "vector",
        "human_quality_score": 0.92,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "什么是JWT令牌？",
        "expected_route": "vector",
        "human_quality_score": 0.90,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "Explain CORS",
        "expected_route": "vector",
        "human_quality_score": 0.89,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "什么是WebSocket？",
        "expected_route": "vector",
        "human_quality_score": 0.88,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "What is CI/CD?",
        "expected_route": "vector",
        "human_quality_score": 0.94,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "解释DevOps的概念",
        "expected_route": "vector",
        "human_quality_score": 0.87,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "What is container orchestration?",
        "expected_route": "vector",
        "human_quality_score": 0.86,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "什么是服务网格？",
        "expected_route": "vector",
        "human_quality_score": 0.85,
        "complexity": "simple",
        "category": "factual"
    },

    # Additional medium complexity queries
    {
        "query": "How does garbage collection work in Java?",
        "expected_route": "hybrid",
        "human_quality_score": 0.82,
        "complexity": "medium",
        "category": "analytical"
    },
    {
        "query": "Python的GIL是如何影响多线程性能的？",
        "expected_route": "hybrid",
        "human_quality_score": 0.80,
        "complexity": "medium",
        "category": "analytical"
    },
    {
        "query": "Compare async/await vs promises in JavaScript",
        "expected_route": "hybrid",
        "human_quality_score": 0.81,
        "complexity": "medium",
        "category": "comparative"
    },
    {
        "query": "比较SQL和NoSQL数据库的查询性能",
        "expected_route": "hybrid",
        "human_quality_score": 0.79,
        "complexity": "medium",
        "category": "comparative"
    },
    {
        "query": "How to optimize database queries?",
        "expected_route": "hybrid",
        "human_quality_score": 0.83,
        "complexity": "medium",
        "category": "procedural"
    },
    {
        "query": "如何提高API响应速度？",
        "expected_route": "hybrid",
        "human_quality_score": 0.78,
        "complexity": "medium",
        "category": "procedural"
    },
    {
        "query": "What are the principles of RESTful API design?",
        "expected_route": "hybrid",
        "human_quality_score": 0.84,
        "complexity": "medium",
        "category": "analytical"
    },
    {
        "query": "解释事件驱动架构的优势",
        "expected_route": "hybrid",
        "human_quality_score": 0.77,
        "complexity": "medium",
        "category": "analytical"
    },
    {
        "query": "How to implement rate limiting?",
        "expected_route": "hybrid",
        "human_quality_score": 0.80,
        "complexity": "medium",
        "category": "procedural"
    },
    {
        "query": "如何实现分布式锁？",
        "expected_route": "hybrid",
        "human_quality_score": 0.76,
        "complexity": "medium",
        "category": "procedural"
    },

    # Additional complex queries
    {
        "query": "Design a fault-tolerant distributed cache system",
        "expected_route": "react",
        "human_quality_score": 0.74,
        "complexity": "complex",
        "category": "analytical"
    },
    {
        "query": "设计一个高可用的消息队列系统",
        "expected_route": "react",
        "human_quality_score": 0.72,
        "complexity": "complex",
        "category": "analytical"
    },
    {
        "query": "How would you implement a recommendation engine?",
        "expected_route": "react",
        "human_quality_score": 0.76,
        "complexity": "complex",
        "category": "analytical"
    },
    {
        "query": "如何实现一个实时数据处理管道？",
        "expected_route": "react",
        "human_quality_score": 0.73,
        "complexity": "complex",
        "category": "procedural"
    },
    {
        "query": "What are strategies for handling distributed transactions?",
        "expected_route": "react",
        "human_quality_score": 0.77,
        "complexity": "complex",
        "category": "analytical"
    },
    {
        "query": "如何设计一个多租户SaaS架构？",
        "expected_route": "react",
        "human_quality_score": 0.71,
        "complexity": "complex",
        "category": "analytical"
    },
    {
        "query": "How to implement blue-green deployment?",
        "expected_route": "react",
        "human_quality_score": 0.75,
        "complexity": "complex",
        "category": "procedural"
    },
    {
        "query": "如何实现服务的优雅降级和熔断？",
        "expected_route": "react",
        "human_quality_score": 0.74,
        "complexity": "complex",
        "category": "procedural"
    },
    {
        "query": "Compare different load balancing algorithms",
        "expected_route": "react",
        "human_quality_score": 0.73,
        "complexity": "complex",
        "category": "comparative"
    },
    {
        "query": "分析不同的数据分片策略",
        "expected_route": "react",
        "human_quality_score": 0.70,
        "complexity": "complex",
        "category": "analytical"
    },

    # More edge cases
    {
        "query": "Is Node.js better than Python?",
        "expected_route": "hybrid",
        "human_quality_score": 0.55,
        "complexity": "medium",
        "category": "comparative"
    },
    {
        "query": "React比Angular好吗？",
        "expected_route": "hybrid",
        "human_quality_score": 0.53,
        "complexity": "medium",
        "category": "comparative"
    },
    {
        "query": "Should I use SQL or NoSQL?",
        "expected_route": "hybrid",
        "human_quality_score": 0.52,
        "complexity": "medium",
        "category": "comparative"
    },
    {
        "query": "我应该学哪种编程语言？",
        "expected_route": "vector",
        "human_quality_score": 0.43,
        "complexity": "simple",
        "category": "comparative"
    },
    {
        "query": "How long to learn programming?",
        "expected_route": "vector",
        "human_quality_score": 0.41,
        "complexity": "simple",
        "category": "procedural"
    },
    {
        "query": "学会Python要多久？",
        "expected_route": "vector",
        "human_quality_score": 0.39,
        "complexity": "simple",
        "category": "procedural"
    },
    {
        "query": "What is the future of AI?",
        "expected_route": "hybrid",
        "human_quality_score": 0.58,
        "complexity": "medium",
        "category": "analytical"
    },
    {
        "query": "区块链技术的未来发展如何？",
        "expected_route": "hybrid",
        "human_quality_score": 0.56,
        "complexity": "medium",
        "category": "analytical"
    },
    {
        "query": "Why do developers hate PHP?",
        "expected_route": "hybrid",
        "human_quality_score": 0.47,
        "complexity": "medium",
        "category": "analytical"
    },
    {
        "query": "为什么大家都说Java臃肿？",
        "expected_route": "hybrid",
        "human_quality_score": 0.44,
        "complexity": "medium",
        "category": "analytical"
    },

    # Additional high-quality queries
    {
        "query": "What is the difference between TCP and UDP?",
        "expected_route": "vector",
        "human_quality_score": 0.94,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "解释同步和异步编程的区别",
        "expected_route": "vector",
        "human_quality_score": 0.90,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "What is denormalization in databases?",
        "expected_route": "vector",
        "human_quality_score": 0.88,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "什么是数据库索引？",
        "expected_route": "vector",
        "human_quality_score": 0.89,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "Explain the singleton pattern",
        "expected_route": "vector",
        "human_quality_score": 0.91,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "什么是观察者模式？",
        "expected_route": "vector",
        "human_quality_score": 0.87,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "What is TDD?",
        "expected_route": "vector",
        "human_quality_score": 0.93,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "解释什么是持续集成",
        "expected_route": "vector",
        "human_quality_score": 0.86,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "What is a reverse proxy?",
        "expected_route": "vector",
        "human_quality_score": 0.92,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "什么是负载均衡？",
        "expected_route": "vector",
        "human_quality_score": 0.88,
        "complexity": "simple",
        "category": "factual"
    },

    # Additional queries to reach 100
    {
        "query": "What is the difference between GET and POST?",
        "expected_route": "vector",
        "human_quality_score": 0.94,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "解释CSS盒模型",
        "expected_route": "vector",
        "human_quality_score": 0.87,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "How does CDN work?",
        "expected_route": "hybrid",
        "human_quality_score": 0.82,
        "complexity": "medium",
        "category": "analytical"
    },
    {
        "query": "如何优化前端性能？",
        "expected_route": "hybrid",
        "human_quality_score": 0.79,
        "complexity": "medium",
        "category": "procedural"
    },
    {
        "query": "Design a distributed logging system",
        "expected_route": "react",
        "human_quality_score": 0.76,
        "complexity": "complex",
        "category": "analytical"
    },
    {
        "query": "如何设计一个秒杀系统？",
        "expected_route": "react",
        "human_quality_score": 0.71,
        "complexity": "complex",
        "category": "analytical"
    },
    {
        "query": "What is serverless computing?",
        "expected_route": "vector",
        "human_quality_score": 0.90,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "解释什么是边缘计算",
        "expected_route": "vector",
        "human_quality_score": 0.86,
        "complexity": "simple",
        "category": "factual"
    },
    {
        "query": "Compare SQL joins: INNER vs OUTER",
        "expected_route": "hybrid",
        "human_quality_score": 0.81,
        "complexity": "medium",
        "category": "comparative"
    },
    {
        "query": "如何实现消息队列的高可用？",
        "expected_route": "react",
        "human_quality_score": 0.72,
        "complexity": "complex",
        "category": "procedural"
    },
]


def get_dataset() -> List[Dict[str, Any]]:
    """Return the golden dataset."""
    return GOLDEN_DATASET


def get_dataset_by_complexity(complexity: str) -> List[Dict[str, Any]]:
    """Filter dataset by complexity level."""
    return [item for item in GOLDEN_DATASET if item["complexity"] == complexity]


def get_dataset_by_category(category: str) -> List[Dict[str, Any]]:
    """Filter dataset by category."""
    return [item for item in GOLDEN_DATASET if item["category"] == category]


def validate_dataset() -> bool:
    """
    Validate the golden dataset structure and constraints.

    Returns:
        True if valid, raises AssertionError otherwise
    """
    assert len(GOLDEN_DATASET) == 100, f"Expected 100 queries, got {len(GOLDEN_DATASET)}"

    for i, item in enumerate(GOLDEN_DATASET):
        # Check required fields
        assert "query" in item, f"Item {i} missing 'query'"
        assert "expected_route" in item, f"Item {i} missing 'expected_route'"
        assert "human_quality_score" in item, f"Item {i} missing 'human_quality_score'"
        assert "complexity" in item, f"Item {i} missing 'complexity'"
        assert "category" in item, f"Item {i} missing 'category'"

        # Validate values
        assert item["expected_route"] in ["vector", "hybrid", "graph", "react"], \
            f"Item {i} has invalid route: {item['expected_route']}"
        assert 0.0 <= item["human_quality_score"] <= 1.0, \
            f"Item {i} has invalid quality score: {item['human_quality_score']}"
        assert item["complexity"] in ["simple", "medium", "complex"], \
            f"Item {i} has invalid complexity: {item['complexity']}"
        assert item["category"] in ["factual", "analytical", "procedural", "comparative"], \
            f"Item {i} has invalid category: {item['category']}"

    return True
