# Quality Assurance Agents Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 5 quality assurance agents to systematically improve route accuracy, retrieval quality, and answer trustworthiness in the QueryMind RAG system

**Architecture:** Hybrid validation mode with critical checkpoints using serial validation and non-critical metrics using parallel monitoring. Performance-optimized with rule-based fast paths and LLM fallbacks.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic 2.0+, asyncio, sentence-transformers (NLI model), Redis (optional)

## Global Constraints

- Python version: 3.11+
- Average added latency target: <250ms
- Route validation fast path threshold: 85% queries <30ms
- Answer validation fast path threshold: 90% queries <180ms
- All async operations must have timeouts
- All configuration must be centralized in quality_config.py
- Use existing model access patterns from app.core.models
- Follow existing agent patterns in app/agents/
- All timestamps use datetime.utcnow()
- Test coverage minimum: 80%

---

## File Structure

```
app/agents/
├── quality_models.py              # Pydantic models for all quality validation data
├── quality_config.py              # Centralized configuration constants
├── route_validator_agent.py       # Route decision validation (rule + LLM)
├── retrieval_quality_agent.py     # Async retrieval quality assessment
├── answer_validator_agent.py      # Answer validation with NLI model
├── quality_orchestrator_agent.py  # Quality score fusion and reporting
├── context_tracker_agent.py       # Session context management
├── enhanced_rag_workflow.py       # Main workflow integration
└── _quality_helpers.py            # Shared utility functions

app/api/routes/
└── enhanced_query.py              # Enhanced query API endpoint

tests/agents/
├── test_quality_models.py
├── test_route_validator.py
├── test_retrieval_quality.py
├── test_answer_validator.py
├── test_quality_orchestrator.py
├── test_context_tracker.py
├── test_enhanced_workflow.py
└── test_integration_quality.py
```

---

### Task 1: Data Models and Configuration

**Files:**
- Create: `app/agents/quality_models.py`
- Create: `app/agents/quality_config.py`
- Create: `tests/agents/test_quality_models.py`

**Interfaces:**
- Consumes: None
- Produces: 
  - `RouteValidationResult(is_valid: bool, confidence: float, validation_method: str, validation_reason: str, execution_time_ms: int, suggested_alternative: Optional[Dict], warnings: List[str])`
  - `RetrievalQualityResult(overall_quality: float, metrics: RetrievalQualityMetrics, execution_time_ms: int, issues: List[str], suggestions: List[str])`
  - `AnswerValidationResult(is_valid: bool, overall_score: float, validation_details: AnswerValidationDetails, issues: List[AnswerIssue], action: Literal["approve", "flag", "regenerate"], execution_time_ms: int, validation_method: str)`
  - `QualityReport(overall_confidence: float, quality_level: str, quality_label: str, user_prompt: Optional[str], breakdown: QualityBreakdown, issues: List[Dict], suggestions: List[str], execution_stats: ExecutionStats)`
  - Configuration constants from `quality_config.py`

- [ ] **Step 1: Write test for RouteValidationResult model**

