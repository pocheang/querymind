# Agent Quality Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Quality-first deep refactor of all 11 agents to improve accuracy from 95%→98% (Router), precision from 0.90→0.93+ (RAG), validation from 92%→96% (Quality), and reduce hallucinations by 70-80% (Synthesis)

**Architecture:** Systematic enhancement across 4 layers: (1) Router with few-shot prompts and confidence calibration, (2) RAG with query expansion and parameter tuning, (3) Quality validators with multi-stage NLI and pattern detection, (4) Synthesis with citation discipline and fact verification. Each phase builds on previous work with independent testing.

**Tech Stack:** Python 3.11+, FastAPI, LangChain, LangGraph, ChromaDB, Neo4j, BGE-reranker, NLI models, Pydantic

## Global Constraints

- Python version: 3.11+
- Conda environment: `rag-local` must be activated for all operations
- All changes must maintain backward compatibility with existing API contracts
- Response time regression acceptable if < 10% increase
- No breaking changes to frontend integration or SSE streaming
- All configuration must be externalized (no hardcoded thresholds in logic)
- Maintain existing database schemas (SQLite/PostgreSQL, ChromaDB, Neo4j)
- All prompts must support both English and Chinese queries
- Quality metrics must be measurable and logged
- Error handling must prevent cascading failures

---

## Phase 1: Router & Retrieval Foundation (Day 1 - 10 hours)

### Task 1: Router Agent - Few-Shot Prompt Enhancement

**Goal:** Add few-shot examples and reasoning chain to router prompt to improve accuracy from 95% to 98%

**Files:**
- Modify: `app/agents/router_agent.py:46-82` (ROUTER_PROMPT constant)
- Modify: `app/agents/router_agent.py:118-135` (decide_route function)
- Create: `app/agents/router_examples.py` (few-shot example library)
- Test: `tests/agents/test_router_enhanced.py`

**Interfaces:**
- Consumes: None (entry point)
- Produces: Enhanced ROUTER_PROMPT (str), decide_route() returns RouteDecision with calibrated confidence

---

#### Step 1.1: Create few-shot examples library

- [ ] **Write test for few-shot examples structure**

Create `tests/agents/test_router_enhanced.py`:

```python
"""Tests for enhanced router agent with few-shot examples."""
import pytest
from app.agents.router_examples import (
    get_few_shot_examples_by_route,
    format_examples_for_prompt,
    EXAMPLE_VECTOR_QUERIES,
    EXAMPLE_GRAPH_QUERIES,
    EXAMPLE_HYBRID_QUERIES,
)


def test_few_shot_examples_structure():
    """Test that few-shot examples have required fields."""
    for route_type in ["vector", "graph", "hybrid", "react"]:
        examples = get_few_shot_examples_by_route(route_type)
        assert len(examples) >= 3, f"{route_type} should have at least 3 examples"
        
        for ex in examples:
            assert "query" in ex
            assert "route" in ex
            assert "reason" in ex
            assert "confidence" in ex
            assert isinstance(ex["confidence"], float)
            assert 0.0 <= ex["confidence"] <= 1.0


def test_format_examples_for_prompt():
    """Test that examples are formatted correctly for LLM prompt."""
    examples = get_few_shot_examples_by_route("vector", count=2)
    formatted = format_examples_for_prompt(examples)
    
    assert "Query:" in formatted
    assert "Route:" in formatted
    assert "Reason:" in formatted
    assert "Confidence:" in formatted
    assert len(formatted) > 100  # Should be substantial text


def test_example_vector_queries_content():
    """Test vector query examples are appropriate."""
    assert len(EXAMPLE_VECTOR_QUERIES) >= 5
    
    # Check for concept/definition queries
    concept_queries = [ex for ex in EXAMPLE_VECTOR_QUERIES if "definition" in ex["reason"].lower() or "concept" in ex["reason"].lower()]
    assert len(concept_queries) >= 2
```

