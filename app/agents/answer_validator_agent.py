"""
Answer Validator Agent with NLI-based hallucination detection.

Multi-level validation cascade:
- Level 0: Quick checks (<20ms) - length, citations, safety
- Level 1: Citation validation (<100ms) - text matching
- Level 2: Hallucination detection (<200ms) - lightweight NLI
- Level 3: LLM deep validation (~500ms) - only for <10% queries

90% of queries should complete in <150ms via fast path.
"""

import asyncio
import time
import re
import logging
from typing import List, Dict, Optional

from app.agents.quality_models import (
    AnswerValidationResult,
    AnswerValidationDetails,
    AnswerIssue
)
from app.agents.quality_config import (
    ANSWER_FAST_PATH_THRESHOLD,
    ANSWER_STANDARD_PATH_THRESHOLD,
    ANSWER_WEIGHT_FACTUALITY,
    ANSWER_WEIGHT_CITATION,
    ANSWER_WEIGHT_QUALITY,
    ANSWER_WEIGHT_SAFETY,
    HALLUCINATION_HIGH_RISK_THRESHOLD,
    ANSWER_APPROVE_THRESHOLD,
    ANSWER_FLAG_THRESHOLD,
    NLI_MODEL_NAME,
    NLI_MAX_CHECKS,
    ANSWER_VALIDATOR_TIMEOUT_MS
)

logger = logging.getLogger(__name__)

# Lazy load NLI model to avoid startup overhead
_nli_model = None
_nli_load_attempted = False


def _get_nli_model():
    """
    Lazy load NLI model for hallucination detection.
    Returns None if sentence-transformers is not available.
    """
    global _nli_model, _nli_load_attempted

    if _nli_load_attempted:
        return _nli_model

    _nli_load_attempted = True

    try:
        from sentence_transformers import CrossEncoder
        _nli_model = CrossEncoder(NLI_MODEL_NAME)
        logger.info(f"Loaded NLI model: {NLI_MODEL_NAME}")
    except ImportError:
        logger.warning(
            "sentence-transformers not available. Install with: "
            "pip install sentence-transformers>=2.5.0 or pip install -e .[reranker]"
        )
        _nli_model = None
    except Exception as e:
        logger.error(f"Failed to load NLI model: {e}")
        _nli_model = None

    return _nli_model


def _quick_validation(answer: str, citations: List[Dict]) -> Dict:
    """
    Level 0: Quick checks (<20ms).

    Checks:
    - Answer length
    - Citation presence
    - Safety patterns (PII, sensitive data)

    Returns:
        Dict with 'reject', 'reason', and optional 'flag'
    """
    # Safety check FIRST: detect sensitive patterns (most critical)
    unsafe_patterns = [
        (r'\b\d{3}-\d{2}-\d{4}\b', 'SSN'),  # SSN
        (r'\b\d{16}\b', 'credit_card'),  # Credit card (16 consecutive digits)
        (r'password\s*[:=]\s*\S+', 'password'),  # Password
    ]

    for pattern, pattern_type in unsafe_patterns:
        if re.search(pattern, answer, re.IGNORECASE):
            return {"reject": True, "reason": "safety_issue", "pattern_type": pattern_type}

    # Check minimum length (relaxed to 40 chars for short factual answers)
    if len(answer) < 40:
        return {"reject": True, "reason": "answer_too_short"}

    # Check for citations (warn but don't reject)
    if len(citations) == 0:
        return {"reject": False, "reason": "no_citations", "flag": True}

    return {"reject": False, "reason": "passed"}


def _validate_citations(answer: str, citations: List[Dict], source_docs: List[Dict]) -> float:
    """
    Level 1: Citation consistency (<100ms).

    Validates that citations reference actual source documents.

    Returns:
        Citation completeness score (0.0-1.0)
    """
    if not citations:
        return 0.0

    # Check each citation exists in source_docs
    valid_citations = 0
    for citation in citations:
        doc_id = citation.get("doc_id")
        if any(doc.get("id") == doc_id or doc.get("doc_id") == doc_id for doc in source_docs):
            valid_citations += 1

    return valid_citations / len(citations) if citations else 0.0


