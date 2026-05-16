# Implementation Plan: Chinese NLP Optimization

**Date**: 2026-05-15  
**Estimated Duration**: 1 day  
**Dependencies**: Plan 1 (Performance Comparison Framework)  
**Related Spec**: [Interview Demo Improvements Design](../specs/2026-05-15-interview-demo-improvements-design.md)

## Objective

Enhance the RAG system's Chinese language processing capabilities to improve retrieval quality for Chinese queries. This addresses a critical gap in the current system and demonstrates domain expertise for the Chinese market.

## Scope

### In Scope
- Chinese word segmentation using jieba with custom domain dictionary
- Chinese entity recognition for technical terms
- Synonym expansion for common Chinese terms
- Semantic similarity matching for Chinese queries
- Integration with existing hybrid retriever
- Configuration toggle for Chinese NLP features
- Evaluation of Chinese query performance improvement

### Out of Scope
- Traditional Chinese support (focus on Simplified Chinese)
- Chinese text generation or summarization
- Chinese-specific embedding models (use existing multilingual model)
- Chinese speech recognition or TTS

## Architecture

```
app/services/
└── chinese_nlp_service.py        # Chinese NLP service

app/ingestion/utils/
└── chinese_text_processor.py     # Chinese text preprocessing

data/chinese_nlp/
├── domain_dict.txt               # Domain-specific terms
├── synonyms.json                 # Synonym mappings
└── stopwords.txt                 # Chinese stopwords

app/retrieval/
└── hybrid_retriever.py           # Integration point (add Chinese optimization)

tests/unit/
└── test_chinese_nlp_service.py   # Unit tests
```

## File Details

### 1. `app/services/chinese_nlp_service.py` (~280 lines)
**Purpose**: Core Chinese NLP processing service  
**Key Components**:

**Module 1: ChineseTokenizer** (~70 lines)
- Jieba-based word segmentation
- Custom domain dictionary loading
- Stopword filtering
- Methods:
  - `tokenize(text: str) -> List[str]`: Segment text into words
  - `load_domain_dict(dict_path: str)`: Load custom dictionary
  - `filter_stopwords(tokens: List[str]) -> List[str]`: Remove stopwords

**Module 2: ChineseEntityRecognizer** (~70 lines)
- Technical term extraction
- Named entity recognition for domain-specific entities
- Methods:
  - `extract_entities(text: str) -> List[Entity]`: Extract entities
  - `extract_technical_terms(text: str) -> List[str]`: Extract tech terms
  - `is_technical_term(word: str) -> bool`: Check if word is technical term

**Module 3: ChineseSynonymExpander** (~70 lines)
- Synonym dictionary management
- Query expansion with synonyms
- Methods:
  - `load_synonyms(synonyms_path: str)`: Load synonym mappings
  - `expand_query(query: str) -> List[str]`: Expand query with synonyms
  - `get_synonyms(word: str) -> List[str]`: Get synonyms for a word

**Module 4: ChineseSemanticMatcher** (~70 lines)
- Semantic similarity calculation for Chinese text
- Character-level and word-level matching
- Methods:
  - `calculate_similarity(text1: str, text2: str) -> float`: Calculate similarity
  - `match_keywords(query: str, document: str) -> float`: Keyword matching score
  - `fuzzy_match(query: str, document: str) -> float`: Fuzzy matching score

### 2. `app/ingestion/utils/chinese_text_processor.py` (~150 lines)
**Purpose**: Chinese text preprocessing for ingestion  
**Key Components**:
- `ChineseTextProcessor` class
- Methods:
  - `preprocess(text: str) -> str`: Clean and normalize Chinese text
  - `normalize_punctuation(text: str) -> str`: Normalize Chinese punctuation
  - `remove_special_chars(text: str) -> str`: Remove special characters
  - `segment_sentences(text: str) -> List[str]`: Segment into sentences
- Integration with existing text splitter

### 3. `data/chinese_nlp/domain_dict.txt`
**Purpose**: Domain-specific Chinese terms for jieba  
**Format**: One term per line, optional frequency and POS tag
**Content Examples**:
```
FastAPI 100 n
LangGraph 100 n
向量数据库 50 n
知识图谱 50 n
大语言模型 50 n
检索增强生成 50 n
混合检索 30 n
重排序 30 n
语义相似度 30 n
```
**Size**: ~200 terms