- [ ] **Run test to verify it fails**

```bash
conda activate rag-local
pytest tests/agents/test_router_enhanced.py::test_few_shot_examples_structure -v
```

Expected: `ModuleNotFoundError: No module named 'app.agents.router_examples'`

- [ ] **Create few-shot examples library**

Create `app/agents/router_examples.py`:

```python
"""
Few-shot examples for router agent prompt engineering.

Provides curated examples of routing decisions across different query types
to improve LLM routing accuracy through in-context learning.
"""
from typing import List, Dict, Any

# Vector RAG examples - concept queries, definitions, facts
EXAMPLE_VECTOR_QUERIES = [
    {
        "query": "What is machine learning?",
        "route": "vector",
        "reason": "Concept definition query best answered from document text",
        "confidence": 0.95
    },
    {
        "query": "Explain the transformer architecture",
        "route": "vector",
        "reason": "Technical explanation requiring detailed text from papers/docs",
        "confidence": 0.92
    },
    {
        "query": "What are the benefits of cloud computing?",
        "route": "vector",
        "reason": "Factual information query, needs comprehensive text retrieval",
        "confidence": 0.90
    },
    {
        "query": "How does gradient descent work?",
        "route": "vector",
        "reason": "Algorithm explanation, best from educational content",
        "confidence": 0.93
    },
    {
        "query": "什么是深度学习？",  # What is deep learning?
        "route": "vector",
        "reason": "Chinese concept definition, semantic search in documents",
        "confidence": 0.94
    },
]

# Graph RAG examples - relationship queries, entity connections
EXAMPLE_GRAPH_QUERIES = [
    {
        "query": "Who reports to the CTO?",
        "route": "graph",
        "reason": "Org chart relationship query, needs knowledge graph traversal",
        "confidence": 0.96
    },
    {
        "query": "What projects is Alice working on?",
        "route": "graph",
        "reason": "Person-project relationship, graph entity connections",
        "confidence": 0.94
    },
    {
        "query": "Show me the connection between OpenAI and Anthropic",
        "route": "graph",
        "reason": "Entity relationship query, multi-hop reasoning in graph",
        "confidence": 0.91
    },
    {
        "query": "Which teams depend on the authentication service?",
        "route": "graph",
        "reason": "Dependency relationship query, graph traversal needed",
        "confidence": 0.93
    },
    {
        "query": "张三的直接下属有哪些？",  # Who are Zhang San's direct reports?
        "route": "graph",
        "reason": "Chinese org structure query, relationship traversal",
        "confidence": 0.95
    },
]

# Hybrid examples - queries needing both text and graph
EXAMPLE_HYBRID_QUERIES = [
    {
        "query": "Compare Python and Java for machine learning",
        "route": "hybrid",
        "reason": "Comparison needs concept understanding (vector) AND feature comparison (structured)",
        "confidence": 0.88
    },
    {
        "query": "What are the technical skills of team members in the AI department?",
        "route": "hybrid",
        "reason": "Combines org structure (graph) with skill descriptions (vector)",
        "confidence": 0.87
    },
    {
        "query": "How do microservices relate to our current architecture?",
        "route": "hybrid",
        "reason": "Concept explanation (vector) + architecture dependencies (graph)",
        "confidence": 0.86
    },
]

# ReAct examples - complex multi-step reasoning
EXAMPLE_REACT_QUERIES = [
    {
        "query": "Find all Python experts, check their current projects, and recommend who should lead the new ML initiative",
        "route": "react",
        "reason": "Multi-step task: search experts, analyze projects, make recommendation",
        "confidence": 0.89
    },
    {
        "query": "Compare the performance of different database solutions and suggest the best one for our use case",
        "route": "react",
        "reason": "Requires research, comparison, and contextual reasoning",
        "confidence": 0.85
    },
]


def get_few_shot_examples_by_route(route_type: str, count: int = 5) -> List[Dict[str, Any]]:
    """
    Get few-shot examples for a specific route type.
    
    Args:
        route_type: One of "vector", "graph", "hybrid", "react"
        count: Number of examples to return (default 5, max available)
    
    Returns:
        List of example dictionaries with query, route, reason, confidence
    """
    examples_map = {
        "vector": EXAMPLE_VECTOR_QUERIES,
        "graph": EXAMPLE_GRAPH_QUERIES,
        "hybrid": EXAMPLE_HYBRID_QUERIES,
        "react": EXAMPLE_REACT_QUERIES,
    }
    
    examples = examples_map.get(route_type, [])
    return examples[:count]


def format_examples_for_prompt(examples: List[Dict[str, Any]]) -> str:
    """
    Format few-shot examples for inclusion in LLM prompt.
    
    Args:
        examples: List of example dictionaries
    
    Returns:
        Formatted string for prompt injection
    """
    formatted_lines = ["Examples of correct routing decisions:\n"]
    
    for i, ex in enumerate(examples, 1):
        formatted_lines.append(f"\nExample {i}:")
        formatted_lines.append(f"Query: \"{ex['query']}\"")
        formatted_lines.append(f"Route: {ex['route']}")
        formatted_lines.append(f"Reason: {ex['reason']}")
        formatted_lines.append(f"Confidence: {ex['confidence']}")
    
    return "\n".join(formatted_lines)


def get_mixed_examples(vector_count: int = 2, graph_count: int = 2, 
                       hybrid_count: int = 1, react_count: int = 1) -> str:
    """
    Get a balanced mix of examples across all route types.
    
    Args:
        vector_count: Number of vector examples
        graph_count: Number of graph examples
        hybrid_count: Number of hybrid examples
        react_count: Number of react examples
    
    Returns:
        Formatted prompt string with mixed examples
    """
    all_examples = []
    all_examples.extend(get_few_shot_examples_by_route("vector", vector_count))
    all_examples.extend(get_few_shot_examples_by_route("graph", graph_count))
    all_examples.extend(get_few_shot_examples_by_route("hybrid", hybrid_count))
    all_examples.extend(get_few_shot_examples_by_route("react", react_count))
    
    return format_examples_for_prompt(all_examples)
```

