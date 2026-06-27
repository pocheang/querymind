---
name: agent-quality-optimization
description: Quality-first deep refactor of all 11 agents to improve accuracy, reliability, and performance
metadata:
  type: project
---

# Agent Quality Optimization Design

**Date**: 2026-06-27  
**Status**: Approved  
**Priority**: High - Quality improvements across all agents

## Executive Summary

This design addresses quality, reliability, and performance issues across QueryMind's 11-agent system. Using a systematic quality-first approach, we will enhance:

1. **Router Agent** - Improve routing accuracy from ~95% to ~98%
2. **Vector/Graph RAG Agents** - Boost retrieval precision from 0.90 to 0.93+
3. **Quality Agents** - Increase validation accuracy from ~92% to ~96%
4. **Synthesis Agent** - Reduce hallucinations by 70-80%
5. **Workflow Orchestration** - Improve reliability from 99.5% to 99.8%

**Why**: The system currently experiences issues across performance, quality, reliability, and agent coordination. Quality improvement is the top priority as it directly impacts user trust and answer accuracy.

**How**: Deep refactor of each agent with architectural fixes, better prompt engineering, improved algorithms, and robust error handling.

**Timeline**: 3 days total (4 phases)

## Current System Analysis

### Agent Inventory (11 Total)

**Core Routing (1)**:
- 🎯 Router Agent - Intent classification and route selection

**Retrieval Execution (5)**:
- 🔍 Vector RAG Agent - Hybrid retrieval (Vector + BM25 + Reranking)
- 🕸️ Graph RAG Agent - Knowledge graph queries
- 🌍 Web Research Agent - Real-time web search
- 🤖 ReAct Agent - Multi-step reasoning
- ✨ Synthesis Agent - Answer generation

**Quality Assurance (5)** ⭐ v0.5.0:
- 🎯 Route Validator Agent - Routing verification
- 📊 Retrieval Quality Agent - Retrieval assessment
- 🛡️ Answer Validator Agent - NLI hallucination detection
- 💭 Context Tracker Agent - Multi-turn context
- ⚖️ Quality Orchestrator Agent - Score fusion

### Issues Identified

**Performance Issues**:
- Timeouts under load
- Inefficient async coordination
- Cache misses for similar queries

**Quality Issues**:
- Router makes suboptimal routing decisions (~5% error rate)
- Retrieval returns irrelevant results (Precision@5: 0.90)
- Quality validators have false positives/negatives (~8% error rate)
- Synthesis generates hallucinations (~15-40% of answers)

**Reliability Issues**:
- Poor error handling causes cascading failures
- State management bugs in multi-turn conversations
- Memory leaks in context tracking

**Integration Issues**:
- Agent coordination timing problems
- Inconsistent retry logic
- Workflow doesn't gracefully degrade

## Detailed Improvement Design

### 1. Router Agent Quality Enhancement

**Goal**: Improve routing accuracy from ~95% to ~98%

**Current Issues**:
- Simple prompt without few-shot examples
- Confidence scores not calibrated to actual accuracy
- No fallback strategy for low-confidence decisions
- Cache may perpetuate poor routing decisions
- Weak handling of multi-intent or ambiguous queries

**Improvements**:

#### 1.1 Enhanced Prompt Engineering
- Add **few-shot examples** (3-5 per route type) showing correct routing decisions
- Include **negative examples** (common mistakes to avoid)
- Add **reasoning chain** - force LLM to explain decision before choosing route
- Structured output format with explicit confidence justification

**Example prompt addition**:
```
Examples:
Q: "What is machine learning?"
Route: vector (concept definition, best from documents)
Confidence: 0.95

Q: "Who reports to the CTO and what projects are they on?"
Route: graph (relationship query, multi-hop reasoning needed)
Confidence: 0.92

Q: "Compare Python and Java for ML"
Route: hybrid (needs both concept understanding AND comparison)
Confidence: 0.88
```

#### 1.2 Confidence Calibration
- Track **historical accuracy** by confidence bucket (0.6-0.7, 0.7-0.8, etc.)
- Apply **calibration multiplier** based on actual performance
- If raw confidence is 0.9 but historical accuracy at 0.9 is only 0.85, adjust down
- Store calibration data in config for tuning

#### 1.3 Fallback Strategies
- **Low confidence fallback** (< 0.6): Try reasoning model or default to safe route (vector)
- **Ambiguity detection**: If multiple routes score similarly, flag as ambiguous
- **Multi-intent handling**: Detect queries needing multiple routes, return hybrid
- **User clarification**: For very ambiguous queries (< 0.5 confidence), suggest clarifying question