```python
# tests/agents/test_quality_models.py
from app.agents.quality_models import RouteValidationResult

def test_route_validation_result_creation():
    result = RouteValidationResult(
        is_valid=True,
        confidence=0.92,
        validation_method="rule_fast",
        validation_reason="high_confidence_fast_pass",
        execution_time_ms=8,
        suggested_alternative=None,
        warnings=[]
    )
    assert result.is_valid is True
    assert result.confidence == 0.92
    assert result.validation_method == "rule_fast"
    assert 0.0 <= result.confidence <= 1.0

def test_route_validation_with_alternative():
    result = RouteValidationResult(
        is_valid=False,
        confidence=0.45,
        validation_method="llm",
        validation_reason="low_confidence_mismatch",
        execution_time_ms=320,
        suggested_alternative={"route": "graph", "skill": "compare_entities"},
        warnings=["route_mismatch"]
    )
    assert result.is_valid is False
    assert result.suggested_alternative is not None
    assert result.suggested_alternative["route"] == "graph"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
conda activate rag-local
pytest tests/agents/test_quality_models.py::test_route_validation_result_creation -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'app.agents.quality_models'"

- [ ] **Step 3: Implement quality_models.py with all Pydantic models**

```python
# app/agents/quality_models.py
"""
Pydantic models for quality assurance agents.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal, Any
from datetime import datetime


# Route Validation Models
class RouteValidationResult(BaseModel):
    """Route validation result from Route Validator Agent"""
    is_valid: bool
    confidence: float = Field(ge=0.0, le=1.0)
    validation_method: Literal["rule_fast", "rule_feature", "llm", "cache"]
    validation_reason: str
    execution_time_ms: int
    suggested_alternative: Optional[Dict[str, str]] = None
    warnings: List[str] = Field(default_factory=list)


# Retrieval Quality Models
class RetrievalQualityMetrics(BaseModel):
    """Individual retrieval quality metrics"""
    coverage_score: float = Field(ge=0.0, le=1.0)
    relevance_score: float = Field(ge=0.0, le=1.0)
    diversity_score: float = Field(ge=0.0, le=1.0)
    completeness_score: float = Field(ge=0.0, le=1.0)


class RetrievalQualityResult(BaseModel):
    """Retrieval quality assessment result"""
    overall_quality: float = Field(ge=0.0, le=1.0)
    metrics: RetrievalQualityMetrics
    execution_time_ms: int
    issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


# Answer Validation Models
class AnswerValidationDetails(BaseModel):
    """Detailed answer validation metrics"""
    factual_consistency: float = Field(ge=0.0, le=1.0)
    hallucination_risk: float = Field(ge=0.0, le=1.0)
    citation_completeness: float = Field(ge=0.0, le=1.0)
    answer_quality: float = Field(ge=0.0, le=1.0)
    safety_score: float = Field(ge=0.0, le=1.0)


class AnswerIssue(BaseModel):
    """Individual answer issue"""
    type: Literal["unsupported_claim", "missing_citation", "hallucination", "safety", "quality"]
    content: str
    severity: Literal["low", "medium", "high", "critical"]
    suggestion: str
    location: Optional[str] = None


class AnswerValidationResult(BaseModel):
    """Answer validation result from Answer Validator Agent"""
    is_valid: bool
    overall_score: float = Field(ge=0.0, le=1.0)
    validation_details: AnswerValidationDetails
    issues: List[AnswerIssue] = Field(default_factory=list)
    action: Literal["approve", "flag", "regenerate"]
    execution_time_ms: int
    validation_method: Literal["fast_path", "standard", "deep"]


# Quality Orchestration Models
class QualityBreakdown(BaseModel):
    """Quality score breakdown by component"""
    route_decision: Dict[str, Any]
    retrieval: Dict[str, Any]
    answer_factuality: Dict[str, Any]
    citations: Dict[str, Any]


class ExecutionStats(BaseModel):
    """Execution statistics"""
    total_time_ms: int
    validation_overhead_ms: int
    retry_count: int
    route_retry: int = 0
    answer_retry: int = 0


class QualityReport(BaseModel):
    """Comprehensive quality report from Quality Orchestrator"""
    overall_confidence: float = Field(ge=0.0, le=1.0)
    quality_level: Literal["high", "medium", "low", "very_low"]
    quality_label: str
    user_prompt: Optional[str] = None
    breakdown: QualityBreakdown
    issues: List[Dict[str, str]] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    execution_stats: ExecutionStats


# Context Tracking Models
class ConversationTurn(BaseModel):
    """Single conversation turn"""
    query: str
    response: str
    route: str
    entities: List[str] = Field(default_factory=list)
    timestamp: datetime


class ConversationContext(BaseModel):
    """Conversation context for session"""
    session_id: str
    user_id: str
    conversation_history: List[ConversationTurn] = Field(default_factory=list, max_length=10)
    topic_stack: List[str] = Field(default_factory=list)
    entity_mentions: Dict[str, int] = Field(default_factory=dict)
    current_intent: Optional[str] = None
    context_summary: Optional[str] = None
    last_update_time: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ContextHints(BaseModel):
    """Context hints for routing"""
    resolve_references: Optional[Dict[str, int]] = None
    followup: bool = False
    previous_route: Optional[str] = None
    focus_entities: List[str] = Field(default_factory=list)
```

- [ ] **Step 4: Implement quality_config.py with configuration constants**

```python
# app/agents/quality_config.py
"""
Configuration constants for quality assurance system.
"""

from typing import Final

# Global Switches
ENABLE_QUALITY_VALIDATION: Final[bool] = True
ENABLE_CONTEXT_TRACKING: Final[bool] = True
ENABLE_VERBOSE_LOGGING: Final[bool] = False

# Route Validator Configuration
ROUTE_HIGH_CONFIDENCE_THRESHOLD: Final[float] = 0.85
ROUTE_MEDIUM_CONFIDENCE_THRESHOLD: Final[float] = 0.60
ROUTE_LOW_CONFIDENCE_THRESHOLD: Final[float] = 0.40
ROUTE_VALIDATOR_USE_CACHE: Final[bool] = True
ROUTE_VALIDATOR_CACHE_TTL: Final[int] = 3600

# Retrieval Quality Configuration
RETRIEVAL_WEIGHT_COVERAGE: Final[float] = 0.30
RETRIEVAL_WEIGHT_RELEVANCE: Final[float] = 0.40
RETRIEVAL_WEIGHT_DIVERSITY: Final[float] = 0.15
RETRIEVAL_WEIGHT_COMPLETENESS: Final[float] = 0.15
RETRIEVAL_QUALITY_GOOD_THRESHOLD: Final[float] = 0.70
RETRIEVAL_QUALITY_POOR_THRESHOLD: Final[float] = 0.50
RETRIEVAL_SAMPLE_TOP_K: Final[int] = 3

# Answer Validator Configuration
ANSWER_FAST_PATH_THRESHOLD: Final[float] = 0.80
ANSWER_STANDARD_PATH_THRESHOLD: Final[float] = 0.60
ANSWER_WEIGHT_FACTUALITY: Final[float] = 0.40
ANSWER_WEIGHT_CITATION: Final[float] = 0.25
ANSWER_WEIGHT_QUALITY: Final[float] = 0.25
ANSWER_WEIGHT_SAFETY: Final[float] = 0.10
HALLUCINATION_HIGH_RISK_THRESHOLD: Final[float] = 0.30
HALLUCINATION_MEDIUM_RISK_THRESHOLD: Final[float] = 0.15
ANSWER_APPROVE_THRESHOLD: Final[float] = 0.80
ANSWER_FLAG_THRESHOLD: Final[float] = 0.60
NLI_MODEL_NAME: Final[str] = "cross-encoder/nli-MiniLM2-L6-H768"
NLI_MAX_CHECKS: Final[int] = 5

# Quality Orchestrator Configuration
QUALITY_WEIGHT_ROUTE: Final[float] = 0.15
QUALITY_WEIGHT_RETRIEVAL: Final[float] = 0.25
QUALITY_WEIGHT_ANSWER_FACT: Final[float] = 0.40
QUALITY_WEIGHT_ANSWER_QUALITY: Final[float] = 0.15
QUALITY_WEIGHT_CITATION: Final[float] = 0.05
QUALITY_HIGH_THRESHOLD: Final[float] = 0.85
QUALITY_MEDIUM_THRESHOLD: Final[float] = 0.70
QUALITY_LOW_THRESHOLD: Final[float] = 0.50

# Context Tracker Configuration
CONTEXT_MAX_HISTORY_TURNS: Final[int] = 10
CONTEXT_SUMMARY_FREQUENCY: Final[int] = 5
CONTEXT_SUMMARY_MIN_TURNS: Final[int] = 3
CONTEXT_TTL_SECONDS: Final[int] = 3600

# Retry Strategy Configuration
MAX_ROUTE_RETRIES: Final[int] = 1
MAX_ANSWER_RETRIES: Final[int] = 1
MAX_TOTAL_RETRIES: Final[int] = 2
MAX_TOTAL_TIME_MS: Final[int] = 10000
ROUTE_VALIDATOR_TIMEOUT_MS: Final[int] = 500
RETRIEVAL_QUALITY_TIMEOUT_MS: Final[int] = 200
ANSWER_VALIDATOR_TIMEOUT_MS: Final[int] = 1000

# Performance Monitoring Configuration
PERF_THRESHOLD_FAST: Final[int] = 2000
PERF_THRESHOLD_MEDIUM: Final[int] = 5000
PERF_THRESHOLD_SLOW: Final[int] = 8000
ENABLE_PERFORMANCE_LOGGING: Final[bool] = True

# Fallback Configuration
FALLBACK_ROUTE_MAP: Final[dict] = {
    "hybrid": "vector",
    "graph": "vector",
    "react": "vector"
}
ENABLE_AUTO_FALLBACK: Final[bool] = True
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/agents/test_quality_models.py -v
```

Expected: PASS (all tests)

- [ ] **Step 6: Commit**

```bash
git add app/agents/quality_models.py app/agents/quality_config.py tests/agents/test_quality_models.py
git commit -m "feat(quality): add data models and configuration for quality assurance agents"
```

---

### Task 2: Route Validator Agent

**Files:**
- Create: `app/agents/route_validator_agent.py`
- Create: `tests/agents/test_route_validator.py`
- Modify: `app/agents/shared_cache.py` (add route validation caching if needed)

**Interfaces:**
- Consumes: 
  - `RouteDecision` from `app.agents.router_agent`
  - `RouteValidationResult` from `app.agents.quality_models`
  - Config from `app.agents.quality_config`
- Produces:
  - `async def validate_route_decision(query: str, route_decision: RouteDecision, use_cache: bool = True) -> RouteValidationResult`

- [ ] **Step 1: Write test for route validator fast path**

```python
# tests/agents/test_route_validator.py
import pytest
from app.agents.route_validator_agent import validate_route_decision
from app.agents.router_agent import RouteDecision

@pytest.mark.asyncio
async def test_route_validator_high_confidence_fast_pass():
    """High confidence routes should pass quickly without LLM"""
    query = "什么是机器学习？"
    route_decision = RouteDecision(
        route="vector",
        reason="concept_query",
        skill="answer_with_citations",
        agent_class="general",
        confidence=0.92
    )
    
    result = await validate_route_decision(query, route_decision)
    
    assert result.is_valid is True
    assert result.confidence >= 0.85
    assert result.validation_method == "rule_fast"
    assert result.execution_time_ms < 50
    assert result.suggested_alternative is None

@pytest.mark.asyncio
async def test_route_validator_low_confidence_triggers_llm():
    """Low confidence should trigger LLM validation"""
    query = "张三和李四有什么关系"
    route_decision = RouteDecision(
        route="vector",
        reason="uncertain",
        skill="answer_with_citations",
        agent_class="general",
        confidence=0.45
    )
    
    result = await validate_route_decision(query, route_decision)
    
    assert result.validation_method in ["llm", "rule_feature"]
    assert result.execution_time_ms < 600
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/agents/test_route_validator.py::test_route_validator_high_confidence_fast_pass -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'app.agents.route_validator_agent'"

- [ ] **Step 3: Implement route_validator_agent.py with layered validation**

```python
# app/agents/route_validator_agent.py
"""
Route Validator Agent - Validates router decisions with layered approach.
"""

import logging
import time
import re
from typing import Dict, Any

from app.agents.quality_models import RouteValidationResult
from app.agents.quality_config import (
    ROUTE_HIGH_CONFIDENCE_THRESHOLD,
    ROUTE_MEDIUM_CONFIDENCE_THRESHOLD,
    ROUTE_LOW_CONFIDENCE_THRESHOLD,
    ROUTE_VALIDATOR_USE_CACHE,
)
from app.agents.router_agent import RouteDecision
from app.agents.agent_config import VALID_ROUTES, VALID_SKILLS
from app.core.models import get_chat_model

logger = logging.getLogger(__name__)


def _extract_query_features(query: str) -> Dict[str, Any]:
    """Extract features from query for rule-based validation"""
    query_lower = query.lower()
    
    features = {
        "has_relation_keywords": any(kw in query_lower for kw in ["关系", "依赖", "连接", "关联", "relationship", "dependency"]),
        "has_comparison_keywords": any(kw in query_lower for kw in ["对比", "区别", "差异", "vs", "比较", "compare", "difference"]),
        "has_graph_keywords": any(kw in query_lower for kw in ["路径", "拓扑", "网络", "path", "topology", "network"]),
        "has_pdf_keywords": any(kw in query_lower for kw in ["pdf", "文档", "文件", "提取", "document", "file", "extract"]),
        "has_security_keywords": any(kw in query_lower for kw in ["安全", "漏洞", "攻击", "防护", "security", "vulnerability", "attack"]),
        "question_words": [w for w in ["什么", "为什么", "如何", "怎么", "what", "why", "how"] if w in query_lower],
        "has_entities": len(re.findall(r'[一-鿿]{2,}|[A-Z][a-z]+', query)) > 1,
    }
    
    return features


def _rule_based_validation(query: str, route_decision: RouteDecision) -> Dict[str, Any]:
    """Fast rule-based validation"""
    features = _extract_query_features(query)
    issues = []
    confidence = 0.8
    
    # Check route consistency
    if features["has_relation_keywords"] or features["has_graph_keywords"]:
        if route_decision.route not in ["graph", "hybrid"]:
            issues.append("query_has_relation_keywords_but_route_is_not_graph")
            confidence -= 0.3
    
    if features["has_comparison_keywords"]:
        if route_decision.skill != "compare_entities":
            issues.append("comparison_query_but_wrong_skill")
            confidence -= 0.2
    
    if features["has_pdf_keywords"]:
        if route_decision.skill != "pdf_text_reader":
            issues.append("pdf_query_but_wrong_skill")
            confidence -= 0.3
    
    # Check agent class consistency
    if features["has_security_keywords"]:
        if route_decision.agent_class != "cybersecurity":
            issues.append("security_query_but_wrong_agent_class")
            confidence -= 0.2
    
    # Validate route and skill are valid
    if route_decision.route not in VALID_ROUTES:
        issues.append(f"invalid_route_{route_decision.route}")
        confidence -= 0.5
    
    if route_decision.skill not in VALID_SKILLS:
        issues.append(f"invalid_skill_{route_decision.skill}")
        confidence -= 0.4
    
    confidence = max(0.0, min(1.0, confidence))
    
    return {
        "confidence": confidence,
        "reason": "rule_validation" if not issues else f"rule_validation_issues:{','.join(issues)}",
        "warnings": issues
    }


async def _llm_validation(query: str, route_decision: RouteDecision) -> Dict[str, Any]:
    """LLM-based validation for uncertain cases"""
    model = get_chat_model(temperature=0.0)
    
    prompt = f"""Validate this routing decision for quality assurance.

