# Implementation Plan: Advanced RAG Techniques

**Date**: 2026-05-15  
**Estimated Duration**: 2 days  
**Dependencies**: Plan 1 (Performance Comparison Framework)  
**Related Spec**: [Interview Demo Improvements Design](../specs/2026-05-15-interview-demo-improvements-design.md)

## Objective

Implement two advanced RAG techniques - Query Decomposition and Self-RAG - to improve the system's ability to handle complex queries and ensure high-quality retrieval and generation. These techniques demonstrate cutting-edge RAG research and provide measurable accuracy improvements.

## Scope

### In Scope
- Query Decomposition: Break complex queries into simpler sub-queries
- Self-RAG: Self-evaluation of retrieval relevance and answer quality
- Integration with existing workflow (Router and Vector RAG agents)
- Configuration toggles for each technique
- Performance evaluation showing accuracy improvements
- Cost and latency impact analysis

### Out of Scope
- Iterative refinement loops (future enhancement)
- Multi-hop reasoning across documents (covered by Graph RAG)
- Query rewriting or reformulation
- Adaptive retrieval strategies

## Architecture

```
app/services/
├── query_decomposer.py           # Query decomposition service
└── self_rag_evaluator.py         # Self-RAG evaluation service

app/agents/
├── router_agent.py               # Integration point (query decomposition)
└── vector_rag_agent.py           # Integration point (self-RAG)

app/models/
└── advanced_rag_models.py        # Data models

tests/unit/
├── test_query_decomposer.py
└── test_self_rag_evaluator.py
```

## File Details

### 1. `app/services/query_decomposer.py` (~180 lines)
**Purpose**: Decompose complex queries into simpler sub-queries  
**Key Components**:

**QueryDecomposer Class**:
```python
class QueryDecomposer:
    def __init__(self, llm_client):
        self.llm = llm_client
        self.decomposition_prompt = self._load_prompt()
    
    async def decompose(self, query: str) -> DecomposedQuery:
        """
        Decompose complex query into sub-queries.
        Returns original query if decomposition is not beneficial.
        """
        # Detect if query needs decomposition
        if not self._needs_decomposition(query):
            return DecomposedQuery(
                original_query=query,
                sub_queries=[query],
                decomposition_strategy="none"
            )
        
        # Determine decomposition strategy
        strategy = self._detect_strategy(query)
        
        # Decompose using LLM
        sub_queries = await self._decompose_with_llm(query, strategy)
        
        return DecomposedQuery(
            original_query=query,
            sub_queries=sub_queries,
            decomposition_strategy=strategy
        )
    
    def _needs_decomposition(self, query: str) -> bool:
        """Check if query is complex enough to benefit from decomposition."""
        indicators = [
            "和" in query and "区别" in query,  # Comparison
            "以及" in query or "还有" in query,  # Multiple aspects
            len(query) > 50,  # Long query
            query.count("?") > 1 or query.count("？") > 1,  # Multiple questions
        ]
        return any(indicators)
    
    def _detect_strategy(self, query: str) -> str:
        """Detect decomposition strategy based on query type."""
        if any(word in query for word in ["区别", "对比", "比较", "difference", "compare"]):
            return "comparison"
        elif any(word in query for word in ["步骤", "如何", "怎么", "how to", "steps"]):
            return "sequential"
        elif any(word in query for word in ["和", "以及", "还有", "and", "also"]):
            return "parallel"
        else:
            return "general"
    
    async def _decompose_with_llm(
        self, query: str, strategy: str
    ) -> List[str]:
        """Use LLM to decompose query into sub-queries."""
        prompt = self.decomposition_prompt.format(
            query=query,
            strategy=strategy
        )
        
        response = await self.llm.generate(
            prompt=prompt,
            max_tokens=200,
            temperature=0.3
        )
        
        # Parse sub-queries from response
        sub_queries = self._parse_sub_queries(response)
        
        # Limit to max 4 sub-queries
        return sub_queries[:4]
    
    def _parse_sub_queries(self, response: str) -> List[str]:
        """Parse sub-queries from LLM response."""
        lines = response.strip().split("\n")
        sub_queries = []
        for line in lines:
            # Remove numbering and clean up
            line = re.sub(r"^\d+[\.\)]\s*", "", line).strip()
            if line and len(line) > 5:
                sub_queries.append(line)
        return sub_queries
```