#### 1.4 Cache Intelligence
- Add **cache version** to allow invalidation of old decisions
- Store **decision metadata** (timestamp, model version, confidence)
- Implement **cache warming** with high-quality decisions
- Add **cache bypass** flag for testing new routing logic

**Expected Impact**:
- Routing accuracy: 95% → 98%
- Confidence calibration error: ±0.15 → ±0.05
- Ambiguous query handling: 60% → 90%

---

### 2. Vector & Graph RAG Quality Enhancement

**Goal**: Boost retrieval Precision@5 from 0.90 to 0.93+

#### 2.1 Vector RAG Improvements

**Current Issues**:
- Query understanding misses key entities or intent
- Fixed retrieval parameters don't adapt to query type
- Reranker parameters not optimally tuned
- No fallback when top results have low relevance scores

**Improvements**:

**Query Expansion & Understanding**:
- **Entity extraction**: Use NER to identify key entities before retrieval
- **Synonym expansion**: Add related terms (e.g., "ML" → "machine learning", "深度学习" → "deep learning")
- **Query rewriting**: For follow-up questions, expand with context
- **Intent-based weighting**: Adjust vector vs BM25 weights by query type
  - Concept queries: 80% vector, 20% BM25
  - Keyword queries: 50% vector, 50% BM25
  - Entity queries: 60% vector, 40% BM25

**Retrieval Parameter Tuning**:
- **Dynamic top-k**: Retrieve more candidates (top-30) for complex queries, fewer (top-15) for simple
- **RRF weight optimization**: Test different vector:BM25 ratios per query type
- **Overlap in chunking**: Increase overlap from 50 to 100 tokens to preserve context
- **Chunk size tuning**: Test 300/500/700 token chunks, choose optimal per document type

**Reranker Enhancement**:
- **Model upgrade**: Evaluate BGE-reranker-large vs current model
- **Batch reranking**: Process candidates in batches for efficiency
- **Score normalization**: Normalize reranker scores to [0,1] for better thresholding
- **Threshold filtering**: Drop results with reranker score < 0.5

**Fallback Strategy**:
- If top-5 average score < 0.6, **expand search** (increase top-k, try query variations)
- If still low, **try alternative route** (graph if entities detected, web for time-sensitive)
- Log low-score queries for offline analysis

**Expected Impact**:
- Precision@5: 0.90 → 0.93
- Recall@5: 0.84 → 0.87
- Query understanding: 85% → 92%

#### 2.2 Graph RAG Improvements

**Current Issues**:
- Entity extraction can fail or extract wrong entities
- Entity linking struggles with ambiguous names
- Cypher queries can be malformed
- No fallback when graph returns empty results

**Improvements**:

**Robust Entity Extraction**:
- **Multi-stage extraction**:
  1. Rule-based NER for common patterns
  2. LLM-based extraction for complex cases
  3. Cross-validation between methods
- **Entity validation**: Check extracted entities exist in graph before querying
- **Fuzzy matching**: Use Levenshtein distance ≤ 2 for similar entity names
- **Disambiguation**: When multiple matches, use context to pick correct entity

**Cypher Query Enhancement**:
- **Query templates**: Use proven templates for common query patterns
- **Syntax validation**: Parse and validate Cypher before execution
- **Query optimization**: Add LIMIT clauses, optimize path length
- **Error handling**: Catch Neo4j errors and retry with simpler query

**Relationship Filtering**:
- **Confidence scoring**: Prioritize high-confidence relationships (extracted from multiple sources)
- **Relationship type ranking**: Prefer direct relationships over indirect
- **Path pruning**: Limit multi-hop queries to 3 hops maximum
- **Result ranking**: Rank paths by relevance to original query

**Hybrid Fallback**:
- If graph returns **0 results**: Fall back to vector RAG
- If graph returns **low-confidence results** (< 0.5): Combine with vector RAG
- **Entity mention search**: If entity not in graph, search for entity mentions in documents

**Expected Impact**:
- Entity extraction accuracy: 85% → 92%
- Graph query success rate: 88% → 95%
- Multi-hop reasoning F1: 0.76 → 0.82
- Empty result rate: 15% → 5%

---

### 3. Quality Agents Validation Accuracy

**Goal**: Increase validation accuracy from ~92% to ~96%

#### 3.1 Answer Validator Improvements

**Current Issues**:
- NLI model has false positives (flags correct inferences as hallucinations)
- False negatives (misses subtle hallucinations)
- Doesn't catch common hallucination patterns (wrong dates, numbers)
- Citation checking is incomplete

**Improvements**:

**Multi-Stage NLI Validation**:
- **Sentence-level validation**: Break answer into sentences, validate each
- **Claim extraction**: Identify factual claims vs opinions/hedging
- **Aggregation**: Answer valid if ≥90% of factual claims are entailed
- **Confidence weighting**: Weight high-confidence claims more