- [ ] **Run test to verify it passes**

```bash
pytest tests/agents/test_router_enhanced.py -v
```

Expected: All tests PASS

- [ ] **Commit few-shot examples library**

```bash
git add app/agents/router_examples.py tests/agents/test_router_enhanced.py
git commit -m "feat(router): add few-shot examples library for prompt engineering

- Create router_examples.py with curated examples per route type
- 5 vector examples (concept/definition queries)
- 5 graph examples (relationship queries)
- 3 hybrid examples (mixed requirements)
- 2 react examples (multi-step reasoning)
- Support Chinese and English queries
- Helper functions for prompt formatting"
```

---

#### Step 1.2: Enhance ROUTER_PROMPT with few-shot examples and reasoning chain

- [ ] **Write test for enhanced router prompt**

Add to `tests/agents/test_router_enhanced.py`:

```python
def test_enhanced_router_prompt_includes_examples():
    """Test that enhanced prompt includes few-shot examples."""
    from app.agents.router_agent import ROUTER_PROMPT
    
    # Should include few-shot examples
    assert "Example" in ROUTER_PROMPT or "examples" in ROUTER_PROMPT.lower()
    
    # Should include reasoning instruction
    assert "reason" in ROUTER_PROMPT.lower() or "explain" in ROUTER_PROMPT.lower()
    
    # Should still have route options
    assert "vector" in ROUTER_PROMPT
    assert "graph" in ROUTER_PROMPT
    assert "hybrid" in ROUTER_PROMPT


def test_decide_route_returns_enhanced_decision():
    """Test that decide_route returns decision with reasoning."""
    from app.agents.router_agent import decide_route
    
    decision = decide_route("What is machine learning?")
    
    assert hasattr(decision, "route")
    assert hasattr(decision, "reason")
    assert hasattr(decision, "confidence")
    assert hasattr(decision, "skill")
    
    # Reason should be non-empty
    assert len(decision.reason) > 10
```