**Decomposition Strategies**:
- **Comparison**: "FastAPI和Flask的区别" → ["FastAPI的特点", "Flask的特点", "FastAPI和Flask的性能对比"]
- **Sequential**: "如何部署FastAPI应用" → ["FastAPI应用打包", "服务器配置", "部署步骤", "监控设置"]
- **Parallel**: "年假和病假政策" → ["年假政策", "病假政策"]
- **General**: Break down by aspects or topics

### 2. `app/services/self_rag_evaluator.py` (~200 lines)
**Purpose**: Evaluate retrieval relevance and answer quality  
**Key Components**:

**SelfRAGEvaluator Class**:
```python
class SelfRAGEvaluator:
    def __init__(self, llm_client):
        self.llm = llm_client
        self.relevance_prompt = self._load_relevance_prompt()
        self.quality_prompt = self._load_quality_prompt()
        self.relevance_threshold = float(os.getenv("SELF_RAG_RELEVANCE_THRESHOLD", "0.6"))
    
    async def evaluate_retrieval_relevance(
        self, query: str, documents: List[Document]
    ) -> List[RelevanceScore]:
        """
        Evaluate relevance of each retrieved document to the query.
        Returns relevance scores (0-1) for each document.
        """
        relevance_scores = []
        
        for doc in documents:
            prompt = self.relevance_prompt.format(
                query=query,
                document=doc.content[:500]  # Use first 500 chars
            )
            
            response = await self.llm.generate(
                prompt=prompt,
                max_tokens=50,
                temperature=0.1
            )
            
            score = self._parse_relevance_score(response)
            relevance_scores.append(
                RelevanceScore(
                    document_id=doc.id,
                    score=score,
                    reasoning=response
                )
            )
        
        return relevance_scores
    
    def filter_relevant_documents(
        self,
        documents: List[Document],
        relevance_scores: List[RelevanceScore]
    ) -> List[Document]:
        """Filter documents based on relevance threshold."""
        relevant_docs = []
        for doc, score in zip(documents, relevance_scores):
            if score.score >= self.relevance_threshold:
                relevant_docs.append(doc)
        return relevant_docs
    
    async def evaluate_answer_quality(
        self, query: str, answer: str, documents: List[Document]
    ) -> AnswerQuality:
        """
        Evaluate quality of generated answer.
        Returns quality score and feedback.
        """
        prompt = self.quality_prompt.format(
            query=query,
            answer=answer,
            documents=self._format_documents(documents)
        )
        
        response = await self.llm.generate(
            prompt=prompt,
            max_tokens=150,
            temperature=0.1
        )
        
        quality = self._parse_quality_evaluation(response)
        
        return AnswerQuality(
            score=quality["score"],
            completeness=quality["completeness"],
            accuracy=quality["accuracy"],
            relevance=quality["relevance"],
            feedback=response,
            needs_refinement=quality["score"] < 0.7
        )
    
    def _parse_relevance_score(self, response: str) -> float:
        """Parse relevance score from LLM response."""
        # Look for score in format "Score: 0.8" or "8/10"
        match = re.search(r"(\d+\.?\d*)\s*/\s*10", response)
        if match:
            return float(match.group(1)) / 10
        
        match = re.search(r"Score:\s*(\d+\.?\d*)", response, re.IGNORECASE)
        if match:
            return float(match.group(1))
        
        # Default to medium relevance if can't parse
        return 0.5
    
    def _parse_quality_evaluation(self, response: str) -> Dict[str, float]:
        """Parse quality evaluation from LLM response."""
        # Extract scores for different aspects
        quality = {
            "score": 0.5,
            "completeness": 0.5,
            "accuracy": 0.5,
            "relevance": 0.5
        }
        
        for aspect in quality.keys():
            pattern = rf"{aspect}:\s*(\d+\.?\d*)"
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                quality[aspect] = float(match.group(1))
        
        return quality
```