### 4. `data/chinese_nlp/synonyms.json`
**Purpose**: Synonym mappings for query expansion  
**Format**: JSON with word -> synonyms mapping
**Content Examples**:
```json
{
  "年假": ["年度假期", "带薪休假", "年休假"],
  "病假": ["病假期", "医疗假"],
  "加班": ["超时工作", "加班工作"],
  "报销": ["费用报销", "开支报销"],
  "VPN": ["虚拟专用网络", "远程访问"],
  "FastAPI": ["Fast API", "FastAPI框架"],
  "向量检索": ["向量搜索", "语义检索", "向量相似度搜索"],
  "知识图谱": ["知识网络", "知识库图谱"]
}
```
**Size**: ~100 synonym groups

### 5. `data/chinese_nlp/stopwords.txt`
**Purpose**: Chinese stopwords for filtering  
**Format**: One stopword per line
**Content**: Common Chinese stopwords (的, 了, 在, 是, 我, 有, etc.)
**Size**: ~300 stopwords

### 6. Integration in `app/retrieval/hybrid_retriever.py`
**Changes**: Add Chinese optimization option
```python
class HybridRetriever:
    def __init__(
        self,
        vector_store,
        bm25_index,
        enable_chinese_nlp: bool = False
    ):
        self.enable_chinese_nlp = enable_chinese_nlp
        if enable_chinese_nlp:
            self.chinese_nlp = ChineseNLPService()
    
    async def retrieve(self, query: str, top_k: int = 5):
        # Detect if query is Chinese
        if self.enable_chinese_nlp and self._is_chinese(query):
            # Apply Chinese NLP optimizations
            query = self._optimize_chinese_query(query)
        
        # Continue with normal retrieval
        ...
    
    def _optimize_chinese_query(self, query: str) -> str:
        # Tokenize
        tokens = self.chinese_nlp.tokenizer.tokenize(query)
        
        # Expand with synonyms
        expanded = self.chinese_nlp.synonym_expander.expand_query(query)
        
        # Combine original and expanded
        return " ".join([query] + expanded)
```

## Implementation Tasks

### Task 1: Setup Chinese NLP Dependencies
**Duration**: 30 minutes  
**Steps**:
1. Add dependencies to `requirements.txt`:
   - `jieba==0.42.1` (Chinese word segmentation)
   - `pypinyin==0.49.0` (optional, for pinyin conversion)
2. Run `pip install -r requirements.txt`
3. Test jieba installation:
   ```python
   import jieba
   result = jieba.lcut("我想了解年假政策")
   print(result)  # Should output: ['我', '想', '了解', '年假', '政策']
   ```
4. Create directory structure: `data/chinese_nlp/`

**Verification**:
- [ ] Dependencies installed successfully
- [ ] Jieba works correctly
- [ ] Directory structure created

### Task 2: Prepare Chinese NLP Data Files
**Duration**: 2 hours  
**Steps**:
1. Create `data/chinese_nlp/domain_dict.txt`:
   - Add technical terms: FastAPI, LangGraph, RAG, 向量数据库, etc.
   - Add enterprise terms: 年假, 病假, 报销, VPN, etc.
   - Format: `term frequency pos_tag`
   - Total: ~200 terms
2. Create `data/chinese_nlp/synonyms.json`:
   - Map common terms to synonyms
   - Focus on HR and technical domains
   - Total: ~100 synonym groups
3. Create `data/chinese_nlp/stopwords.txt`:
   - Use standard Chinese stopword list
   - Add domain-specific stopwords if needed
   - Total: ~300 stopwords
4. Validate JSON format
5. Document data sources in `data/chinese_nlp/README.md`

**Verification**:
- [ ] All data files created
- [ ] Domain dictionary covers key terms
- [ ] Synonym mappings are accurate
- [ ] JSON is valid
- [ ] README documents data sources