Query: {query}

Routing Decision:
- Route: {route_decision.route}
- Skill: {route_decision.skill}
- Agent Class: {route_decision.agent_class}
- Reason: {route_decision.reason}

Is this routing decision appropriate? If not, suggest an alternative.

Respond in this format:
VALID: yes/no
CONFIDENCE: 0.0-1.0
REASON: brief explanation
ALTERNATIVE_ROUTE: route (if VALID=no)
ALTERNATIVE_SKILL: skill (if VALID=no)
"""
    
    try:
        response = await model.ainvoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        
        is_valid = "yes" in content.lower().split("valid:")[1].split("\n")[0] if "valid:" in content.lower() else True
        
        confidence_match = re.search(r"confidence:\s*([\d.]+)", content.lower())
        confidence = float(confidence_match.group(1)) if confidence_match else 0.7
        
        reason_match = re.search(r"reason:\s*(.+?)(?:\n|$)", content, re.IGNORECASE)
        reason = reason_match.group(1).strip() if reason_match else "llm_validation"
        
        alternative = None
        if not is_valid:
            alt_route_match = re.search(r"alternative_route:\s*(\w+)", content, re.IGNORECASE)
            alt_skill_match = re.search(r"alternative_skill:\s*([\w_]+)", content, re.IGNORECASE)
            
            if alt_route_match or alt_skill_match:
                alternative = {
                    "route": alt_route_match.group(1) if alt_route_match else route_decision.route,
                    "skill": alt_skill_match.group(1) if alt_skill_match else route_decision.skill,
                    "reason": reason
                }
        
        return {
            "is_valid": is_valid,
            "confidence": confidence,
            "reason": reason,
            "alternative": alternative
        }
    
    except Exception as e:
        logger.exception(f"LLM validation failed: {e}")
        return {
            "is_valid": True,
            "confidence": 0.7,
            "reason": f"llm_error:{type(e).__name__}",
            "alternative": None
        }


async def validate_route_decision(
    query: str,
    route_decision: RouteDecision,
    use_cache: bool = True
) -> RouteValidationResult:
    """
    Validate routing decision with layered approach.
    
    Layer 1: High confidence fast pass (>=0.85) - ~5ms
    Layer 2: Rule-based validation (0.6-0.85) - ~30ms
    Layer 3: LLM validation (<0.6) - ~300ms
    
    Args:
        query: Original query text
        route_decision: Router's decision to validate
        use_cache: Whether to use cache
        
    Returns:
        RouteValidationResult with validation outcome
    """
    start_time = time.time()
    
    # Get router confidence if available
    router_confidence = getattr(route_decision, 'confidence', 0.7)
    
    # Layer 1: High confidence fast pass
    if router_confidence >= ROUTE_HIGH_CONFIDENCE_THRESHOLD:
        return RouteValidationResult(
            is_valid=True,
            confidence=router_confidence,
            validation_method="rule_fast",
            validation_reason="high_confidence_fast_pass",
            execution_time_ms=int((time.time() - start_time) * 1000),
            suggested_alternative=None,
            warnings=[]
        )
    
    # Layer 2: Rule-based validation
    rule_result = _rule_based_validation(query, route_decision)
    
    if rule_result["confidence"] >= ROUTE_MEDIUM_CONFIDENCE_THRESHOLD:
        return RouteValidationResult(
            is_valid=True,
            confidence=rule_result["confidence"],
            validation_method="rule_feature",
            validation_reason=rule_result["reason"],
            execution_time_ms=int((time.time() - start_time) * 1000),
            suggested_alternative=None,
            warnings=rule_result.get("warnings", [])
        )
    
    # Layer 3: LLM validation (only for low confidence)
    if router_confidence < ROUTE_LOW_CONFIDENCE_THRESHOLD:
        llm_result = await _llm_validation(query, route_decision)
        
        return RouteValidationResult(
            is_valid=llm_result["is_valid"],
            confidence=llm_result["confidence"],
            validation_method="llm",
            validation_reason=llm_result["reason"],
            execution_time_ms=int((time.time() - start_time) * 1000),
            suggested_alternative=llm_result.get("alternative"),
            warnings=[]
        )
    
    # Default: Medium confidence, pass with warning
    return RouteValidationResult(
        is_valid=True,
        confidence=0.7,
        validation_method="rule_feature",
        validation_reason="medium_confidence_default",
        execution_time_ms=int((time.time() - start_time) * 1000),
        suggested_alternative=None,
        warnings=["medium_confidence"]
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/agents/test_route_validator.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/route_validator_agent.py tests/agents/test_route_validator.py
git commit -m "feat(quality): implement Route Validator Agent with layered validation"
```

---

Due to message length limits, I'll continue with the remaining tasks. The plan will cover:
- Task 3: Retrieval Quality Agent
- Task 4: Answer Validator Agent  
- Task 5: Quality Orchestrator Agent
- Task 6: Context Tracker Agent
- Task 7: Enhanced RAG Workflow
- Task 8: API Integration
- Task 9: Integration Tests
- Task 10: Documentation

Should I continue writing the complete plan to the file?