**Hallucination Pattern Detection**:
- **Rule-based checks**:
  - Date validation (check if date is in retrieved context)
  - Number validation (verify numerical claims)
  - Entity validation (check if mentioned entities are in context)
  - Negation detection (ensure answer doesn't negate source)
- **Common patterns**:
  - "According to X, Y" where X is not in citations
  - Specific numbers/dates not in source
  - Definitive statements when source is uncertain

**Citation Cross-Checking**:
- **Claim-to-citation mapping**: Every factual claim must have supporting citation
- **Citation accuracy**: Verify citation content actually supports claim
- **Citation completeness**: Flag if major claims lack citations
- **Source diversity**: Prefer claims supported by multiple sources

**False Positive Reduction**:
- **Inference allowance**: Allow reasonable inferences (e.g., "CEO leads company" from "X is CEO")
- **Context awareness**: Don't flag general knowledge or logical implications
- **Threshold tuning**: Adjust NLI thresholds based on empirical false positive rate
- **Confidence bands**: Low-confidence entailment (0.5-0.7) is warning, not failure

**Validation Cascade** (4 levels):
1. **Level 1 - Fast rules** (5ms): Check obvious patterns
2. **Level 2 - NLI batch** (100ms): Sentence-level NLI validation
3. **Level 3 - Citation verify** (50ms): Cross-check citations
4. **Level 4 - LLM deep check** (200ms): Only if levels 1-3 flag issues

**Expected Impact**:
- NLI accuracy: 92% → 96%
- False positive rate: 8% → 3%
- False negative rate: 5% → 2%
- Hallucination detection: 85% → 95%

#### 3.2 Route Validator Improvements

**Current Issues**:
- Confidence thresholds too strict or too loose
- Doesn't learn from historical routing accuracy
- 3-layer validation has redundancy

**Improvements**:

**Historical Accuracy Tracking**:
- Track **actual routing outcomes** (did route produce good results?)
- Build **accuracy model** per route type and query pattern
- Use history to **recalibrate confidence**
- **Feedback loop**: Learn from Route Validator corrections

**3-Layer Validation Refinement**:
- **Layer 1 - Intent check**: Is intent classification clear and confident? (threshold: 0.7)
- **Layer 2 - Entity check**: Are key entities identified correctly? (entity coverage ≥ 80%)
- **Layer 3 - Strategy check**: Is route optimal for this query pattern? (compare to historical best)

**Ambiguity Detection**:
- Flag queries with **conflicting signals** (e.g., entity query but no entities detected)
- Detect **multi-intent queries** needing clarification or hybrid route
- **Confidence penalty** for ambiguous queries (-0.2)

**Dynamic Thresholds**:
- **Adaptive thresholds** by query complexity:
  - Simple queries: require 0.8+ confidence
  - Complex queries: accept 0.6+ confidence (harder to route)
- **Domain-specific thresholds**: Technical queries may need graph, general need vector

**Expected Impact**:
- Route validation accuracy: 90% → 95%
- Ambiguity detection: 60% → 85%
- Unnecessary route retries: 15% → 5%

#### 3.3 Retrieval Quality Improvements

**Current Issues**:
- Metrics (Precision/Recall) don't capture actual relevance
- Coverage analysis is shallow
- Doesn't detect contradictions in retrieved docs

**Improvements**:

**Relevance Scoring**:
- Use **lightweight LLM** (e.g., Haiku) to score query-document relevance
- 3-point scale: Highly Relevant (1.0), Somewhat Relevant (0.5), Not Relevant (0.0)
- Aggregate: Overall quality = avg(relevance scores) for top-5
- **Fast implementation**: Batch process in <100ms

**Coverage Analysis**:
- **Query decomposition**: Break query into key aspects (who, what, when, where, why)
- **Aspect coverage**: Check if retrieved docs cover each aspect
- **Coverage score**: % of query aspects with supporting evidence
- Flag queries with **low coverage** (<50%) for retrieval expansion

**Consistency Checking**:
- **Contradiction detection**: Check if retrieved docs contradict each other
- **Entity consistency**: Same entity should have consistent attributes
- **Fact checking**: Cross-verify numerical facts across documents
- Flag contradictions for **manual review** or **additional retrieval**

**Quality Metrics Enhancement**:
- Add **NDCG@5** (normalized discounted cumulative gain)
- Add **MAP** (mean average precision)
- **Diversity score**: Measure topical diversity of results
- **Freshness score**: For time-sensitive queries, check document dates

**Expected Impact**:
- Relevance assessment accuracy: 80% → 92%
- Coverage detection: 70% → 88%
- Contradiction detection: 40% → 75%

#### 3.4 Quality Orchestrator Improvements

**Current Issues**:
- Fixed weights may not be optimal
- Thresholds don't adapt to query type
- Penalty rules are simplistic

**Improvements**:

**Weight Optimization**:
- **A/B test different weight configurations** on golden dataset
- Current: Route 15%, Retrieval 25%, Factuality 40%, Quality 15%, Citation 5%
- Test: Route 10%, Retrieval 30%, Factuality 45%, Quality 10%, Citation 5%
- Choose weights that **maximize correlation** with human quality judgments

**Dynamic Thresholds**:
- **Query-type thresholds**:
  - Factual queries: require high quality (0.8+)
  - Exploratory queries: accept medium quality (0.6+)
  - Opinion queries: lower threshold (0.5+)
- **Domain thresholds**: Technical domains may need higher quality

**Enhanced Penalty Rules**:
- **Hallucination risk**: 
  - Low (< 0.2): no penalty
  - Medium (0.2-0.5): multiply by 0.9
  - High (0.5+): multiply by 0.7
- **Route confidence**:
  - High (> 0.8): no penalty
  - Medium (0.5-0.8): multiply by 0.95
  - Low (< 0.5): multiply by 0.8
- **Retrieval quality**:
  - If < 0.5: multiply overall by 0.85

**Actionable Recommendations**:
- **High quality (0.8+)**: "Answer is trustworthy"
- **Medium quality (0.6-0.8)**: "Verify with additional sources"
- **Low quality (0.4-0.6)**: "Use with caution, may be incomplete"
- **Very low (< 0.4)**: "Answer unreliable, recommend regeneration or clarification"

**Expected Impact**:
- Quality score correlation with human judgment: 0.75 → 0.88
- Actionable recommendation accuracy: 70% → 90%
- Over-conservative flagging: 20% → 8%

---

### 4. Synthesis Agent Answer Quality

**Goal**: Reduce hallucination rate by 70-80%, improve citation completeness to 95%

**Current Issues**:
- Generates answers not fully grounded in retrieved context
- Citations are incomplete or inaccurate
- Hallucinations slip through validation
- Answer structure inconsistent across query types
- No hedging when uncertainty is high

**Improvements**:

#### 4.1 Structured Generation with Citation Discipline

**Citation-First Approach**:
- **Step 1**: Identify relevant passages from retrieved documents
- **Step 2**: Extract key facts with citation markers
- **Step 3**: Compose answer around cited facts
- **Step 4**: Verify every factual claim has citation

**Prompt Template**:
```
You are a factual answer generator. Follow these rules strictly:

1. ONLY use information from the provided context
2. Every factual claim MUST have a citation [doc_id:page]
3. If uncertain, use hedging language ("may", "possibly", "according to")
4. If information is missing, state "Information not found in provided sources"
5. Do NOT add external knowledge or make assumptions

Context:
{retrieved_documents}

Query: {user_query}

Generate answer with inline citations:
```

#### 4.2 Chain-of-Thought Synthesis

**Reasoning Before Generation**:
- **Analysis phase**: "Let me analyze what the context says about X..."
- **Evidence gathering**: "Document A states..., Document B confirms..."
- **Synthesis phase**: "Based on these sources, I can conclude..."
- **Confidence check**: "I am confident/uncertain about this because..."

**Multi-Pass Generation**:
1. **Draft generation** (fast): Initial answer with citations
2. **Self-validation**: Check if answer is fully grounded
3. **Refinement**: Fix citation gaps or unsupported claims
4. **Final output**: Validated, well-cited answer

#### 4.3 Answer Templates by Query Type

**Concept Definition**:
```
[Concept] is [definition from source]. [Citation]

Key characteristics:
- [Point 1] [Citation]
- [Point 2] [Citation]

[Additional context if available]
```

**Comparison**:
```
[Entity A] and [Entity B] differ in the following ways:

| Aspect | Entity A | Entity B |
|--------|----------|----------|
| [Aspect1] | [Value] [Cit] | [Value] [Cit] |

Key similarities: [List with citations]
```

**Relationship Query**:
```
According to the knowledge graph, [Entity A] is connected to [Entity B] through [relationship type]. [Citation]

Path: [Entity A] → [Relation1] → [Intermediate] → [Relation2] → [Entity B]

Additional context: [Text from documents] [Citation]
```

#### 4.4 Confidence Indicators

**Hedging Language**:
- **High confidence** (multiple sources agree): "The evidence clearly shows..."
- **Medium confidence** (single source or weak evidence): "According to [Source], it appears that..."
- **Low confidence** (conflicting sources): "Sources disagree on this point..."
- **No information**: "I don't have sufficient information to answer this question."

**Explicit Uncertainty**:
- Flag when **context is incomplete**
- Acknowledge **conflicting information**
- State **assumptions** when making inferences

#### 4.5 Fact Verification Layer

**Post-Generation Checks**:
- **Citation verification**: Each [citation] marker maps to actual retrieved document
- **Fact extraction**: Extract all factual claims from generated answer
- **Source matching**: Verify each fact appears in cited source
- **Negation check**: Ensure answer doesn't contradict sources
- **Number/date check**: Verify all specific numbers and dates

**Hallucination Prevention Rules**:
- No specific dates unless in source
- No precise numbers unless in source
- No entity attributes unless explicitly stated
- No causal claims unless supported
- No "always/never" unless source uses them

**Expected Impact**:
- Hallucination rate: 15-40% → 5-8%
- Citation completeness: 85% → 95%
- Answer groundedness: 80% → 94%
- User trust score: 7.5/10 → 8.8/10

---

### 5. Workflow Orchestration & Integration

**Goal**: Improve system reliability from 99.5% to 99.8%, reduce cascading failures

**Current Issues**:
- Poor error handling causes cascading failures
- State management fragile across async operations
- Retry logic not intelligent (retries same operation)
- No graceful degradation when agents fail
- Timeout issues under load

**Improvements**:

#### 5.1 Graceful Degradation Strategy

**Failure Modes & Fallbacks**:
- **Router fails** → Default to vector RAG (safe fallback)
- **Vector RAG fails** → Try graph RAG or web search
- **Graph RAG fails** → Fall back to vector RAG
- **Quality validation fails** → Return answer with warning
- **Synthesis fails** → Return raw retrieved passages
- **All agents fail** → Apologize and suggest rephrasing query

**Quality-Based Degradation**:
- If quality score < 0.4, **attempt regeneration** with expanded retrieval
- If regeneration fails, **return partial results** with strong warning
- Track degradation events for offline analysis

#### 5.2 Error Isolation

**Circuit Breaker Pattern**:
- Track **error rate** per agent (rolling 5-minute window)
- If error rate > 50%, **temporarily disable agent** (5 minutes)
- Route to fallback agent automatically
- Send alert to monitoring system

**Exception Isolation**:
- **Try-catch blocks** around each agent call
- Log exception with full context (query, state, stack trace)
- Return structured error response, not raw exception
- Continue workflow with fallback when possible

#### 5.3 State Synchronization

**Context State Management**:
- Use **immutable state objects** to prevent race conditions
- **Lock mechanism** for conversation context updates
- Validate state consistency before each operation
- Periodic state **health checks** (detect corruption)

**Session State Cleanup**:
- Active cleanup of expired sessions (already implemented in P1-6)
- **Memory monitoring**: Alert if context store > 1GB
- Graceful handling of state not found (session expired)

#### 5.4 Intelligent Retry Logic

**Retry with Variation**:
- **First retry**: Increase retrieval top-k (5 → 10)
- **Second retry**: Try alternative route (vector → hybrid)
- **Third retry**: Use reasoning model instead of chat model
- **Max retries**: 2 per agent to prevent infinite loops

**Exponential Backoff**:
- Wait 100ms before first retry
- Wait 500ms before second retry
- Track retry counts in execution metadata

#### 5.5 Timeout Management

**Agent-Specific Timeouts**:
- Router: 2s (fast decision needed)
- Vector RAG: 5s (retrieval + reranking)
- Graph RAG: 8s (entity extraction + Cypher query)
- Quality validation: 2s (parallel execution)
- Synthesis: 5s (LLM generation)
- **Total workflow timeout**: 10s (configurable, already implemented in P1-11)

**Progressive Timeout Handling**:
- 50% of timeout: Log warning
- 80% of timeout: Attempt quick completion
- 100% of timeout: Cancel operation, return cached/fallback result

#### 5.6 Execution Tracing

**Structured Logging**:
- Log **entry/exit** of each agent with timing
- Log **key decisions** (route chosen, quality score, etc.)
- Log **errors** with full context
- Use **correlation ID** to trace request across agents

**Performance Metrics**:
- Track **p50, p95, p99 latencies** per agent
- Monitor **error rates** and **retry rates**
- Track **cache hit rates**
- Dashboard for real-time monitoring

**Quality Gates**:
- **Hard stop** if quality score < 0.3 (don't return answer)
- **Warning** if quality score 0.3-0.5 (return with strong warning)
- **Acceptable** if quality score 0.5-0.7 (return with suggestion to verify)
- **Good** if quality score > 0.7 (return confidently)

**Expected Impact**:
- System availability: 99.5% → 99.8%
- Cascading failure rate: 5% → 1%
- Mean time to recovery: 2min → 30s
- Graceful degradation success: 60% → 90%

---

## Testing & Validation Strategy

### Golden Dataset Creation

**Dataset Composition** (100 queries total):
- **Concept queries** (25): "What is X?", "Explain Y", "Define Z"
- **Relationship queries** (20): "Who reports to X?", "What is the relationship between A and B?"
- **Comparison queries** (15): "Compare X and Y", "Difference between A and B"
- **Multi-hop reasoning** (15): "If X, then what happens to Y?", "Trace the path from A to B"
- **Ambiguous queries** (10): Unclear intent, multiple interpretations
- **Follow-up queries** (10): Multi-turn conversation requiring context
- **Edge cases** (5): Empty result, contradictory info, time-sensitive

**Expected Outcomes**:
- **Correct route**: Which route should be chosen
- **Expected retrieval**: Which documents should be retrieved
- **Expected answer**: Gold standard answer
- **Required citations**: Which sources should be cited
- **Quality threshold**: Minimum acceptable quality score

### Evaluation Metrics

**Router Metrics**:
- **Routing accuracy**: % of queries routed correctly
- **Confidence calibration**: Correlation between confidence and actual accuracy
- **Ambiguity detection**: % of ambiguous queries correctly flagged
- **Fallback rate**: % of queries using fallback route

**Retrieval Metrics**:
- **Precision@5**: % of top-5 results that are relevant
- **Recall@5**: % of relevant docs in top-5
- **NDCG@5**: Normalized discounted cumulative gain
- **MRR**: Mean reciprocal rank of first relevant result
- **F1 Score**: Harmonic mean of precision and recall

**Quality Validation Metrics**:
- **NLI accuracy**: % of NLI judgments that match human annotation
- **False positive rate**: % of correct answers flagged as hallucinations
- **False negative rate**: % of hallucinations not caught
- **Validation time**: Average time for quality validation

**Synthesis Metrics**:
- **Hallucination rate**: % of answers containing unsupported claims
- **Citation completeness**: % of factual claims with citations
- **Citation accuracy**: % of citations that actually support claims
- **Answer quality** (human-judged): Relevance, completeness, clarity (1-10 scale)

**System Metrics**:
- **End-to-end quality score**: Overall quality on golden dataset
- **Response time**: p50, p95, p99 latencies
- **Success rate**: % of queries that complete successfully
- **Error rate**: % of queries that fail

### Testing Approach

#### Phase 1: Unit Testing (Per Agent)

**Router Agent**:
- Test routing decisions on 25 labeled queries per route type
- Verify confidence calibration with historical data
- Test fallback logic with low-confidence queries
- Verify cache invalidation

**Vector RAG Agent**:
- Test query expansion on 50 queries
- Benchmark retrieval with different top-k values
- Compare reranker models (current vs upgraded)
- Test fallback logic with low-score results

**Graph RAG Agent**:
- Test entity extraction on 30 entity-heavy queries
- Verify Cypher query generation and validation
- Test fuzzy matching and disambiguation
- Test fallback to vector RAG

**Quality Agents**:
- Test NLI validation on 50 answer-context pairs
- Test hallucination pattern detection with synthetic examples
- Test citation cross-checking logic
- Verify quality score fusion

**Synthesis Agent**:
- Test answer generation on 50 queries with retrieved context
- Verify citation completeness
- Test hedging language with uncertain contexts
- Test answer templates

#### Phase 2: Integration Testing

**Workflow Tests**:
- Test complete pipeline on 100 golden dataset queries
- Verify agent coordination and state management
- Test error handling with simulated failures
- Test retry logic and fallback strategies
- Test timeout handling

**Quality Gates**:
- Verify quality score calculation
- Test quality-based decisions (accept/warn/regenerate)
- Test graceful degradation

**Performance Tests**:
- Load test with 50 concurrent users
- Measure latency under load
- Verify timeout protection works
- Test cache performance

#### Phase 3: A/B Comparison

**Old vs New System**:
- Run both systems on same 100 queries
- Compare routing accuracy
- Compare retrieval quality (Precision, Recall, F1)
- Compare answer quality (hallucination rate, citation completeness)
- Compare response times
- Compare error rates

**Success Criteria**:
- Routing accuracy improvement ≥ 2%
- Retrieval Precision@5 improvement ≥ 2%
- Hallucination rate reduction ≥ 60%
- Citation completeness improvement ≥ 8%
- No regression on response time (< 10% increase acceptable)
- Error rate improvement ≥ 50%

#### Phase 4: Regression Testing

**Ensure No Breaking Changes**:
- Run full test suite on existing functionality
- Verify API contracts unchanged
- Test backward compatibility with frontend
- Test database schema compatibility
- Verify SSE streaming still works

**Edge Case Testing**:
- Empty queries
- Very long queries (> 500 words)
- Multilingual queries (Chinese, English, mixed)
- Queries with special characters
- Concurrent queries from same session
- Session expiration handling

---

## Implementation Plan

### Phase 1: Router & Retrieval (Day 1)

**Morning (4h): Router Agent**
- [ ] Add few-shot examples to router prompt
- [ ] Implement confidence calibration logic
- [ ] Add fallback strategies for low confidence
- [ ] Add cache versioning and invalidation
- [ ] Unit test routing decisions (25 queries per type)

**Afternoon (4h): Vector RAG**
- [ ] Implement query expansion (entity extraction, synonyms)
- [ ] Add dynamic top-k based on query complexity
- [ ] Tune RRF weights for different query types
- [ ] Implement retrieval fallback logic
- [ ] Unit test retrieval quality (50 queries)

**Evening (2h): Graph RAG**
- [ ] Implement multi-stage entity extraction
- [ ] Add Cypher query validation
- [ ] Implement fuzzy matching for entity linking
- [ ] Add fallback to vector RAG
- [ ] Unit test entity extraction and queries (30 queries)

**Deliverables**:
- Enhanced router_agent.py with better prompts and fallback
- Enhanced vector_rag_agent.py with query expansion and tuning
- Enhanced graph_rag_agent.py with robust entity handling
- Unit test results showing improvement

---

### Phase 2: Quality Validation (Day 2)

**Morning (4h): Answer Validator**
- [ ] Implement multi-stage NLI validation
- [ ] Add hallucination pattern detection (dates, numbers, entities)
- [ ] Implement citation cross-checking
- [ ] Add false positive reduction logic
- [ ] Unit test on 50 answer-context pairs

**Afternoon (3h): Route & Retrieval Quality**
- [ ] Implement historical accuracy tracking for router
- [ ] Add ambiguity detection logic
- [ ] Implement LLM-based relevance scoring for retrieval
- [ ] Add coverage and consistency checking
- [ ] Unit test validation accuracy

**Evening (3h): Quality Orchestrator**
- [ ] Test different weight configurations
- [ ] Implement dynamic thresholds by query type
- [ ] Enhance penalty rules
- [ ] Add actionable recommendations
- [ ] Integration test quality score fusion

**Deliverables**:
- Enhanced answer_validator_agent.py with multi-stage validation
- Enhanced route_validator_agent.py with historical tracking
- Enhanced retrieval_quality_agent.py with LLM relevance scoring
- Enhanced quality_orchestrator_agent.py with optimized weights
- Quality validation accuracy results

---

### Phase 3: Synthesis & Orchestration (Day 2.5)

**Morning (3h): Synthesis Agent**
- [ ] Implement citation-first approach in prompt
- [ ] Add chain-of-thought synthesis
- [ ] Create answer templates for different query types
- [ ] Add confidence indicators and hedging
- [ ] Implement post-generation fact verification
- [ ] Unit test on 50 queries

**Afternoon (2h): Workflow Orchestration**
- [ ] Implement graceful degradation strategies
- [ ] Add circuit breaker pattern
- [ ] Implement intelligent retry logic
- [ ] Enhance error isolation and logging
- [ ] Add execution tracing with correlation IDs

**Deliverables**:
- Enhanced synthesis_agent.py with citation discipline
- Enhanced enhanced_rag_workflow.py with better error handling
- Workflow integration tests passing
- Reduced hallucination rate demonstrated

---

### Phase 4: Testing & Tuning (Day 3)

**Morning (3h): Golden Dataset Testing**
- [ ] Create golden dataset (100 queries with expected outcomes)
- [ ] Run new system on golden dataset
- [ ] Measure all metrics (routing, retrieval, quality, synthesis)
- [ ] Compare against baseline (old system)
- [ ] Identify failing cases

**Afternoon (2h): A/B Comparison & Tuning**
- [ ] Run side-by-side comparison on golden dataset
- [ ] Analyze improvement areas and remaining gaps
- [ ] Tune thresholds based on results
- [ ] Fix critical issues identified in testing
- [ ] Re-run tests to verify improvements

**Evening (2h): Performance & Regression Testing**
- [ ] Load test with 50 concurrent users
- [ ] Measure latency under load
- [ ] Run regression test suite
- [ ] Verify no breaking changes
- [ ] Document performance characteristics

**Final (1h): Documentation & Handoff**
- [ ] Update CHANGELOG.md with improvements
- [ ] Document configuration parameters
- [ ] Create monitoring dashboard queries
- [ ] Write deployment guide
- [ ] Prepare demo for stakeholders

**Deliverables**:
- Golden dataset with 100 annotated queries
- A/B comparison report showing improvements
- Performance benchmark results
- Updated documentation
- Production-ready code

---

## Success Metrics Summary

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| **Router Accuracy** | 95% | 98% | % correct routes on golden dataset |
| **Retrieval Precision@5** | 0.90 | 0.93 | Top-5 precision on 100 queries |
| **NLI Validation Accuracy** | 92% | 96% | % correct validations on test set |
| **Hallucination Rate** | 15-40% | 5-8% | % answers with unsupported claims |
| **Citation Completeness** | 85% | 95% | % factual claims with citations |
| **System Reliability** | 99.5% | 99.8% | % successful query completions |
| **Response Time P95** | 3.5s | <4.0s | 95th percentile latency |
| **Error Rate** | 0.5% | 0.2% | % failed queries |

---

## Risk Mitigation

### Technical Risks

**Risk: Prompt changes reduce quality**
- **Mitigation**: A/B test all prompt changes, maintain versioning, easy rollback
- **Contingency**: Keep old prompts as fallback option

**Risk: Performance degradation from additional checks**
- **Mitigation**: Profile all changes, use async where possible, add caching
- **Contingency**: Make quality checks optional via feature flag

**Risk: Breaking changes to API**
- **Mitigation**: Maintain backward compatibility, version all APIs
- **Contingency**: Provide adapter layer for old API format

**Risk: LLM model changes affect behavior**
- **Mitigation**: Pin model versions, test with multiple models
- **Contingency**: Support multiple model backends

### Operational Risks

**Risk: Deployment causes production issues**
- **Mitigation**: Deploy to staging first, gradual rollout (10% → 50% → 100%)
- **Contingency**: Instant rollback capability, keep old version running

**Risk: New bugs introduced**
- **Mitigation**: Comprehensive testing, code review, monitoring alerts
- **Contingency**: On-call support during rollout, quick hotfix process

**Risk: User confusion from changed behavior**
- **Mitigation**: Document changes, update UI messages, user communication
- **Contingency**: Add explanation in UI for quality scores and warnings

---

## Configuration & Tuning Parameters

### Router Configuration
```python
ROUTER_FEW_SHOT_EXAMPLES = 5  # Number of examples per route type
ROUTER_CONFIDENCE_THRESHOLD = 0.6  # Minimum confidence before fallback
ROUTER_USE_REASONING_MODEL = False  # Use reasoning model for complex queries
ROUTER_CACHE_VERSION = "v2"  # Cache version for invalidation
```

### Retrieval Configuration
```python
VECTOR_TOP_K = 20  # Initial retrieval size
VECTOR_FINAL_K = 5  # After reranking
BM25_WEIGHT = 0.3  # BM25 weight in RRF
VECTOR_WEIGHT = 0.7  # Vector weight in RRF
RERANKER_THRESHOLD = 0.5  # Minimum reranker score
CHUNK_SIZE = 500  # Tokens per chunk
CHUNK_OVERLAP = 100  # Overlap tokens
```

### Quality Validation Configuration
```python
NLI_ENTAILMENT_THRESHOLD = 0.7  # NLI entailment confidence
HALLUCINATION_RISK_THRESHOLD = 0.3  # High risk threshold
CITATION_COMPLETENESS_THRESHOLD = 0.8  # Minimum citation coverage
QUALITY_HIGH_THRESHOLD = 0.8  # High quality score
QUALITY_MEDIUM_THRESHOLD = 0.6  # Medium quality score
QUALITY_LOW_THRESHOLD = 0.4  # Low quality score
```

### Workflow Configuration
```python
MAX_ROUTE_RETRIES = 1  # Maximum route retry attempts
MAX_ANSWER_RETRIES = 1  # Maximum answer regeneration attempts
TOTAL_TIMEOUT_MS = 10000  # Total workflow timeout
CIRCUIT_BREAKER_THRESHOLD = 0.5  # Error rate to trigger circuit breaker
CIRCUIT_BREAKER_DURATION = 300  # Seconds to disable failing agent
```

---

## Why This Design Works

**Quality-First Approach**:
- Addresses root causes, not symptoms
- Each improvement builds on previous work
- Systematic validation at every step

**Architectural Soundness**:
- Leverages existing agent structure
- Adds capabilities without breaking changes
- Maintains separation of concerns

**Risk Management**:
- Incremental implementation with checkpoints
- Comprehensive testing at each phase
- Easy rollback if issues arise

**Measurable Impact**:
- Clear metrics for each component
- A/B testing validates improvements
- Success criteria aligned with business goals

**Maintainability**:
- Configuration-driven behavior
- Well-documented parameters
- Tunable thresholds for optimization