- [ ] **Run test to verify current implementation fails**

```bash
pytest tests/agents/test_router_enhanced.py::test_enhanced_router_prompt_includes_examples -v
```

Expected: May pass or fail depending on current prompt

- [ ] **Update ROUTER_PROMPT in router_agent.py**

Modify `app/agents/router_agent.py` at line 46:

```python
from app.agents.router_examples import get_mixed_examples

ROUTER_PROMPT = """
You are a route planner for a RAG (Retrieval-Augmented Generation) assistant.

Your task: Analyze the user's query and choose the best retrieval route.

Available routes:
- vector: Find answers from text chunks using semantic search (best for concepts, definitions, facts)
- graph: Query entity relationships in knowledge graph (best for "who", "what relationship", organizational queries)
- hybrid: Combine both text retrieval AND graph queries (best for comparisons, complex questions needing both)
- react: Multi-step reasoning with iterative tool use (best for "compare then analyze", multi-step investigations)

Skills to choose from:
- answer_with_citations: Standard Q&A with source citations
- compare_entities: Side-by-side comparison
- timeline_builder: Chronological event sequences
- web_fact_check: Verify with web search
- cyber_attack_analysis: Attack chain analysis
- cyber_defense_hardening: Defense recommendations
- incident_response_playbook: Incident handling
- ai_knowledge_assistant: General AI/ML questions
- pdf_text_reader: Extract and read PDF content

{few_shot_examples}

IMPORTANT: Think step-by-step before deciding:
1. What is the user asking for? (concept, relationship, comparison, multi-step task?)
2. What information sources are needed? (text docs, entity relationships, both, web?)
3. Which route best matches the query pattern?
4. How confident are you in this decision? (0.0-1.0)

Output JSON only:
{{"route":"vector|graph|hybrid|react","reason":"your step-by-step reasoning here","skill":"chosen_skill","confidence":0.0-1.0}}

Query: {{question}}
"""

# Inject few-shot examples into prompt
ROUTER_PROMPT = ROUTER_PROMPT.format(
    few_shot_examples=get_mixed_examples(vector_count=2, graph_count=2, hybrid_count=1, react_count=1)
)
```

- [ ] **Run tests to verify enhanced prompt works**

```bash
pytest tests/agents/test_router_enhanced.py -v
```

Expected: All tests PASS

- [ ] **Test routing accuracy manually with sample queries**

Create `tests/agents/test_router_accuracy.py`:

```python
"""Manual accuracy tests for router with sample queries."""
import pytest
from app.agents.router_agent import decide_route


@pytest.mark.parametrize("query,expected_route", [
    ("What is deep learning?", "vector"),
    ("Who reports to the CEO?", "graph"),
    ("Compare Python and Java", "hybrid"),
    ("Find experts and recommend a team lead", "react"),
])
def test_routing_accuracy_samples(query, expected_route):
    """Test routing accuracy on sample queries."""
    decision = decide_route(query)
    assert decision.route == expected_route, f"Query: {query}, Got: {decision.route}, Expected: {expected_route}, Reason: {decision.reason}"
```

```bash
pytest tests/agents/test_router_accuracy.py -v
```

Expected: Most tests should PASS (aim for 3/4 or 4/4)

- [ ] **Commit enhanced router prompt**