**Evaluation Criteria**:
- **Retrieval Relevance**: Does the document contain information relevant to the query?
- **Answer Completeness**: Does the answer address all aspects of the query?
- **Answer Accuracy**: Is the answer factually correct based on the documents?
- **Answer Relevance**: Is the answer directly relevant to the query?

### 3. `app/models/advanced_rag_models.py` (~100 lines)
**Purpose**: Pydantic models for advanced RAG  
**Models**:
```python
class DecomposedQuery(BaseModel):
    original_query: str
    sub_queries: List[str]
    decomposition_strategy: str  # "comparison", "sequential", "parallel", "general", "none"

class RelevanceScore(BaseModel):
    document_id: str
    score: float  # 0-1
    reasoning: str

class AnswerQuality(BaseModel):
    score: float  # 0-1
    completeness: float
    accuracy: float
    relevance: float
    feedback: str
    needs_refinement: bool

class SubQueryResult(BaseModel):
    sub_query: str
    documents: List[Document]
    answer: str
    relevance_scores: List[RelevanceScore]

class AdvancedRAGResult(BaseModel):
    query: str
    decomposed_query: Optional[DecomposedQuery]
    sub_query_results: List[SubQueryResult]
    final_answer: str
    answer_quality: AnswerQuality
    metadata: Dict[str, Any]
```

### 4. Integration in `app/agents/router_agent.py`
**Changes**: Add query decomposition before routing
```python
class RouterAgent:
    def __init__(self, ..., enable_query_decomposition: bool = False):
        self.enable_query_decomposition = enable_query_decomposition
        if enable_query_decomposition:
            self.query_decomposer = QueryDecomposer(llm_client)
    
    async def route(self, query: str, context: Dict) -> RoutingDecision:
        # Decompose query if enabled
        if self.enable_query_decomposition:
            decomposed = await self.query_decomposer.decompose(query)
            context["decomposed_query"] = decomposed
            
            # If decomposed, route each sub-query
            if len(decomposed.sub_queries) > 1:
                return RoutingDecision(
                    strategy="decomposed",
                    sub_queries=decomposed.sub_queries,
                    agents=["VectorRAG"] * len(decomposed.sub_queries)
                )
        
        # Normal routing logic
        ...
```

### 5. Integration in `app/agents/vector_rag_agent.py`
**Changes**: Add self-RAG evaluation
```python
class VectorRAGAgent:
    def __init__(self, ..., enable_self_rag: bool = False):
        self.enable_self_rag = enable_self_rag
        if enable_self_rag:
            self.self_rag_evaluator = SelfRAGEvaluator(llm_client)
    
    async def retrieve_and_generate(
        self, query: str, context: Dict
    ) -> RAGResult:
        # Retrieve documents
        documents = await self.retriever.retrieve(query, top_k=10)
        
        # Evaluate retrieval relevance if Self-RAG is enabled
        if self.enable_self_rag:
            relevance_scores = await self.self_rag_evaluator.evaluate_retrieval_relevance(
                query, documents
            )
            documents = self.self_rag_evaluator.filter_relevant_documents(
                documents, relevance_scores
            )
            context["relevance_scores"] = relevance_scores
        
        # Generate answer
        answer = await self.generator.generate(query, documents)
        
        # Evaluate answer quality if Self-RAG is enabled
        if self.enable_self_rag:
            answer_quality = await self.self_rag_evaluator.evaluate_answer_quality(
                query, answer, documents
            )
            context["answer_quality"] = answer_quality
            
            # Refine if quality is low
            if answer_quality.needs_refinement:
                # Retrieve more documents or refine answer
                additional_docs = await self.retriever.retrieve(query, top_k=5)
                documents.extend(additional_docs)
                answer = await self.generator.generate(query, documents)
        
        return RAGResult(
            query=query,
            documents=documents,
            answer=answer,
            metadata=context
        )
```

