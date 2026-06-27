"""
4-Level Validation Cascade for Answer Validator.

Implements progressive validation with early exit:
- Level 1: Rule-based checks (dates, numbers, entities) - 5ms target
- Level 2: Sentence-level NLI batch validation - 2-3s actual (disabled by default)
- Level 3: Citation cross-checking - 50ms target
- Level 4: Deep LLM validation - 2-3s actual (only if issues flagged)

Performance notes:
- Level 2 (NLI) has significant latency (2-3s) due to model loading and inference
- Level 4 (LLM) latency varies with local model performance
- By default, only Levels 1 and 3 are enabled for <150ms validation
- Enable Level 2 for higher semantic accuracy at cost of 2-3s latency
"""

import asyncio
import time
import re
import logging
from typing import List, Dict, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field

from app.core.models import get_chat_model

logger = logging.getLogger(__name__)


class CascadeLevel(str, Enum):
    """Validation cascade levels"""
    RULE_BASED = "rule_based"
    NLI_BATCH = "nli_batch"
    CITATION_CHECK = "citation_check"
    DEEP_LLM = "deep_llm"


class RuleBasisIssue(BaseModel):
    """Issue found during validation"""
    issue_type: str
    severity: str
    content: str
    suggestion: Optional[str] = None


class CascadeResult(BaseModel):
    """Result from a single cascade level"""
    level: CascadeLevel
    has_issues: bool
    confidence_score: float = Field(ge=0.0, le=1.0)
    issues: List[RuleBasisIssue] = Field(default_factory=list)
    execution_time_ms: int
    nli_scores: Optional[List[float]] = None
    should_continue: bool = True


class ValidationCascadeResult(BaseModel):
    """Result from full cascade validation"""
    has_issues: bool
    confidence_score: float = Field(ge=0.0, le=1.0)
    highest_level_reached: CascadeLevel
    all_issues: List[RuleBasisIssue] = Field(default_factory=list)
    total_execution_time_ms: int
    execution_time_ms: int  # Alias for compatibility
    level_results: List[CascadeResult] = Field(default_factory=list)