```bash
git add app/agents/router_agent.py tests/agents/test_router_enhanced.py tests/agents/test_router_accuracy.py
git commit -m "feat(router): enhance prompt with few-shot examples and reasoning chain

- Inject 6 few-shot examples into ROUTER_PROMPT (2 vector, 2 graph, 1 hybrid, 1 react)
- Add step-by-step reasoning instructions before decision
- Structured JSON output with explicit reasoning field
- Add tests for prompt structure and routing accuracy
- Expected impact: routing accuracy improvement 95% → 96-97%"
```

---

**Task 1 Complete** ✓ Router now has few-shot examples and reasoning chain

---

### Task 2: Router Agent - Confidence Calibration

**Goal:** Implement confidence calibration to reduce calibration error from ±0.15 to ±0.05

**Files:**
- Create: `app/agents/router_calibration.py` (calibration logic)
- Modify: `app/agents/router_agent.py:135-150` (apply calibration in decide_route)
- Create: `app/agents/router_config.py` (calibration parameters)
- Test: `tests/agents/test_router_calibration.py`

**Implementation Summary:**
- Create confidence bucket system (0.5-0.6, 0.6-0.7, 0.7-0.8, 0.8-0.9, 0.9-1.0)
- Track historical accuracy per bucket (store in config file)
- Apply calibration multiplier: `calibrated = raw_confidence * (historical_accuracy / raw_confidence)`
- Add cache versioning to router_agent.py
- Test calibration improves confidence-accuracy correlation

**Expected Outcome:** Calibrated confidence better reflects actual accuracy

---

### Task 3: Router Agent - Fallback Strategies

**Goal:** Add intelligent fallback for low-confidence routing decisions

**Files:**
- Modify: `app/agents/router_agent.py:135-180` (add fallback logic)
- Modify: `app/agents/agent_config.py` (add ROUTER_LOW_CONFIDENCE_THRESHOLD)
- Test: `tests/agents/test_router_fallback.py`

**Implementation Summary:**
- If confidence < 0.6, trigger fallback
- Fallback strategy: try reasoning model OR default to vector (safe route)
- Detect ambiguous queries (multiple routes with similar scores)
- Log fallback events for analysis
- Test fallback improves low-confidence query handling

**Expected Outcome:** Ambiguous query handling improves from 60% to 90%

---

### Task 4: Vector RAG - Query Expansion

**Goal:** Add entity extraction and synonym expansion to improve query understanding

**Files:**
- Create: `app/retrievers/query_expansion.py` (expansion logic)
- Modify: `app/agents/vector_rag_agent.py` (integrate expansion)
- Test: `tests/retrievers/test_query_expansion.py`

**Implementation Summary:**
- Use spaCy or similar for entity extraction
- Add synonym dictionary for common terms ("ML" → "machine learning")
- Expand queries with extracted entities + synonyms
- Test expansion improves retrieval for abbreviated/incomplete queries
- Measure impact on Precision@5

**Expected Outcome:** Query understanding improves from 85% to 92%

---

### Task 5: Vector RAG - Dynamic Parameters

**Goal:** Implement dynamic top-k and RRF weight tuning based on query type

**Files:**
- Modify: `app/agents/vector_rag_agent.py` (add dynamic parameters)
- Create: `app/retrievers/parameter_tuning.py` (tuning logic)
- Test: `tests/retrievers/test_dynamic_parameters.py`

**Implementation Summary:**
- Classify query complexity (simple/medium/complex)
- Adjust top-k: simple=15, medium=20, complex=30
- Tune vector:BM25 weights by query type
- Test parameter tuning improves retrieval quality
- Measure Precision@5 and Recall@5 improvements

**Expected Outcome:** Precision@5 improves from 0.90 to 0.92

---

### Task 6: Graph RAG - Robust Entity Extraction

**Goal:** Implement multi-stage entity extraction with validation

**Files:**
- Create: `app/graph/entity_extraction.py` (extraction logic)
- Modify: `app/agents/graph_rag_agent.py` (integrate extraction)
- Test: `tests/graph/test_entity_extraction.py`