### Task 3: Implement ChineseTokenizer
**Duration**: 1.5 hours  
**Steps**:
1. Create `app/services/chinese_nlp_service.py`
2. Implement `ChineseTokenizer` class:
   ```python
   class ChineseTokenizer:
       def __init__(self, domain_dict_path: str, stopwords_path: str):
           self.stopwords = self._load_stopwords(stopwords_path)
           jieba.load_userdict(domain_dict_path)
       
       def tokenize(self, text: str) -> List[str]:
           tokens = jieba.lcut(text)
           return self.filter_stopwords(tokens)
       
       def filter_stopwords(self, tokens: List[str]) -> List[str]:
           return [t for t in tokens if t not in self.stopwords and len(t.strip()) > 0]
       
       def _load_stopwords(self, path: str) -> Set[str]:
           with open(path, 'r', encoding='utf-8') as f:
               return set(line.strip() for line in f)
   ```
3. Add logging for tokenization
4. Write unit tests:
   - Test tokenization with domain terms
   - Test stopword filtering
   - Test empty input handling
5. Test with sample queries

**Verification**:
- [ ] Tokenizer segments Chinese text correctly
- [ ] Domain dictionary is loaded
- [ ] Stopwords are filtered
- [ ] Unit tests pass

### Task 4: Implement ChineseEntityRecognizer
**Duration**: 1.5 hours  
**Steps**:
1. Add `ChineseEntityRecognizer` class to `chinese_nlp_service.py`:
   ```python
   class ChineseEntityRecognizer:
       def __init__(self, domain_dict_path: str):
           self.technical_terms = self._load_technical_terms(domain_dict_path)
       
       def extract_entities(self, text: str) -> List[Entity]:
           tokens = jieba.lcut(text)
           entities = []
           for token in tokens:
               if self.is_technical_term(token):
                   entities.append(Entity(text=token, type="TECHNICAL"))
           return entities
       
       def extract_technical_terms(self, text: str) -> List[str]:
           tokens = jieba.lcut(text)
           return [t for t in tokens if self.is_technical_term(t)]
       
       def is_technical_term(self, word: str) -> bool:
           return word in self.technical_terms
       
       def _load_technical_terms(self, path: str) -> Set[str]:
           terms = set()
           with open(path, 'r', encoding='utf-8') as f:
               for line in f:
                   term = line.strip().split()[0]
                   terms.add(term)
           return terms
   ```
2. Define `Entity` data model (Pydantic)
3. Write unit tests:
   - Test entity extraction
   - Test technical term detection
   - Test with mixed Chinese/English text
4. Test with sample documents

**Verification**:
- [ ] Can extract technical terms
- [ ] Entity recognition works correctly
- [ ] Handles mixed Chinese/English text
- [ ] Unit tests pass

### Task 5: Implement ChineseSynonymExpander
**Duration**: 1.5 hours  
**Steps**:
1. Add `ChineseSynonymExpander` class to `chinese_nlp_service.py`:
   ```python
   class ChineseSynonymExpander:
       def __init__(self, synonyms_path: str):
           self.synonyms = self._load_synonyms(synonyms_path)
       
       def expand_query(self, query: str, max_expansions: int = 2) -> List[str]:
           tokens = jieba.lcut(query)
           expansions = []
           for token in tokens:
               synonyms = self.get_synonyms(token)
               if synonyms:
                   expansions.extend(synonyms[:max_expansions])
           return expansions
       
       def get_synonyms(self, word: str) -> List[str]:
           return self.synonyms.get(word, [])
       
       def _load_synonyms(self, path: str) -> Dict[str, List[str]]:
           with open(path, 'r', encoding='utf-8') as f:
               return json.load(f)
   ```
2. Add configuration for max expansions
3. Write unit tests:
   - Test query expansion
   - Test synonym retrieval
   - Test with words that have no synonyms
4. Test with sample queries

**Verification**:
- [ ] Can expand queries with synonyms
- [ ] Max expansions limit works
- [ ] Handles words without synonyms
- [ ] Unit tests pass