## Implementation Tasks

### Task 1: Implement Query Decomposer Service
**Duration**: 3 hours  
**Steps**:
1. Create `app/services/query_decomposer.py`
2. Implement `QueryDecomposer` class with methods:
   - `decompose(query)`: Main decomposition method
   - `_needs_decomposition(query)`: Complexity detection
   - `_detect_strategy(query)`: Strategy detection
   - `_decompose_with_llm(query, strategy)`: LLM-based decomposition
   - `_parse_sub_queries(response)`: Parse LLM response
3. Create decomposition prompt template:
   ```
   You are a query decomposition expert. Break down the following complex query into simpler sub-queries.
   
   Query: {query}
   Strategy: {strategy}
   
   Rules:
   - For comparison queries, create separate queries for each item and a comparison query
   - For sequential queries, break down into logical steps
   - For parallel queries, separate into independent aspects
   - Limit to maximum 4 sub-queries
   - Each sub-query should be self-contained and answerable independently
   
   Output format:
   1. [sub-query 1]
   2. [sub-query 2]
   ...
   ```
4. Add configuration to `.env`:
   ```
   ENABLE_QUERY_DECOMPOSITION=true
   QUERY_DECOMPOSITION_MAX_SUBQUERIES=4
   ```
5. Write unit tests:
   - Test complexity detection
   - Test strategy detection
   - Test decomposition for each strategy
   - Test with mock LLM
6. Test with sample queries

**Verification**:
- [ ] Can detect complex queries
- [ ] Correctly identifies decomposition strategy
- [ ] Decomposes queries appropriately
- [ ] Limits sub-queries to max 4
- [ ] Unit tests pass

### Task 2: Implement Self-RAG Evaluator Service
**Duration**: 4 hours  
**Steps**:
1. Create `app/services/self_rag_evaluator.py`
2. Implement `SelfRAGEvaluator` class with methods:
   - `evaluate_retrieval_relevance(query, documents)`: Evaluate document relevance
   - `filter_relevant_documents(documents, scores)`: Filter by threshold
   - `evaluate_answer_quality(query, answer, documents)`: Evaluate answer
   - `_parse_relevance_score(response)`: Parse relevance score
   - `_parse_quality_evaluation(response)`: Parse quality scores
3. Create relevance evaluation prompt:
   ```
   Evaluate the relevance of the following document to the query.
   
   Query: {query}
   Document: {document}
   
   Rate the relevance on a scale of 0-10, where:
   - 0-3: Not relevant (document doesn't address the query)
   - 4-6: Partially relevant (document has some related information)
   - 7-10: Highly relevant (document directly answers the query)
   
   Output format:
   Score: [0-10]
   Reasoning: [brief explanation]
   ```
4. Create quality evaluation prompt:
   ```
   Evaluate the quality of the following answer to the query.
   
   Query: {query}
   Answer: {answer}
   Source Documents: {documents}
   
   Rate the answer on these aspects (0-1 scale):
   - Completeness: Does it address all aspects of the query?
   - Accuracy: Is it factually correct based on the documents?
   - Relevance: Is it directly relevant to the query?
   
   Output format:
   Completeness: [0-1]
   Accuracy: [0-1]
   Relevance: [0-1]
   Overall Score: [0-1]
   Feedback: [brief explanation]
   ```
5. Add configuration to `.env`:
   ```
   ENABLE_SELF_RAG=true
   SELF_RAG_RELEVANCE_THRESHOLD=0.6
   SELF_RAG_QUALITY_THRESHOLD=0.7
   ```
6. Write unit tests:
   - Test relevance evaluation
   - Test document filtering
   - Test quality evaluation
   - Test score parsing
   - Test with mock LLM