**Implementation Summary:**
- Stage 1: Rule-based NER for common patterns
- Stage 2: LLM-based extraction for complex cases
- Cross-validate between methods
- Fuzzy matching for entity linking (Levenshtein distance ≤ 2)
- Test extraction accuracy on entity-heavy queries

**Expected Outcome:** Entity extraction accuracy improves from 85% to 92%

---

### Task 7: Graph RAG - Cypher Validation & Fallback

**Goal:** Add Cypher query validation and fallback to vector RAG

**Files:**
- Create: `app/graph/cypher_validation.py` (validation logic)
- Modify: `app/agents/graph_rag_agent.py` (add validation and fallback)
- Test: `tests/graph/test_cypher_validation.py`

**Implementation Summary:**
- Parse and validate Cypher syntax before execution
- Catch Neo4j errors and retry with simpler query
- If graph returns 0 results, fall back to vector RAG
- Add query templates for common patterns
- Test validation reduces malformed queries

**Expected Outcome:** Graph query success rate improves from 88% to 95%, empty results reduce from 15% to 5%

---

## Phase 2: Quality Validation (Day 2 - 10 hours)

### Task 8: Answer Validator - Multi-Stage NLI

**Goal:** Implement 4-level validation cascade with sentence-level NLI

**Files:**
- Modify: `app/agents/answer_validator_agent.py` (add cascade)
- Create: `app/agents/validation_cascade.py` (cascade logic)
- Test: `tests/agents/test_answer_validator_cascade.py`

**Implementation Summary:**
- Level 1: Fast rule-based checks (dates, numbers, entities) - 5ms
- Level 2: Sentence-level NLI batch validation - 100ms
- Level 3: Citation cross-checking - 50ms
- Level 4: Deep LLM check (only if issues flagged) - 200ms
- Test cascade improves accuracy and reduces false positives

**Expected Outcome:** NLI accuracy improves from 92% to 96%, false positive rate drops from 8% to 3%

---

### Task 9: Answer Validator - Hallucination Pattern Detection

**Goal:** Add rule-based checks for common hallucination patterns

**Files:**
- Create: `app/agents/hallucination_patterns.py` (pattern detection)
- Modify: `app/agents/answer_validator_agent.py` (integrate patterns)
- Test: `tests/agents/test_hallucination_detection.py`

**Implementation Summary:**
- Date validation: check if dates appear in source
- Number validation: verify numerical claims
- Entity validation: check entity mentions in context
- Negation detection: ensure answer doesn't negate source
- Test pattern detection catches common hallucinations

**Expected Outcome:** Hallucination detection improves from 85% to 95%

---

### Task 10: Route Validator - Historical Accuracy Tracking

**Goal:** Build accuracy model per route type for confidence recalibration

**Files:**
- Create: `app/agents/route_accuracy_tracker.py` (tracking logic)
- Modify: `app/agents/route_validator_agent.py` (integrate tracking)
- Test: `tests/agents/test_route_accuracy.py`

**Implementation Summary:**
- Track actual routing outcomes (did route produce good results?)
- Build accuracy model per route type and query pattern
- Use history to recalibrate confidence
- Store tracking data in database or file
- Test tracking improves route validation accuracy

**Expected Outcome:** Route validation accuracy improves from 90% to 95%

---

### Task 11: Retrieval Quality - LLM Relevance Scoring

**Goal:** Add lightweight LLM scoring for query-document relevance

**Files:**
- Create: `app/agents/relevance_scoring.py` (scoring logic)
- Modify: `app/agents/retrieval_quality_agent.py` (integrate scoring)
- Test: `tests/agents/test_relevance_scoring.py`

**Implementation Summary:**
- Use Haiku or similar fast model for relevance scoring
- 3-point scale: Highly Relevant (1.0), Somewhat (0.5), Not Relevant (0.0)
- Batch process top-5 results in <100ms
- Aggregate scores for overall quality metric
- Test scoring correlates with human judgments