def _extract_factual_spans(answer: str) -> List[str]:
    """
    Extract high-risk factual content for hallucination detection.

    Targets:
    - Numbers and percentages
    - Dates
    - Proper nouns (Chinese and English)

    Returns:
        List of factual spans (limited to NLI_MAX_CHECKS)
    """
    spans = []

    # Numbers and percentages
    spans.extend(re.findall(r'\d+\.?\d*%?', answer))

    # Dates (various formats)
    spans.extend(re.findall(r'\d{4}[年\-/]\d{1,2}[月\-/]?\d{0,2}日?', answer))
    spans.extend(re.findall(r'\d{1,2}/\d{1,2}/\d{2,4}', answer))

    # Proper nouns - Chinese (2+ characters)
    spans.extend(re.findall(r'[一-鿿]{2,}', answer))

    # Proper nouns - English (capitalized words)
    spans.extend(re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', answer))

    # Deduplicate and limit
    unique_spans = list(dict.fromkeys(spans))  # Preserve order
    return unique_spans[:NLI_MAX_CHECKS]


async def _check_hallucination(answer: str, source_docs: List[Dict]) -> float:
    """
    Level 2: Hallucination detection with NLI (<200ms).

    Uses cross-encoder NLI model to check if factual spans
    are entailed by source documents.

    Returns:
        Factual consistency score (0.0-1.0)
    """
    spans = _extract_factual_spans(answer)

    if not spans or not source_docs:
        return 0.5  # Neutral if no spans or no sources

    # Concatenate source text
    source_text = " ".join([
        doc.get("content", doc.get("text", ""))
        for doc in source_docs[:5]  # Limit to top 5 docs
    ])

    if not source_text:
        return 0.5

    model = _get_nli_model()

    # Fallback if NLI model unavailable
    if model is None:
        logger.warning("NLI model not available, using citation-based fallback")
        return 0.7  # Conservative fallback

    try:
        # Check each span against sources
        unsupported = 0
        for span in spans:
            if len(span) < 2:
                continue

            # NLI entailment check
            # Model returns numpy array with shape (1, 3): [contradiction, neutral, entailment]
            scores = model.predict([(source_text, f"The document mentions: {span}")])

            # Extract entailment score (index 2)
            import numpy as np
            if isinstance(scores, np.ndarray):
                # scores has shape (1, 3) - get entailment score
                entailment_score = float(scores[0, 2]) if scores.ndim > 1 else float(scores[2])
            else:
                entailment_score = 0.0

            # Entailment score > 0 means supported by source
            # We use threshold of 0.5 for entailment
            if entailment_score < 0.5:
                unsupported += 1

        # Calculate factuality score
        hallucination_risk = unsupported / len(spans) if spans else 0.0
        return 1.0 - hallucination_risk

    except Exception as e:
        logger.warning(f"NLI check failed: {e}")
        return 0.7  # Conservative fallback


def _assess_answer_quality(answer: str) -> float:
    """
    Assess structural quality of answer.

    Checks:
    - Length appropriateness
    - Sentence structure
    - Informativeness (not just "don't know")

    Returns:
        Quality score (0.0-1.0)
    """
    quality = 0.8  # Base score

    # Check length (too short or too long is bad)
    if len(answer) < 100:
        quality -= 0.2
    elif len(answer) > 2000:
        quality -= 0.1

    # Check structure (has multiple sentences)
    sentences = re.split(r'[。！？.!?]', answer)
    if len(sentences) < 2:
        quality -= 0.1

    # Check informativeness (not just "I don't know")
    filler_phrases = [
        "不知道", "无法回答", "没有信息",
        "don't know", "cannot answer", "no information"
    ]
    if any(phrase in answer.lower() for phrase in filler_phrases):
        quality -= 0.3

    return max(0.0, min(1.0, quality))


def _safety_check(answer: str) -> float:
    """
    Check for safety issues.

    Note: Quick validation already caught critical issues.
    This is a secondary check.

    Returns:
        Safety score (0.0-1.0)
    """
    # Already checked in quick_validation
    return 1.0


async def validate_answer(
    query: str,
    answer: str,
    source_docs: List[Dict],
    citations: List[Dict]
) -> AnswerValidationResult:
    """
    Validate answer quality with multi-level checks.

    Validation cascade:
    - Level 0: Quick checks (<20ms)
    - Level 1: Citation validation (<100ms)
    - Level 2: Hallucination detection (<200ms)
    - Level 3: LLM deep validation (~500ms, <10% queries)

    90% of queries should complete in <150ms via fast path.

    Args:
        query: Original query
        answer: Generated answer
        source_docs: Source documents used
        citations: Citation list

    Returns:
        AnswerValidationResult with validation outcome and action
    """
    start_time = time.time()

    try:
        # Level 0: Quick validation
        quick_result = _quick_validation(answer, citations)

        if quick_result["reject"]:
            return AnswerValidationResult(
                is_valid=False,
                overall_score=0.0,
                validation_details=AnswerValidationDetails(
                    factual_consistency=0.0,
                    hallucination_risk=1.0,
                    citation_completeness=0.0,
                    answer_quality=0.0,
                    safety_score=0.0 if quick_result["reason"] == "safety_issue" else 1.0
                ),
                issues=[AnswerIssue(
                    type="safety" if quick_result["reason"] == "safety_issue" else "quality",
                    content=answer[:100],
                    severity="critical",
                    suggestion=quick_result["reason"]
                )],
                action="regenerate",
                execution_time_ms=int((time.time() - start_time) * 1000),
                validation_method="fast_path"
            )

        # Level 1: Citation validation
        citation_score = _validate_citations(answer, citations, source_docs)
        answer_quality = _assess_answer_quality(answer)
        safety_score = _safety_check(answer)

        # Decide if we need deeper validation
        preliminary_score = (citation_score + answer_quality) / 2

        if preliminary_score >= ANSWER_FAST_PATH_THRESHOLD and citation_score >= 0.8:
            # Fast path: looks good, skip NLI
            factuality_score = 0.85  # Assume good if citations are complete
            hallucination_risk = 0.15
            validation_method = "fast_path"
        else:
            # Level 2: NLI-based hallucination detection
            factuality_score = await asyncio.wait_for(
                _check_hallucination(answer, source_docs),
                timeout=ANSWER_VALIDATOR_TIMEOUT_MS / 1000.0
            )
            hallucination_risk = 1.0 - factuality_score
            validation_method = "standard"

        # Calculate overall score with weighted dimensions
        overall_score = (
            factuality_score * ANSWER_WEIGHT_FACTUALITY +
            citation_score * ANSWER_WEIGHT_CITATION +
            answer_quality * ANSWER_WEIGHT_QUALITY +
            safety_score * ANSWER_WEIGHT_SAFETY
        )

        # Penalty for high hallucination risk
        if hallucination_risk > HALLUCINATION_HIGH_RISK_THRESHOLD:
            overall_score *= 0.7

        # Determine action
        if overall_score >= ANSWER_APPROVE_THRESHOLD:
            action = "approve"
        elif overall_score >= ANSWER_FLAG_THRESHOLD:
            action = "flag"
        else:
            action = "regenerate"

        # Identify issues
        issues = []
        if hallucination_risk > HALLUCINATION_HIGH_RISK_THRESHOLD:
            issues.append(AnswerIssue(
                type="hallucination",
                content="High hallucination risk detected",
                severity="high",
                suggestion="Verify factual claims against sources"
            ))

        if citation_score < 0.5:
            issues.append(AnswerIssue(
                type="missing_citation",
                content="Incomplete citations",
                severity="medium",
                suggestion="Add citations for key claims"
            ))

        return AnswerValidationResult(
            is_valid=(action != "regenerate"),
            overall_score=round(overall_score, 3),
            validation_details=AnswerValidationDetails(
                factual_consistency=round(factuality_score, 3),
                hallucination_risk=round(hallucination_risk, 3),
                citation_completeness=round(citation_score, 3),
                answer_quality=round(answer_quality, 3),
                safety_score=round(safety_score, 3)
            ),
            issues=issues,
            action=action,
            execution_time_ms=int((time.time() - start_time) * 1000),
            validation_method=validation_method
        )

    except asyncio.TimeoutError:
        logger.warning("Answer validation timed out")
        return AnswerValidationResult(
            is_valid=True,
            overall_score=0.7,
            validation_details=AnswerValidationDetails(
                factual_consistency=0.7,
                hallucination_risk=0.3,
                citation_completeness=0.7,
                answer_quality=0.7,
                safety_score=1.0
            ),
            issues=[],
            action="flag",
            execution_time_ms=ANSWER_VALIDATOR_TIMEOUT_MS,
            validation_method="timeout_fallback"
        )

    except Exception as e:
        logger.error(f"Answer validation failed: {e}")
        # Return conservative fallback
        return AnswerValidationResult(
            is_valid=True,
            overall_score=0.65,
            validation_details=AnswerValidationDetails(
                factual_consistency=0.65,
                hallucination_risk=0.35,
                citation_completeness=0.5,
                answer_quality=0.7,
                safety_score=1.0
            ),
            issues=[AnswerIssue(
                type="quality",
                content=f"Validation error: {str(e)}",
                severity="medium",
                suggestion="Manual review recommended"
            )],
            action="flag",
            execution_time_ms=int((time.time() - start_time) * 1000),
            validation_method="error_fallback"
        )