7. Test with sample queries and documents

**Verification**:
- [ ] Can evaluate document relevance
- [ ] Filters documents correctly
- [ ] Can evaluate answer quality
- [ ] Score parsing is robust
- [ ] Unit tests pass

### Task 3: Create Data Models
**Duration**: 1 hour  
**Steps**:
1. Create `app/models/advanced_rag_models.py`
2. Define Pydantic models:
   - `DecomposedQuery`
   - `RelevanceScore`
   - `AnswerQuality`
   - `SubQueryResult`
   - `AdvancedRAGResult`
3. Add validation rules:
   - Scores must be between 0 and 1
   - Sub-queries list must not be empty
   - Strategy must be valid enum value
4. Add example data for documentation
5. Write unit tests for model validation

**Verification**:
- [ ] All models defined correctly
- [ ] Validation rules work
- [ ] Can serialize/deserialize to JSON
- [ ] Unit tests pass

### Task 4: Integrate Query Decomposition into Router Agent
**Duration**: 3 hours  
**Steps**:
1. Read `app/agents/router_agent.py` to understand current implementation
2. Add `enable_query_decomposition` parameter to constructor
3. Initialize `QueryDecomposer` if enabled
4. Modify `route()` method:
   - Call decomposer before routing
   - If decomposed, create routing decision for sub-queries
   - Store decomposed query in context
5. Add logic to handle sub-query results:
   - Collect results from all sub-queries
   - Synthesize final answer from sub-query results
6. Update routing decision model to support decomposed queries
7. Write integration tests:
   - Test with decomposition enabled
   - Test with decomposition disabled
   - Test with queries that don't need decomposition
8. Test with sample complex queries

**Verification**:
- [ ] Query decomposition integrates smoothly
- [ ] Sub-queries are routed correctly
- [ ] Results are synthesized properly
- [ ] Configuration toggle works
- [ ] Integration tests pass

### Task 5: Integrate Self-RAG into Vector RAG Agent
**Duration**: 3 hours  
**Steps**:
1. Read `app/agents/vector_rag_agent.py` to understand current implementation
2. Add `enable_self_rag` parameter to constructor
3. Initialize `SelfRAGEvaluator` if enabled
4. Modify `retrieve_and_generate()` method:
   - Evaluate retrieval relevance after retrieval
   - Filter documents based on relevance threshold
   - Evaluate answer quality after generation
   - Refine answer if quality is low (optional)
5. Add metadata tracking:
   - Store relevance scores
   - Store answer quality metrics
   - Track refinement iterations
6. Write integration tests:
   - Test with Self-RAG enabled
   - Test with Self-RAG disabled
   - Test refinement logic
7. Test with sample queries

**Verification**:
- [ ] Self-RAG integrates smoothly
- [ ] Document filtering works correctly
- [ ] Answer quality evaluation works
- [ ] Refinement logic works (if implemented)
- [ ] Configuration toggle works
- [ ] Integration tests pass

### Task 6: Create Prompt Templates
**Duration**: 2 hours  
**Steps**:
1. Create `app/prompts/query_decomposition.txt`:
   - Main decomposition prompt
   - Strategy-specific variations
2. Create `app/prompts/relevance_evaluation.txt`:
   - Relevance scoring prompt
   - Examples of different relevance levels
3. Create `app/prompts/quality_evaluation.txt`:
   - Quality scoring prompt
   - Criteria for each aspect
4. Add prompt loading utility:
   ```python
   def load_prompt(prompt_name: str) -> str:
       path = f"app/prompts/{prompt_name}.txt"
       with open(path, 'r', encoding='utf-8') as f:
           return f.read()
   ```
5. Test prompts with LLM:
   - Verify output format is parseable
   - Adjust prompts if needed
6. Document prompt design decisions

**Verification**:
- [ ] All prompt templates created
- [ ] Prompts produce parseable output
- [ ] Prompt loading utility works
- [ ] Documentation is complete