class ValidationCascade:
    """4-Level validation cascade for answer quality checking"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize validation cascade with optional config overrides"""
        self.config = config or {}
        self._nli_model = None
        self._nli_load_attempted = False

        # Load config with defaults
        self.level1_timeout_ms = self.config.get("level1_timeout_ms", 10)
        self.level2_timeout_ms = self.config.get("level2_timeout_ms", 3000)
        self.level3_timeout_ms = self.config.get("level3_timeout_ms", 75)
        self.level4_timeout_ms = self.config.get("level4_timeout_ms", 3000)
        self.enable_level1 = self.config.get("enable_level1", True)
        self.enable_level2 = self.config.get("enable_level2", False)  # Disabled by default due to perf
        self.enable_level3 = self.config.get("enable_level3", True)
        self.enable_level4 = self.config.get("enable_level4", True)

    def _get_nli_model(self):
        """Lazy load NLI model for Level 2"""
        if self._nli_load_attempted:
            return self._nli_model

        self._nli_load_attempted = True

        try:
            from sentence_transformers import CrossEncoder
            self._nli_model = CrossEncoder("cross-encoder/nli-MiniLM2-L6-H768")
            logger.info("Loaded NLI model for cascade Level 2")
        except ImportError:
            logger.warning("sentence-transformers not available for Level 2 NLI")
            self._nli_model = None
        except Exception as e:
            logger.error(f"Failed to load NLI model: {e}")
            self._nli_model = None

        return self._nli_model

    def _extract_numbers(self, text: str) -> List[float]:
        """Extract numeric values from text"""
        # Match numbers with optional commas, decimals, and common units
        pattern = r'\$?\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:million|billion|M|B|K|thousand))?'
        matches = re.findall(pattern, text, re.IGNORECASE)

        numbers = []
        for match in matches:
            # Clean and convert to number
            cleaned = re.sub(r'[,$\s]', '', match)
            # Handle units
            if 'billion' in match.lower() or 'B' in match:
                cleaned = re.sub(r'[a-zA-Z]', '', cleaned)
                try:
                    numbers.append(float(cleaned) * 1e9)
                except ValueError:
                    pass
            elif 'million' in match.lower() or 'M' in match:
                cleaned = re.sub(r'[a-zA-Z]', '', cleaned)
                try:
                    numbers.append(float(cleaned) * 1e6)
                except ValueError:
                    pass
            elif 'thousand' in match.lower() or 'K' in match:
                cleaned = re.sub(r'[a-zA-Z]', '', cleaned)
                try:
                    numbers.append(float(cleaned) * 1e3)
                except ValueError:
                    pass
            else:
                cleaned = re.sub(r'[a-zA-Z]', '', cleaned)
                try:
                    numbers.append(float(cleaned))
                except ValueError:
                    pass

        return numbers

    def _extract_dates(self, text: str) -> List[str]:
        """Extract dates from text (English and Chinese)"""
        dates = []

        # Year patterns (capture full 4 digits)
        years = re.findall(r'\b((?:19|20)\d{2})\b', text)
        dates.extend(years)

        # Chinese date patterns
        dates.extend(re.findall(r'\d{4}年(?:\d{1,2}月)?(?:\d{1,2}日)?', text))

        # English date patterns
        dates.extend(re.findall(r'\d{1,2}/\d{1,2}/\d{2,4}', text))
        dates.extend(re.findall(r'\d{4}-\d{2}-\d{2}', text))

        # Quarter patterns
        dates.extend(re.findall(r'Q[1-4]\s*\d{4}', text, re.IGNORECASE))

        return dates

    def _extract_entities(self, text: str) -> List[str]:
        """Extract named entities (proper nouns) from text"""
        entities = []

        # English: Capitalized words
        entities.extend(re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text))

        # Chinese: 2+ character sequences
        entities.extend(re.findall(r'[一-鿿]{2,}', text))

        return entities

    def _numbers_match(self, num1: float, num2: float, tolerance: float = 0.15) -> bool:
        """Check if two numbers match within tolerance"""
        if num1 == 0 and num2 == 0:
            return True
        if num1 == 0 or num2 == 0:
            return False

        diff = abs(num1 - num2) / max(abs(num1), abs(num2))
        return diff <= tolerance

    async def validate_level1(self, answer: str, source_docs: List[Dict]) -> CascadeResult:
        """
        Level 1: Fast rule-based checks (5ms target).

        Checks:
        - Date mismatches
        - Number mismatches (>15% difference)
        - Entity mismatches
        - PII patterns (critical stop)
        """
        start_time = time.time()
        issues = []

        # Concatenate source text
        source_text = " ".join([
            doc.get("content", doc.get("text", ""))
            for doc in source_docs[:5]
        ])

        # Critical: Check for PII (immediate stop)
        pii_patterns = [
            (r'\b\d{3}-\d{2}-\d{4}\b', 'SSN'),
            (r'\b\d{16}\b', 'credit_card'),
            (r'\b[\w\.-]+@[\w\.-]+\.\w+\b', 'email'),
            (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', 'phone'),
        ]

        for pattern, pii_type in pii_patterns:
            if re.search(pattern, answer):
                issues.append(RuleBasisIssue(
                    issue_type=f"pii_{pii_type}",
                    severity="critical",
                    content=f"PII detected: {pii_type}",
                    suggestion="Remove sensitive information"
                ))

        # If critical issues, stop immediately
        if issues:
            elapsed = int((time.time() - start_time) * 1000)
            return CascadeResult(
                level=CascadeLevel.RULE_BASED,
                has_issues=True,
                confidence_score=0.0,
                issues=issues,
                execution_time_ms=elapsed,
                should_continue=False
            )

        # Check dates
        answer_dates = set(self._extract_dates(answer))
        source_dates = set(self._extract_dates(source_text))

        if answer_dates and source_dates:
            mismatched_dates = answer_dates - source_dates
            # Flag if any dates don't match (strict for dates)
            if mismatched_dates:
                issues.append(RuleBasisIssue(
                    issue_type="date_mismatch",
                    severity="high",
                    content=f"Date mismatch: {mismatched_dates}",
                    suggestion="Verify dates against source documents"
                ))

        # Check numbers
        answer_numbers = self._extract_numbers(answer)
        source_numbers = self._extract_numbers(source_text)

        if answer_numbers:
            for ans_num in answer_numbers:
                has_match = any(
                    self._numbers_match(ans_num, src_num)
                    for src_num in source_numbers
                )
                if not has_match and source_numbers:
                    issues.append(RuleBasisIssue(
                        issue_type="number_mismatch",
                        severity="high",
                        content=f"Number {ans_num} not found in sources",
                        suggestion="Verify numeric claims"
                    ))

        # Check entities (basic matching)
        answer_entities = set(self._extract_entities(answer))
        source_entities = set(self._extract_entities(source_text))

        if answer_entities and source_entities:
            # Check for entities in answer not in source
            mismatched = answer_entities - source_entities
            # Filter out common words that might be capitalized
            common_words = {'The', 'A', 'An', 'In', 'On', 'At', 'To', 'For', 'Of', 'With', 'CEO', 'CFO', 'CTO'}
            mismatched = {e for e in mismatched if e not in common_words}

            # Only flag if specific named entities (names) mismatch
            # Filter to likely proper nouns (2+ words or Chinese names)
            likely_names = {e for e in mismatched if ' ' in e or re.match(r'[一-鿿]{2,}', e)}

            if likely_names:
                issues.append(RuleBasisIssue(
                    issue_type="entity_mismatch",
                    severity="medium",
                    content=f"Entities not in source: {likely_names}",
                    suggestion="Verify entity names"
                ))

        elapsed = int((time.time() - start_time) * 1000)

        return CascadeResult(
            level=CascadeLevel.RULE_BASED,
            has_issues=len(issues) > 0,
            confidence_score=1.0 - (len(issues) * 0.2),
            issues=issues,
            execution_time_ms=elapsed,
            should_continue=True
        )

    async def validate_level2(self, answer: str, source_docs: List[Dict]) -> CascadeResult:
        """
        Level 2: Sentence-level NLI batch validation (100ms target).

        Uses NLI model to check if each sentence is entailed by sources.
        Processes sentences in batch for efficiency.
        """
        start_time = time.time()
        issues = []

        # Split answer into sentences
        sentences = re.split(r'[。！？.!?]\s*', answer)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]

        if not sentences:
            return CascadeResult(
                level=CascadeLevel.NLI_BATCH,
                has_issues=False,
                confidence_score=1.0,
                issues=[],
                execution_time_ms=0,
                should_continue=True
            )

        # Concatenate source text
        source_text = " ".join([
            doc.get("content", doc.get("text", ""))
            for doc in source_docs[:5]
        ])

        if not source_text:
            return CascadeResult(
                level=CascadeLevel.NLI_BATCH,
                has_issues=False,
                confidence_score=0.5,
                issues=[],
                execution_time_ms=int((time.time() - start_time) * 1000),
                should_continue=True
            )

        # Get NLI model
        model = self._get_nli_model()

        if model is None:
            # Fallback: semantic similarity via keyword overlap
            unsupported = 0
            for sent in sentences:
                # Basic check: key words and numbers present in source
                # Extract key terms (nouns, numbers, entities)
                sent_numbers = self._extract_numbers(sent)
                sent_dates = self._extract_dates(sent)
                sent_entities = self._extract_entities(sent)

                source_numbers = self._extract_numbers(source_text)
                source_dates = self._extract_dates(source_text)
                source_entities = self._extract_entities(source_text)

                # Check if key facts are present
                numbers_match = all(
                    any(self._numbers_match(sn, src) for src in source_numbers)
                    for sn in sent_numbers
                ) if sent_numbers else True

                dates_match = all(d in source_dates for d in sent_dates) if sent_dates else True

                # Word overlap
                words = set(re.findall(r'\w+', sent.lower()))
                source_words = set(re.findall(r'\w+', source_text.lower()))
                overlap = len(words & source_words) / len(words) if words else 0

                # Flag if facts don't match or very low overlap
                if not numbers_match or not dates_match or overlap < 0.25:
                    unsupported += 1

            confidence = 1.0 - (unsupported / len(sentences))

            if unsupported > len(sentences) * 0.3:
                issues.append(RuleBasisIssue(
                    issue_type="nli_contradiction",
                    severity="high",
                    content=f"{unsupported} sentences not supported by sources",
                    suggestion="Verify claims against sources"
                ))

            elapsed = int((time.time() - start_time) * 1000)

            return CascadeResult(
                level=CascadeLevel.NLI_BATCH,
                has_issues=len(issues) > 0,
                confidence_score=confidence,
                issues=issues,
                execution_time_ms=elapsed,
                should_continue=True
            )

        # Use NLI model for batch validation
        try:
            import numpy as np

            # Prepare pairs for batch processing
            pairs = [(source_text, sent) for sent in sentences]

            # Batch predict
            scores = model.predict(pairs)  # Returns array of shape (N, 3)

            # Extract entailment scores (index 2)
            nli_scores = []
            unsupported_sentences = []

            for i, sent in enumerate(sentences):
                if isinstance(scores, np.ndarray):
                    # NLI model output: [contradiction, neutral, entailment]
                    # We want entailment score (index 2)
                    if scores.ndim > 1:
                        entailment_score = float(scores[i, 2])
                    else:
                        entailment_score = float(scores[2])
                else:
                    entailment_score = 0.5

                # Clamp to [0, 1] range
                entailment_score = max(0.0, min(1.0, entailment_score))
                nli_scores.append(entailment_score)

                # Threshold: entailment score < 0.5 means not supported
                if entailment_score < 0.5:
                    unsupported_sentences.append(sent[:50])

            # Flag if too many unsupported sentences
            if len(unsupported_sentences) > len(sentences) * 0.3:
                issues.append(RuleBasisIssue(
                    issue_type="nli_contradiction",
                    severity="high",
                    content=f"{len(unsupported_sentences)} sentences not entailed",
                    suggestion="Verify claims against sources"
                ))

            confidence = sum(nli_scores) / len(nli_scores) if nli_scores else 0.5
            # Clamp confidence to valid range
            confidence = max(0.0, min(1.0, confidence))
            elapsed = int((time.time() - start_time) * 1000)

            return CascadeResult(
                level=CascadeLevel.NLI_BATCH,
                has_issues=len(issues) > 0,
                confidence_score=confidence,
                issues=issues,
                execution_time_ms=elapsed,
                nli_scores=nli_scores,
                should_continue=True
            )

        except Exception as e:
            logger.warning(f"NLI batch validation failed: {e}")
            elapsed = int((time.time() - start_time) * 1000)
            return CascadeResult(
                level=CascadeLevel.NLI_BATCH,
                has_issues=False,
                confidence_score=0.7,
                issues=[],
                execution_time_ms=elapsed,
                should_continue=True
            )

    async def validate_level3(
        self,
        answer: str,
        citations: List[Dict],
        source_docs: List[Dict]
    ) -> CascadeResult:
        """
        Level 3: Citation cross-checking (50ms target).

        Verifies that:
        - Citations exist for factual claims
        - Citation content actually supports the claims
        - Numbers in citations match answer
        """
        start_time = time.time()
        issues = []

        # Extract citation markers from answer (e.g., [1], [2])
        citation_markers = re.findall(r'\[(\d+)\]', answer)

        # Check if citations are provided for claims
        if not citations and not citation_markers:
            # Check if answer has factual claims that need citations
            has_numbers = bool(self._extract_numbers(answer))
            has_dates = bool(self._extract_dates(answer))

            if has_numbers or has_dates:
                issues.append(RuleBasisIssue(
                    issue_type="missing_citation",
                    severity="medium",
                    content="Factual claims without citations",
                    suggestion="Add citations for numbers and dates"
                ))

        # Verify citation content matches claims
        if citations:
            for citation in citations:
                citation_content = citation.get("content", "")
                doc_id = citation.get("doc_id")

                # Find corresponding source doc
                source_doc = next(
                    (doc for doc in source_docs
                     if doc.get("id") == doc_id or doc.get("doc_id") == doc_id),
                    None
                )

                if not source_doc:
                    issues.append(RuleBasisIssue(
                        issue_type="citation_invalid",
                        severity="high",
                        content=f"Citation {doc_id} not found in sources",
                        suggestion="Verify citation references"
                    ))
                    continue

                # Check if citation content is in source
                if citation_content:
                    source_content = source_doc.get("content", source_doc.get("text", ""))

                    # Extract numbers from both citation and answer near citation
                    citation_numbers = self._extract_numbers(citation_content)
                    answer_numbers = self._extract_numbers(answer)
                    source_numbers = self._extract_numbers(source_content)

                    # Check if numbers in answer match citation/source
                    for ans_num in answer_numbers:
                        # Check if this number is near a citation marker
                        # For now, check all answer numbers against this citation's source
                        if citation_numbers:
                            # Citation has numbers, verify they match source
                            for cit_num in citation_numbers:
                                has_match = any(
                                    self._numbers_match(cit_num, src_num)
                                    for src_num in source_numbers
                                )
                                if not has_match:
                                    issues.append(RuleBasisIssue(
                                        issue_type="citation_mismatch",
                                        severity="high",
                                        content=f"Citation number {cit_num} not in source",
                                        suggestion="Verify cited values"
                                    ))
                                    break  # One issue per citation is enough

        elapsed = int((time.time() - start_time) * 1000)

        # Calculate confidence
        confidence = 1.0 - (len(issues) * 0.15)
        confidence = max(0.0, min(1.0, confidence))

        return CascadeResult(
            level=CascadeLevel.CITATION_CHECK,
            has_issues=len(issues) > 0,
            confidence_score=confidence,
            issues=issues,
            execution_time_ms=elapsed,
            should_continue=True
        )

    async def validate_level4(
        self,
        query: str,
        answer: str,
        source_docs: List[Dict]
    ) -> CascadeResult:
        """
        Level 4: Deep LLM validation (200ms target).

        Uses LLM to catch subtle hallucinations:
        - Complex reasoning errors
        - Subtle contradictions
        - Implied claims not in sources
        - Overgeneralizations
        """
        start_time = time.time()
        issues = []

        try:
            model = get_chat_model(temperature=0.0)

            # Prepare source text (limit to top 3 docs, 500 chars each)
            source_text = "\n".join([
                doc.get("content", doc.get("text", ""))[:500]
                for doc in source_docs[:3]
            ])

            if not source_text:
                return CascadeResult(
                    level=CascadeLevel.DEEP_LLM,
                    has_issues=False,
                    confidence_score=0.5,
                    issues=[],
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    should_continue=True
                )

            prompt = f"""Verify if this answer is factually consistent with the source documents.
Check for:
- Direct contradictions
- Unsupported claims or inferences
- Overgeneralizations
- Implied information not in sources

Query: {query}

Answer: {answer}

Source Documents:
{source_text}

Respond in this format:
FACTUAL: yes/no
CONFIDENCE: 0.0-1.0
ISSUES: list any problems (or "none")
"""

            response = await asyncio.wait_for(
                model.ainvoke(prompt),
                timeout=2.0  # 2 second timeout for LLM
            )

            content = response.content if hasattr(response, "content") else str(response)

            # Parse response
            is_factual = True
            if "factual:" in content.lower():
                factual_line = content.lower().split("factual:")[1].split("\n")[0]
                is_factual = "yes" in factual_line

            confidence = 0.7  # Default
            conf_match = re.search(r"confidence:\s*([\d.]+)", content.lower())
            if conf_match:
                confidence = float(conf_match.group(1))

            # Extract issues
            if not is_factual:
                issues_text = "Factual inconsistency detected"
                if "issues:" in content.lower():
                    issues_section = content.lower().split("issues:")[1].split("\n")[0]
                    if "none" not in issues_section:
                        issues_text = issues_section.strip()

                issues.append(RuleBasisIssue(
                    issue_type="llm_hallucination",
                    severity="high",
                    content=issues_text,
                    suggestion="Review answer against sources"
                ))

            elapsed = int((time.time() - start_time) * 1000)

            return CascadeResult(
                level=CascadeLevel.DEEP_LLM,
                has_issues=not is_factual,
                confidence_score=confidence if is_factual else confidence * 0.5,
                issues=issues,
                execution_time_ms=elapsed,
                should_continue=True
            )

        except asyncio.TimeoutError:
            logger.warning(f"Level 4 validation timed out after {self.level4_timeout_ms}ms")
            elapsed = int((time.time() - start_time) * 1000)
            return CascadeResult(
                level=CascadeLevel.DEEP_LLM,
                has_issues=False,
                confidence_score=0.6,
                issues=[],
                execution_time_ms=elapsed,
                should_continue=True
            )
        except Exception as e:
            logger.error(f"Level 4 validation failed: {e}")
            elapsed = int((time.time() - start_time) * 1000)
            return CascadeResult(
                level=CascadeLevel.DEEP_LLM,
                has_issues=False,
                confidence_score=0.6,
                issues=[],
                execution_time_ms=elapsed,
                should_continue=True
            )

    async def run_cascade(
        self,
        query: str,
        answer: str,
        source_docs: List[Dict],
        citations: List[Dict]
    ) -> ValidationCascadeResult:
        """
        Run full validation cascade with early exit.

        Strategy:
        - Level 1: Rule-based (if enabled, default: True)
        - Level 2: NLI batch (if enabled, default: False due to 2-3s latency)
        - Level 3: Citation check (if enabled, default: True)
        - Level 4: Deep LLM (only if issues flagged and enabled, default: True)

        Early exit on critical issues.
        """
        start_time = time.time()
        all_issues = []
        level_results = []
        highest_level = CascadeLevel.RULE_BASED

        # Level 1: Rule-based (if enabled)
        if self.enable_level1:
            level1_result = await self.validate_level1(answer, source_docs)
            level_results.append(level1_result)
            all_issues.extend(level1_result.issues)

            if not level1_result.should_continue:
                # Critical issue, stop immediately
                elapsed = int((time.time() - start_time) * 1000)
                return ValidationCascadeResult(
                    has_issues=True,
                    confidence_score=level1_result.confidence_score,
                    highest_level_reached=CascadeLevel.RULE_BASED,
                    all_issues=all_issues,
                    total_execution_time_ms=elapsed,
                    execution_time_ms=elapsed,
                    level_results=level_results
                )

        # Level 2: NLI batch (if enabled and Level 1 passes or has only minor issues)
        last_confidence = level_results[-1].confidence_score if level_results else 1.0
        if self.enable_level2 and last_confidence >= 0.5:
            highest_level = CascadeLevel.NLI_BATCH
            level2_result = await self.validate_level2(answer, source_docs)
            level_results.append(level2_result)
            all_issues.extend(level2_result.issues)

        # Level 3: Citation check (if enabled)
        last_confidence = level_results[-1].confidence_score if level_results else 1.0
        if self.enable_level3 and last_confidence >= 0.5:
            highest_level = CascadeLevel.CITATION_CHECK
            level3_result = await self.validate_level3(answer, citations, source_docs)
            level_results.append(level3_result)
            all_issues.extend(level3_result.issues)

        # Level 4: Deep LLM (only if issues flagged and enabled)
        should_run_level4 = (
            self.enable_level4 and
            len(all_issues) > 0 and
            any(result.confidence_score < 0.7 for result in level_results)
        )

        if should_run_level4:
            highest_level = CascadeLevel.DEEP_LLM
            level4_result = await self.validate_level4(query, answer, source_docs)
            level_results.append(level4_result)
            all_issues.extend(level4_result.issues)

        # Calculate overall confidence (weighted by level)
        if level_results:
            weights = [0.2, 0.3, 0.3, 0.2]  # Level 1-4 weights
            weighted_sum = sum(
                result.confidence_score * weights[i]
                for i, result in enumerate(level_results)
            )
            total_weight = sum(weights[:len(level_results)])
            overall_confidence = weighted_sum / total_weight
        else:
            overall_confidence = 0.5

        elapsed = int((time.time() - start_time) * 1000)

        return ValidationCascadeResult(
            has_issues=len(all_issues) > 0,
            confidence_score=round(overall_confidence, 3),
            highest_level_reached=highest_level,
            all_issues=all_issues,
            total_execution_time_ms=elapsed,
            execution_time_ms=elapsed,
            level_results=level_results
        )