### Task 6: Implement ChineseSemanticMatcher
**Duration**: 2 hours  
**Steps**:
1. Add `ChineseSemanticMatcher` class to `chinese_nlp_service.py`:
   ```python
   class ChineseSemanticMatcher:
       def __init__(self, tokenizer: ChineseTokenizer):
           self.tokenizer = tokenizer
       
       def calculate_similarity(self, text1: str, text2: str) -> float:
           # Combine multiple matching strategies
           keyword_score = self.match_keywords(text1, text2)
           fuzzy_score = self.fuzzy_match(text1, text2)
           return 0.7 * keyword_score + 0.3 * fuzzy_score
       
       def match_keywords(self, query: str, document: str) -> float:
           query_tokens = set(self.tokenizer.tokenize(query))
           doc_tokens = set(self.tokenizer.tokenize(document))
           if not query_tokens:
               return 0.0
           intersection = query_tokens & doc_tokens
           return len(intersection) / len(query_tokens)
       
       def fuzzy_match(self, query: str, document: str) -> float:
           # Character-level matching for partial matches
           query_chars = set(query)
           doc_chars = set(document)
           if not query_chars:
               return 0.0
           intersection = query_chars & doc_chars
           return len(intersection) / len(query_chars)
   ```
2. Add unit tests:
   - Test similarity calculation
   - Test keyword matching
   - Test fuzzy matching
3. Benchmark performance
4. Test with sample query-document pairs

**Verification**:
- [ ] Similarity calculation works correctly
- [ ] Keyword matching is accurate
- [ ] Fuzzy matching handles partial matches
- [ ] Performance is acceptable (<10ms per comparison)
- [ ] Unit tests pass

### Task 7: Implement ChineseNLPService Facade
**Duration**: 1 hour  
**Steps**:
1. Add `ChineseNLPService` facade class:
   ```python
   class ChineseNLPService:
       def __init__(
           self,
           domain_dict_path: str = "data/chinese_nlp/domain_dict.txt",
           synonyms_path: str = "data/chinese_nlp/synonyms.json",
           stopwords_path: str = "data/chinese_nlp/stopwords.txt"
       ):
           self.tokenizer = ChineseTokenizer(domain_dict_path, stopwords_path)
           self.entity_recognizer = ChineseEntityRecognizer(domain_dict_path)
           self.synonym_expander = ChineseSynonymExpander(synonyms_path)
           self.semantic_matcher = ChineseSemanticMatcher(self.tokenizer)
       
       def process_query(self, query: str) -> ProcessedQuery:
           tokens = self.tokenizer.tokenize(query)
           entities = self.entity_recognizer.extract_entities(query)
           expansions = self.synonym_expander.expand_query(query)
           return ProcessedQuery(
               original=query,
               tokens=tokens,
               entities=entities,
               expansions=expansions
           )
   ```
2. Define `ProcessedQuery` data model
3. Add singleton pattern with `get_instance()`
4. Write integration tests
5. Test with sample queries

**Verification**:
- [ ] Facade integrates all modules
- [ ] Can process queries end-to-end
- [ ] Singleton pattern works
- [ ] Integration tests pass

### Task 8: Integrate with Hybrid Retriever
**Duration**: 2 hours  
**Steps**:
1. Read `app/retrieval/hybrid_retriever.py`
2. Add `enable_chinese_nlp` parameter to constructor
3. Add Chinese language detection:
   ```python
   def _is_chinese(self, text: str) -> bool:
       chinese_chars = sum(1 for c in text if '一' <= c <= '鿿')
       return chinese_chars / len(text) > 0.3 if text else False
   ```
4. Add Chinese query optimization:
   ```python
   def _optimize_chinese_query(self, query: str) -> str:
       processed = self.chinese_nlp.process_query(query)
       # Combine original query with expansions
       expanded_terms = " ".join(processed.expansions[:2])
       return f"{query} {expanded_terms}"
   ```
5. Integrate into `retrieve()` method
6. Add configuration to `.env`:
   ```
   ENABLE_CHINESE_NLP=true
   ```
7. Write integration tests
8. Test with Chinese queries

**Verification**:
- [ ] Chinese language detection works
- [ ] Query optimization improves retrieval
- [ ] Configuration toggle works
- [ ] Integration tests pass
- [ ] No impact on English queries