### Task 7: Implement End-to-End Workflow
**Duration**: 3 hours  
**Steps**:
1. Create workflow integration in `app/workflow/advanced_rag_workflow.py`:
   ```python
   async def process_query_with_advanced_rag(
       query: str,
       enable_decomposition: bool = True,
       enable_self_rag: bool = True
   ) -> AdvancedRAGResult:
       # Step 1: Query decomposition
       if enable_decomposition:
           decomposed = await query_decomposer.decompose(query)
           queries = decomposed.sub_queries
       else:
           queries = [query]
       
       # Step 2: Process each query with Self-RAG
       sub_results = []
       for sub_query in queries:
           # Retrieve with Self-RAG evaluation
           result = await vector_rag_agent.retrieve_and_generate(
               sub_query, enable_self_rag=enable_self_rag
           )
           sub_results.append(result)
       
       # Step 3: Synthesize final answer
       final_answer = await synthesis_agent.synthesize(
           query, sub_results
       )
       
       # Step 4: Evaluate final answer quality
       if enable_self_rag:
           all_docs = [doc for result in sub_results for doc in result.documents]
           answer_quality = await self_rag_evaluator.evaluate_answer_quality(
               query, final_answer, all_docs
           )
       
       return AdvancedRAGResult(
           query=query,
           decomposed_query=decomposed if enable_decomposition else None,
           sub_query_results=sub_results,
           final_answer=final_answer,
           answer_quality=answer_quality if enable_self_rag else None,
           metadata={
               "decomposition_enabled": enable_decomposition,
               "self_rag_enabled": enable_self_rag
           }
       )
   ```
2. Add API endpoint in `app/api/routes/advanced_rag.py`:
   - `POST /api/advanced-rag/query`: Process query with advanced RAG
   - Request body: `{query, enable_decomposition, enable_self_rag}`
   - Response: `AdvancedRAGResult`
3. Write integration tests for end-to-end workflow
4. Test with sample queries

**Verification**:
- [ ] End-to-end workflow works correctly
- [ ] API endpoint is functional
- [ ] Can toggle features independently
- [ ] Integration tests pass

### Task 8: Performance and Cost Analysis
**Duration**: 2 hours  
**Steps**:
1. Instrument code to track:
   - Latency for each component (decomposition, relevance eval, quality eval)
   - Token usage for each LLM call
   - Number of retrieval calls
2. Run test queries with different configurations:
   - Baseline (no advanced RAG)
   - Query decomposition only
   - Self-RAG only
   - Both enabled
3. Calculate metrics:
   - Average latency increase
   - Average token usage increase
   - Cost per query
4. Analyze trade-offs:
   - Accuracy improvement vs latency increase
   - Accuracy improvement vs cost increase
5. Document findings in `docs/advanced_rag_performance.md`
6. Create summary table:
   ```
   | Configuration | Latency | Cost | Accuracy |
   |---------------|---------|------|----------|
   | Baseline      | 850ms   | $0.15| 0.69     |
   | +Decomp       | 1350ms  | $0.20| 0.80     |
   | +SelfRAG      | 1150ms  | $0.18| 0.75     |
   | Both          | 1650ms  | $0.25| 0.85     |
   ```

**Verification**:
- [ ] Performance metrics collected
- [ ] Cost analysis complete
- [ ] Trade-offs documented
- [ ] Summary table created

### Task 9: Evaluate Accuracy Improvements
**Duration**: 3 hours  
**Steps**:
1. Use evaluation framework from Plan 1
2. Create test set for complex queries (10 queries):
   - Comparison queries (3)
   - Multi-aspect queries (3)
   - Sequential queries (2)
   - Long queries (2)
3. Run evaluation with different configurations:
   - Baseline (no advanced RAG)
   - Query decomposition only
   - Self-RAG only
   - Both enabled
4. Calculate metrics:
   - Precision, Recall, F1 for each configuration
   - Improvement percentage
