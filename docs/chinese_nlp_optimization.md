# Chinese NLP Optimization

This module provides comprehensive Chinese language support for the RAG system, including tokenization, synonym expansion, query preprocessing, and Chinese-specific evaluation metrics.

## Features

### 1. Chinese Tokenization (`chinese_tokenizer.py`)

Powered by [jieba](https://github.com/fxsjy/jieba), the most popular Chinese text segmentation library.

**Key capabilities:**
- Standard tokenization with multiple modes (precise, full, search)
- Keyword extraction using TF-IDF and TextRank algorithms
- Custom dictionary support for domain-specific terms
- Part-of-speech tagging support

**Usage:**
```python
from app.services.chinese_tokenizer import get_tokenizer

tokenizer = get_tokenizer()

# Basic tokenization
tokens = tokenizer.tokenize("我想了解人工智能的应用")
# Output: ['我', '想', '了解', '人工智能', '的', '应用']

# Search-optimized tokenization (more granular)
tokens = tokenizer.tokenize_for_search("中国人民银行")
# Output: ['中国', '人民', '银行', '中国人民银行']

# Extract keywords
keywords = tokenizer.extract_keywords("人工智能技术在医疗领域应用广泛", topK=3)
# Output: ['人工智能', '医疗', '技术']

# Add custom terms
tokenizer.add_word("RAG系统", freq=1000)
```

### 2. Synonym Expansion (`synonym_expander.py`)

Expands queries with synonyms to improve recall without sacrificing precision.

**Key capabilities:**
- Built-in synonym dictionary for common technical and business terms
- Custom synonym dictionary support
- Multiple expansion strategies (append, replace with OR clauses)
- Configurable expansion limits

**Usage:**
```python
from app.services.synonym_expander import get_expander

expander = get_expander()

# Get synonyms for a word
synonyms = expander.get_synonyms("人工智能")
# Output: {'AI', '机器学习', '深度学习'}

# Expand query tokens
tokens = ["人工智能", "应用"]
expanded = expander.expand_query(tokens, max_expansions=2)
# Output: ['人工智能', '应用', 'AI', '机器学习', '使用', '运用']

# Expand query string with OR strategy
expanded_query = expander.expand_query_string(
    "数据库优化",
    ["数据库", "优化"],
    strategy="replace"
)
# Output: "(数据库 OR DB OR 数据存储) (优化 OR 改进 OR 提升)"
```

**Default synonym groups include:**
- Technical terms: AI, database, server, network, security, performance
- Business terms: employee, company, management, policy, reimbursement
- Common verbs: use, create, delete, modify, query, submit
- Common adjectives: important, simple, complex, fast, secure

### 3. Query Preprocessing (`chinese_query_preprocessor.py`)

Comprehensive query preprocessing pipeline for Chinese text.

**Key capabilities:**
- Language detection (Chinese, English, mixed)
- Text normalization (full-width to half-width, quote normalization)
- Stopword removal with configurable stopword list
- Automatic synonym expansion
- Keyword extraction

**Usage:**
```python
from app.services.chinese_query_preprocessor import get_preprocessor

preprocessor = get_preprocessor()

# Basic preprocessing
query = "我想了解人工智能的应用"
processed = preprocessor.preprocess(query)
# Output: "了解 人工智能 应用 AI 机器学习"

# Get detailed metadata
result = preprocessor.preprocess(query, return_metadata=True)
# Output: {
#     "processed_query": "了解 人工智能 应用 AI 机器学习",
#     "original_query": "我想了解人工智能的应用",
#     "tokens": ['我', '想', '了解', '人工智能', '的', '应用'],
#     "filtered_tokens": ['了解', '人工智能', '应用'],
#     "expanded_tokens": ['了解', '人工智能', '应用', 'AI', '机器学习'],
#     "language": "chinese",
#     "stopwords_removed": 3,
#     "synonyms_added": 2
# }

# Detect language
lang = preprocessor.detect_language("使用Python开发应用")
# Output: "mixed"

# Extract keywords
keywords = preprocessor.extract_keywords("如何优化数据库性能", topK=3)
# Output: ['数据库', '性能', '优化']
```

### 4. Document Indexing (`chinese_document_indexer.py`)

Enhanced document preprocessing for better Chinese text indexing.

**Key capabilities:**
- Language-aware document preprocessing
- Automatic tokenization and keyword extraction
- Sentence-boundary-aware chunking
- Metadata enrichment for filtering and ranking

**Usage:**
```python
from app.services.chinese_document_indexer import get_indexer, get_chunker
from langchain.schema import Document

indexer = get_indexer()

# Preprocess a document
doc = Document(
    page_content="人工智能技术在医疗领域的应用越来越广泛。",
    metadata={"source": "medical_ai.txt"}
)
processed_doc = indexer.preprocess_document(doc)
# Adds metadata: language, tokens, keywords, segmented_text

# Chunk a long document
chunker = get_chunker(chunk_size=500, chunk_overlap=50)
long_doc = Document(page_content="很长的文档内容..." * 100)
chunks = chunker.chunk_document(long_doc)
# Returns list of Document objects with chunk metadata
```

### 5. Evaluation Metrics (`chinese_evaluation_metrics.py`)

Chinese-specific metrics for evaluating retrieval quality.

**Key capabilities:**
- Token overlap scoring
- Keyword coverage measurement
- Semantic density calculation
- System comparison
- Document ranking

**Usage:**
```python
from app.services.chinese_evaluation_metrics import get_metrics

metrics = get_metrics()

# Calculate metrics for retrieved documents
query = "人工智能在医疗领域的应用"
documents = [
    "人工智能技术在医疗诊断中发挥重要作用...",
    "机器学习算法可以帮助医生分析病例...",
    "深度学习在医学影像识别中的应用..."
]

results = metrics.calculate_chinese_metrics(query, documents)
# Output: {
#     "token_overlap_scores": [0.75, 0.60, 0.55],
#     "keyword_coverage_scores": [0.80, 0.70, 0.65],
#     "semantic_density_scores": [0.72, 0.68, 0.70],
#     "avg_token_overlap": 0.63,
#     "avg_keyword_coverage": 0.72,
#     "avg_semantic_density": 0.70
# }

# Compare multiple systems
system_results = {
    "vector_only": documents[:2],
    "hybrid": documents,
    "rerank": documents[::-1]
}
comparison = metrics.compare_systems(query, system_results)

# Rank documents by Chinese-specific score
ranked = metrics.rank_documents_by_chinese_score(query, documents)
# Output: [(0, 0.76), (1, 0.66), (2, 0.63)]  # (index, score)
```

## Installation

The Chinese NLP features require the `jieba` library:

```bash
pip install jieba>=0.42.1
```

This dependency is already included in `pyproject.toml`.

## Configuration

### Custom Dictionary

To add domain-specific terms, create a custom dictionary file:

```text
# custom_dict.txt
RAG系统 1000 n
向量检索 800 n
语义搜索 800 n
```

Then load it:

```python
from app.services.chinese_tokenizer import ChineseTokenizer

tokenizer = ChineseTokenizer(user_dict_path="path/to/custom_dict.txt")
```

### Custom Synonyms

Create a JSON file with synonym mappings:

```json
{
  "RAG": ["检索增强生成", "Retrieval Augmented Generation"],
  "向量数据库": ["向量存储", "向量检索引擎", "Chroma", "Pinecone"]
}
```

Then load it:

```python
from app.services.synonym_expander import SynonymExpander

expander = SynonymExpander(synonym_dict_path="path/to/synonyms.json")
```

### Custom Stopwords

Add or remove stopwords dynamically:

```python
from app.services.chinese_query_preprocessor import get_preprocessor

preprocessor = get_preprocessor()

# Add custom stopwords
preprocessor.add_stopword("某个")
preprocessor.add_stopword("特定")

# Remove default stopwords
preprocessor.remove_stopword("什么")
```

## Integration with RAG Pipeline

### Query Processing

```python
from app.services.chinese_query_preprocessor import get_preprocessor

preprocessor = get_preprocessor()

def process_user_query(query: str) -> str:
    """Preprocess user query before retrieval."""
    # Detect language
    lang = preprocessor.detect_language(query)
    
    # Only apply Chinese preprocessing for Chinese/mixed queries
    if lang in ["chinese", "mixed"]:
        processed = preprocessor.preprocess(
            query,
            expand_synonyms=True  # Enable synonym expansion
        )
        return processed
    
    return query
```

### Document Ingestion

```python
from app.services.chinese_document_indexer import get_indexer, get_chunker

indexer = get_indexer()
chunker = get_chunker(chunk_size=500, chunk_overlap=50)

def ingest_document(doc: Document) -> List[Document]:
    """Preprocess and chunk document for indexing."""
    # Preprocess document
    processed = indexer.preprocess_document(doc)
    
    # Chunk if needed
    if len(processed.page_content) > 500:
        chunks = chunker.chunk_document(processed)
        return chunks
    
    return [processed]
```

### Evaluation

```python
from app.services.chinese_evaluation_metrics import get_metrics

metrics = get_metrics()

def evaluate_retrieval(query: str, retrieved_docs: List[str], relevant_indices: List[int]):
    """Evaluate retrieval quality with Chinese-specific metrics."""
    results = metrics.calculate_chinese_metrics(
        query,
        retrieved_docs,
        relevant_indices
    )
    
    print(f"Average Token Overlap: {results['avg_token_overlap']:.2f}")
    print(f"Average Keyword Coverage: {results['avg_keyword_coverage']:.2f}")
    print(f"Precision: {results['precision']:.2f}")
    print(f"Recall: {results['recall']:.2f}")
    print(f"F1 Score: {results['f1_score']:.2f}")
```

## Performance Considerations

### Tokenization

- **First call**: Jieba loads its dictionary (~30MB) on first use, taking ~1-2 seconds
- **Subsequent calls**: Very fast (<1ms per query)
- **Recommendation**: Initialize tokenizer at application startup

### Synonym Expansion

- **Memory**: Default dictionary uses ~50KB
- **Speed**: O(n) where n is number of tokens, typically <1ms
- **Recommendation**: Limit `max_expansions` to 2-3 to avoid query bloat

### Query Preprocessing

- **Typical latency**: 5-10ms for Chinese queries, <1ms for English
- **Bottleneck**: Tokenization and keyword extraction
- **Recommendation**: Cache preprocessed queries for repeated searches

## Testing

Run the unit tests:

```bash
pytest tests/unit/test_chinese_tokenizer.py
pytest tests/unit/test_synonym_expander.py
pytest tests/unit/test_chinese_query_preprocessor.py
pytest tests/unit/test_chinese_document_indexer.py
```

## Future Enhancements

- [ ] Support for Traditional Chinese (繁体中文)
- [ ] Named Entity Recognition (NER) for better keyword extraction
- [ ] Context-aware synonym selection
- [ ] Learning-based synonym expansion from user feedback
- [ ] Integration with Chinese language models for semantic similarity
- [ ] Support for Chinese-specific ranking algorithms (e.g., Jieba-based BM25)

## References

- [Jieba Chinese Text Segmentation](https://github.com/fxsjy/jieba)
- [Chinese NLP Best Practices](https://github.com/crownpku/Awesome-Chinese-NLP)
- [Evaluation Metrics for Information Retrieval](https://en.wikipedia.org/wiki/Evaluation_measures_(information_retrieval))