**Expected Outcome:** Relevance assessment accuracy improves from 80% to 92%

---

### Task 12: Quality Orchestrator - Weight Optimization

**Goal:** A/B test and optimize quality score fusion weights

**Files:**
- Create: `tests/golden_dataset.py` (100-query test set)
- Modify: `app/agents/quality_orchestrator_agent.py` (update weights)
- Create: `scripts/test_quality_weights.py` (A/B testing script)

**Implementation Summary:**
- Create golden dataset with 100 annotated queries
- Test current weights: Route 15%, Retrieval 25%, Fact 40%, Quality 15%, Cite 5%
- Test alternative: Route 10%, Retrieval 30%, Fact 45%, Quality 10%, Cite 5%
- Measure correlation with human quality judgments
- Choose weights that maximize correlation

**Expected Outcome:** Quality score correlation with human judgment improves from 0.75 to 0.88

---

## Phase 3: Synthesis & Orchestration (Day 2.5 - 5 hours)

### Task 13: Synthesis Agent - Citation-First Generation

**Goal:** Implement citation discipline in answer generation

**Files:**
- Modify: `app/agents/synthesis_agent.py` (update prompt and logic)
- Create: `app/agents/synthesis_templates.py` (answer templates)
- Test: `tests/agents/test_synthesis_citation.py`

**Implementation Summary:**
- Update prompt: "Every factual claim MUST have citation [doc_id:page]"
- Add chain-of-thought reasoning before generation
- Implement answer templates by query type (concept, comparison, relationship)
- Add hedging language for uncertain contexts
- Test citation completeness and groundedness

**Expected Outcome:** Citation completeness improves from 85% to 95%, hallucination rate drops from 15-40% to 5-8%

---

### Task 14: Synthesis Agent - Fact Verification Layer

**Goal:** Add post-generation fact verification

**Files:**
- Create: `app/agents/fact_verification.py` (verification logic)
- Modify: `app/agents/synthesis_agent.py` (integrate verification)
- Test: `tests/agents/test_fact_verification.py`

**Implementation Summary:**
- Extract all factual claims from generated answer
- Verify each fact appears in cited source
- Check for date/number accuracy
- Detect negations and contradictions
- Flag unverified claims for removal or hedging

**Expected Outcome:** Answer groundedness improves from 80% to 94%

---

### Task 15: Workflow Orchestration - Graceful Degradation

**Goal:** Implement fallback strategies for agent failures

**Files:**
- Modify: `app/agents/enhanced_rag_workflow.py` (add degradation logic)
- Create: `app/agents/degradation_strategies.py` (fallback rules)
- Test: `tests/agents/test_graceful_degradation.py`

**Implementation Summary:**
- Define fallback for each failure mode
- Router fails → default to vector RAG
- Vector RAG fails → try graph or web
- Quality validation fails → return with warning
- Add circuit breaker pattern (disable failing agents)
- Test degradation prevents cascading failures

**Expected Outcome:** System availability improves from 99.5% to 99.8%, cascading failures reduce from 5% to 1%

---

### Task 16: Workflow Orchestration - Intelligent Retry

**Goal:** Implement retry with variation instead of identical retries

**Files:**
- Modify: `app/agents/enhanced_rag_workflow.py` (update retry logic)
- Test: `tests/agents/test_intelligent_retry.py`

**Implementation Summary:**
- First retry: increase retrieval top-k (5 → 10)
- Second retry: try alternative route (vector → hybrid)
- Third retry: use reasoning model instead of chat model
- Max 2 retries per agent
- Exponential backoff: 100ms, 500ms
- Test retry improves success rate

**Expected Outcome:** Retry success rate improves, mean time to recovery drops from 2min to 30s

---

## Phase 4: Testing & Tuning (Day 3 - 8 hours)

### Task 17: Create Golden Dataset