5. Analyze which query types benefit most:
   - Decomposition helps: comparison, multi-aspect
   - Self-RAG helps: all query types (quality improvement)
6. Save results to `data/evaluation/results/advanced_rag_comparison.json`
7. Create visualization of improvements
8. Document findings

**Verification**:
- [ ] Evaluation completed for all configurations
- [ ] Results show expected improvements (target: +15-20% accuracy)
- [ ] Analysis identifies which techniques help which queries
- [ ] Results saved and documented
- [ ] Visualization created

### Task 10: Integration with Demo Page
**Duration**: 2 hours  
**Steps**:
1. Add configuration toggles to demo page:
   - Checkbox for "Enable Query Decomposition"
   - Checkbox for "Enable Self-RAG"
2. Display advanced RAG metadata in results:
   - Show decomposed sub-queries (if applicable)
   - Show relevance scores for documents
   - Show answer quality metrics
3. Add visual indicators:
   - Badge for "Complex Query Detected"
   - Badge for "High Quality Answer" (score > 0.8)
   - Warning for "Low Quality Answer" (score < 0.6)
4. Update API calls to include configuration
5. Test with sample queries
6. Update demo page documentation

**Verification**:
- [ ] Configuration toggles work
- [ ] Advanced RAG metadata displays correctly
- [ ] Visual indicators show appropriately
- [ ] API integration works
- [ ] Documentation updated

## Testing Strategy

### Unit Tests
- Test query decomposer with different query types
- Test self-RAG evaluator with different documents and answers
- Test data model validation
- Mock LLM calls for faster tests

### Integration Tests
- Test integration with router agent
- Test integration with vector RAG agent
- Test end-to-end workflow
- Test with real LLM calls (slower, run separately)

### Evaluation Tests
- Compare accuracy with/without advanced RAG
- Measure latency and cost impact
- Test with diverse query types
- Verify improvements meet targets

### Manual Tests
- Test with real complex queries
- Verify decomposition makes sense
- Verify relevance scores are accurate
- Verify quality evaluations are reasonable

## Acceptance Criteria

- [ ] Query decomposer implemented and tested
- [ ] Self-RAG evaluator implemented and tested
- [ ] Data models defined and validated
- [ ] Integration with router agent complete
- [ ] Integration with vector RAG agent complete
- [ ] End-to-end workflow functional
- [ ] API endpoints implemented
- [ ] Configuration toggles work (ENABLE_QUERY_DECOMPOSITION, ENABLE_SELF_RAG)
- [ ] Performance and cost analysis complete
- [ ] Evaluation shows +15-20% accuracy improvement
- [ ] Latency increase is acceptable (+500-800ms)
- [ ] All unit and integration tests pass
- [ ] Code follows project style (type hints, docstrings, error handling)
- [ ] Documentation updated (README, API docs, performance docs)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Query decomposition creates irrelevant sub-queries | High | Improve decomposition prompt, add validation step |
| Self-RAG evaluation is inaccurate | High | Use clear evaluation criteria, test with ground truth |
| Latency increase is too high | Medium | Make evaluation optional, optimize prompts, use caching |
| Cost increase is too high | Medium | Limit number of evaluations, use smaller model for evaluation |
| Decomposition doesn't improve accuracy | Medium | Only decompose when beneficial, add complexity detection |

## Dependencies

- Plan 1 (Performance Comparison Framework) for evaluation
- Existing router agent and vector RAG agent
- LLM client for decomposition and evaluation
- Synthesis agent for combining sub-query results

## Next Steps

After completing this plan:
1. Combine all improvements (Plans 1-4) for final evaluation
2. Create performance dashboard showing all metrics
3. Prepare demo video showcasing all features
4. Document lessons learned and future improvements
5. Consider additional enhancements:
   - Iterative refinement loops
   - Adaptive retrieval strategies
   - Query rewriting
   - Multi-hop reasoning improvements
