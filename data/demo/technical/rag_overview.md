# RAG 技术综述

## 1. RAG 简介

RAG (Retrieval-Augmented Generation) 是一种结合检索和生成的技术，通过从外部知识库检索相关信息来增强大语言模型的生成能力。

### 1.1 核心思想

传统的大语言模型依赖于训练时学到的知识，存在以下问题：
- 知识更新滞后
- 无法访问私有数据
- 容易产生幻觉

RAG 通过以下方式解决这些问题：
1. 将查询转换为向量表示
2. 从知识库检索相关文档
3. 将检索结果作为上下文提供给 LLM
4. LLM 基于上下文生成答案

### 1.2 RAG vs Fine-tuning

| 特性 | RAG | Fine-tuning |
|------|-----|-------------|
| 知识更新 | 实时更新 | 需要重新训练 |
| 成本 | 低 | 高 |
| 可解释性 | 高（可追溯来源） | 低 |
| 适用场景 | 知识密集型任务 | 特定领域任务 |

## 2. RAG 架构

### 2.1 基础架构

```
用户查询 → 查询编码 → 向量检索 → 上下文构建 → LLM生成 → 答案
```

### 2.2 关键组件

**1. 文档处理**
- 文档加载
- 文本分块（Chunking）
- 向量化（Embedding）
- 索引构建

**2. 检索系统**
- 向量数据库（ChromaDB, Pinecone, Weaviate）
- 相似度计算（余弦相似度、点积）
- Top-K 检索

**3. 生成系统**
- Prompt 构建
- LLM 调用
- 答案后处理

## 3. 检索策略

### 3.1 Dense Retrieval（密集检索）

使用神经网络将文本编码为稠密向量：

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
query_embedding = model.encode("什么是RAG?")
doc_embeddings = model.encode(documents)

# 计算相似度
similarities = cosine_similarity(query_embedding, doc_embeddings)
```

**优点**：
- 语义理解能力强
- 可以处理同义词和改写

**缺点**：
- 计算成本高
- 对罕见词汇效果差

### 3.2 Sparse Retrieval（稀疏检索）

使用传统的关键词匹配方法（如 BM25）：

```python
from rank_bm25 import BM25Okapi

tokenized_docs = [doc.split() for doc in documents]
bm25 = BM25Okapi(tokenized_docs)

query = "什么是RAG"
scores = bm25.get_scores(query.split())
```

**优点**：
- 速度快
- 对精确匹配效果好

**缺点**：
- 无法理解语义
- 对同义词不敏感

### 3.3 Hybrid Retrieval（混合检索）

结合 Dense 和 Sparse 检索的优点：

```python
# 1. 分别检索
dense_results = dense_retriever.search(query, top_k=20)
sparse_results = sparse_retriever.search(query, top_k=20)

# 2. 分数融合
final_scores = 0.7 * dense_scores + 0.3 * sparse_scores

# 3. 重排序
final_results = rerank(final_scores, top_k=5)
```

## 4. 高级 RAG 技术

### 4.1 Query Rewriting（查询重写）

将复杂查询改写为更适合检索的形式：

```python
def rewrite_query(query):
    prompt = f"""
    将以下查询改写为更适合检索的形式：
    原查询：{query}
    改写后：
    """
    return llm.generate(prompt)
```

### 4.2 HyDE (Hypothetical Document Embeddings)

生成假设性文档来改进检索：

```python
def hyde_retrieval(query):
    # 1. 生成假设性答案
    hypothetical_doc = llm.generate(f"回答问题：{query}")
    
    # 2. 使用假设性答案检索
    results = retriever.search(hypothetical_doc)
    
    return results
```

### 4.3 Self-RAG

让模型自我评估检索结果的相关性：

```python
def self_rag(query, documents):
    # 1. 评估文档相关性
    relevance_scores = []
    for doc in documents:
        score = llm.evaluate_relevance(query, doc)
        relevance_scores.append(score)
    
    # 2. 过滤低相关性文档
    filtered_docs = [doc for doc, score in zip(documents, relevance_scores) 
                     if score > threshold]
    
    # 3. 生成答案
    answer = llm.generate(query, filtered_docs)
    
    # 4. 评估答案质量
    quality = llm.evaluate_quality(query, answer, filtered_docs)
    
    # 5. 如果质量不足，补充检索
    if quality < threshold:
        additional_docs = retriever.search(query, top_k=5)
        answer = llm.generate(query, filtered_docs + additional_docs)
    
    return answer