### Task 9: Implement Chinese Text Processor for Ingestion
**Duration**: 1.5 hours  
**Steps**:
1. Create `app/ingestion/utils/chinese_text_processor.py`
2. Implement `ChineseTextProcessor` class:
   ```python
   class ChineseTextProcessor:
       def preprocess(self, text: str) -> str:
           text = self.normalize_punctuation(text)
           text = self.remove_special_chars(text)
           return text.strip()
       
       def normalize_punctuation(self, text: str) -> str:
           # Convert Chinese punctuation to English
           replacements = {
               '，': ',', '。': '.', '！': '!', '？': '?',
               '；': ';', '：': ':', '（': '(', '）': ')',
               '【': '[', '】': ']', '《': '<', '》': '>'
           }
           for cn, en in replacements.items():
               text = text.replace(cn, en)
           return text
       
       def remove_special_chars(self, text: str) -> str:
           # Keep Chinese, English, numbers, and basic punctuation
           return re.sub(r'[^一-鿿\w\s.,!?;:()\[\]<>-]', '', text)
       
       def segment_sentences(self, text: str) -> List[str]:
           # Split on Chinese and English sentence endings
           return re.split(r'[。！？.!?]+', text)
   ```
3. Integrate with existing text splitter
4. Write unit tests
5. Test with Chinese documents

**Verification**:
- [ ] Text preprocessing works correctly
- [ ] Punctuation normalization is accurate
- [ ] Sentence segmentation works
- [ ] Unit tests pass

### Task 10: Evaluate Chinese Query Performance
**Duration**: 2 hours  
**Steps**:
1. Create Chinese query test set (10 queries):
   - HR queries: "年假政策", "如何报销", "VPN怎么用"
   - Technical queries: "FastAPI性能", "向量检索原理", "知识图谱构建"
2. Run evaluation with Chinese NLP disabled:
   - Use evaluation framework from Plan 1
   - Record precision, recall, F1
3. Run evaluation with Chinese NLP enabled:
   - Record same metrics
   - Compare results
4. Analyze improvements:
   - Calculate percentage improvement
   - Identify which queries improved most
   - Document findings
5. Update evaluation results in `data/evaluation/results/chinese_nlp_comparison.json`
6. Create summary report

**Verification**:
- [ ] Chinese query test set created
- [ ] Evaluation completed for both configurations
- [ ] Results show improvement (target: +15-25% recall)
- [ ] Findings documented
- [ ] Summary report created

## Testing Strategy

### Unit Tests
- Test each module independently (tokenizer, entity recognizer, synonym expander, semantic matcher)
- Test data loading and validation
- Test edge cases (empty input, special characters, mixed languages)
- Mock file I/O for faster tests

### Integration Tests
- Test ChineseNLPService facade
- Test integration with hybrid retriever
- Test end-to-end query processing
- Test with real Chinese documents

### Performance Tests
- Benchmark tokenization speed (target: <5ms per query)
- Benchmark similarity calculation (target: <10ms per comparison)
- Test with large documents (>10k characters)

### Evaluation Tests
- Compare retrieval quality with/without Chinese NLP
- Measure recall improvement on Chinese queries
- Verify no degradation on English queries

## Acceptance Criteria

- [ ] Chinese NLP service implemented with 4 modules
- [ ] Domain dictionary, synonym mappings, and stopwords prepared
- [ ] Integration with hybrid retriever complete
- [ ] Configuration toggle works (ENABLE_CHINESE_NLP)
- [ ] Chinese text processor for ingestion implemented
- [ ] All unit and integration tests pass
- [ ] Performance benchmarks meet targets
- [ ] Evaluation shows +15-25% recall improvement on Chinese queries
- [ ] No degradation on English queries
- [ ] Code follows project style (type hints, docstrings, error handling)
- [ ] Documentation updated (README, API docs)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Jieba segmentation errors on domain terms | Medium | Use custom dictionary with domain-specific terms |
| Synonym expansion introduces noise | Medium | Limit max expansions, use relevance threshold |
| Performance overhead on query processing | Low | Benchmark and optimize, cache processed queries |
| Synonym mappings are incomplete | Low | Start with common terms, iterate based on usage |

## Dependencies

- Plan 1 (Performance Comparison Framework) for evaluation
- Jieba library for Chinese word segmentation
- Existing hybrid retriever

## Next Steps

After completing this plan:
1. Proceed to Plan 4: Advanced RAG Techniques
2. Combine Chinese NLP with advanced RAG for maximum improvement
3. Evaluate combined system performance
4. Integrate into demo page with language toggle