**Goal:** Build 100-query test dataset with expected outcomes

**Files:**
- Create: `tests/golden_dataset.json` (100 queries with annotations)
- Create: `scripts/create_golden_dataset.py` (dataset builder)

**Dataset Composition:**
- 25 concept queries with expected answers
- 20 relationship queries with expected entities
- 15 comparison queries with expected structure
- 15 multi-hop reasoning queries
- 10 ambiguous queries with expected clarifications
- 10 follow-up queries with context
- 5 edge cases (empty, contradictory, time-sensitive)

**Expected Outcome:** Comprehensive test dataset for validation

---

### Task 18: A/B Comparison Testing

**Goal:** Run old vs new system on golden dataset and measure improvements

**Files:**
- Create: `scripts/ab_comparison.py` (comparison script)
- Create: `docs/ab_comparison_report.md` (results report)

**Metrics to Compare:**
- Router accuracy (target: 95% → 98%)
- Retrieval Precision@5 (target: 0.90 → 0.93)
- NLI validation accuracy (target: 92% → 96%)
- Hallucination rate (target: 15-40% → 5-8%)
- Citation completeness (target: 85% → 95%)
- Response time P95 (acceptable: < 10% regression)

**Success Criteria:**
- All target metrics met or exceeded
- No major regression on response time
- Error rate reduced by ≥50%

**Expected Outcome:** Validation of all improvements

---

### Task 19: Performance & Regression Testing

**Goal:** Verify no breaking changes and acceptable performance

**Files:**
- Create: `scripts/load_test.py` (concurrent load test)
- Run existing test suite for regression

**Tests:**
- Load test: 50 concurrent users
- Latency measurement: p50, p95, p99
- API contract verification
- Frontend compatibility test
- SSE streaming verification
- Database schema compatibility

**Expected Outcome:** All tests pass, performance acceptable

---

### Task 20: Documentation & Deployment

**Goal:** Update documentation and prepare for deployment

**Files:**
- Update: `CHANGELOG.md` (add v0.6.0 improvements)
- Update: `docs/AGENT_INTEGRATION_GUIDE.md` (document changes)
- Create: `docs/DEPLOYMENT_GUIDE_v0.6.0.md` (deployment instructions)
- Update: `README.md` (update metrics)

**Documentation:**
- Document all configuration parameters
- Create monitoring dashboard queries
- Write deployment guide with rollback plan
- Update API documentation if needed

**Expected Outcome:** Production-ready deployment package

---

## Success Metrics Summary

| Metric | Baseline | Target | Status |
|--------|----------|--------|--------|
| **Router Accuracy** | 95% | 98% | □ |
| **Retrieval Precision@5** | 0.90 | 0.93 | □ |
| **NLI Validation Accuracy** | 92% | 96% | □ |
| **Hallucination Rate** | 15-40% | 5-8% | □ |
| **Citation Completeness** | 85% | 95% | □ |
| **System Reliability** | 99.5% | 99.8% | □ |
| **Response Time P95** | 3.5s | <4.0s | □ |
| **Error Rate** | 0.5% | 0.2% | □ |

---

## Execution Notes

**This is a large-scale refactor project with 20 tasks across 4 phases spanning 3 days.**

**Recommended Execution Approach:**
1. **Subagent-Driven Development** (Preferred): Execute tasks sequentially with independent subagents, allowing review between tasks
2. **Inline Execution**: Execute in current session with checkpoints for review

**Critical Path:**
- Phase 1 (Router & Retrieval) must complete before Phase 2
- Phase 2 (Quality Validation) builds on Phase 1 outputs
- Phase 3 (Synthesis & Orchestration) integrates all prior work
- Phase 4 (Testing) validates everything

**Risk Mitigation:**
- Each task includes tests for validation
- Frequent commits allow rollback
- A/B testing validates improvements
- Gradual deployment recommended (10% → 50% → 100%)