```

### 4.4 RAPTOR (Recursive Abstractive Processing)

递归地总结和索引文档：

```
原始文档 → 分块 → 总结 → 再分块 → 再总结 → 多层索引
```

### 4.5 Query Decomposition（查询分解）

将复杂查询分解为多个子查询：

```python
def decompose_query(complex_query):
    prompt = f"""
    将以下复杂查询分解为多个简单子查询：
    查询：{complex_query}
    子查询：
    """
    sub_queries = llm.generate(prompt).split('\n')
    
    # 分别检索每个子查询
    all_results = []
    for sub_query in sub_queries:
        results = retriever.search(sub_query)
        all_results.extend(results)
    
    # 合并结果
    return merge_results(all_results)
```

## 5. 评估指标

### 5.1 检索质量指标

**Precision@K**：前 K 个结果中相关文档的比例
```python
precision_at_k = relevant_docs_in_top_k / k
```

**Recall@K**：前 K 个结果覆盖的相关文档比例
```python
recall_at_k = relevant_docs_in_top_k / total_relevant_docs
```

**MRR (Mean Reciprocal Rank)**：第一个相关文档的排名倒数
```python
mrr = 1 / rank_of_first_relevant_doc
```

**NDCG (Normalized Discounted Cumulative Gain)**：考虑排序的评估指标

### 5.2 生成质量指标

- **Faithfulness**：答案是否忠实于检索文档
- **Answer Relevance**：答案是否回答了问题
- **Context Relevance**：检索文档是否相关

## 6. 优化技巧

### 6.1 Chunking 策略

**固定大小分块**：
```python
chunk_size = 512
overlap = 50
chunks = [text[i:i+chunk_size] 
          for i in range(0, len(text), chunk_size-overlap)]
```

**语义分块**：
- 按段落分块
- 按句子分块
- 按主题分块

### 6.2 Embedding 优化

- 使用领域特定的 Embedding 模型
- Fine-tune Embedding 模型
- 使用多语言 Embedding 模型

### 6.3 Prompt 工程

```python
prompt_template = """
基于以下上下文回答问题。如果上下文中没有相关信息，请说"我不知道"。

上下文：
{context}

问题：{question}

答案：
"""
```

## 7. 实际应用

### 7.1 企业知识库

- 内部文档问答
- 政策查询
- 技术支持

### 7.2 客户服务

- 智能客服
- FAQ 自动回答
- 工单分类

### 7.3 内容生成

- 报告撰写
- 邮件回复
- 文档总结

## 8. 挑战与未来

### 8.1 当前挑战

- **长文档处理**：如何有效处理超长文档
- **多跳推理**：需要多次检索才能回答的问题
- **实时更新**：如何快速更新知识库
- **成本控制**：降低 Embedding 和 LLM 调用成本

### 8.2 未来方向

- **多模态 RAG**：支持图片、表格、视频
- **个性化 RAG**：根据用户偏好定制检索
- **主动学习**：从用户反馈中学习
- **联邦 RAG**：跨组织的知识共享

## 9. 参考资源

### 9.1 论文

- "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" (Lewis et al., 2020)
- "Self-RAG: Learning to Retrieve, Generate, and Critique" (Asai et al., 2023)
- "RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval" (Sarthi et al., 2024)

### 9.2 开源项目

- LangChain: https://github.com/langchain-ai/langchain
- LlamaIndex: https://github.com/run-llama/llama_index
- Haystack: https://github.com/deepset-ai/haystack

### 9.3 向量数据库

- ChromaDB: https://www.trychroma.com/
- Pinecone: https://www.pinecone.io/
- Weaviate: https://weaviate.io/
- Milvus: https://milvus.io/

---

**文档版本**：v1.0  
**最后更新**：2026年1月  
**作者**：AI Research Team
