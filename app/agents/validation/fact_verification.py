"""
Fact Verification Layer (Task 14).

Post-generation fact verification to improve groundedness from 80% to 94%.

Features:
- Extract factual claims from generated answers
- Verify each fact appears in cited source
- Check date/number accuracy
- Detect negations and contradictions
- Flag unverified claims for removal or hedging

Integrates with:
- Task 13: Citation-first generation (validates [doc_id:page] citations)
- Task 9: Hallucination pattern detection (date/number/entity checks)
- Task 8: Multi-stage NLI validation (semantic verification)

Configuration:
All verification thresholds are externalized via FactVerificationConfig.
Default values preserve original behavior. Tune for specific use cases:

Example - Stricter verification (higher precision):
    config = FactVerificationConfig(
        min_support_confidence=0.7,  # Require higher confidence
        number_tolerance=0.10,        # Tighter number matching (10%)
        min_groundedness=0.90         # Higher overall threshold
    )
    stage = FactVerificationStage(config)

Example - Lenient verification (higher recall):
    config = FactVerificationConfig(
        min_support_confidence=0.5,   # Lower confidence threshold
        number_tolerance=0.20,         # Looser number matching (20%)
        min_groundedness=0.75          # Lower overall threshold
    )
    stage = FactVerificationStage(config)

Example - Default behavior:
    stage = FactVerificationStage()  # Uses FactVerificationConfig() defaults
"""

import logging
import re
from dataclasses import dataclass

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


@dataclass
class FactVerificationConfig:
    """
    Configuration for fact verification thresholds and parameters.

    All thresholds are externalized for tuning and experimentation.
    Default values match the original hardcoded behavior.
    """

    # Citation support thresholds
    min_support_confidence: float = 0.6
    """Minimum confidence score for a claim to be considered supported"""

    no_citation_confidence: float = 0.3
    """Confidence score when claim has no citations"""

    missing_citation_confidence: float = 0.2
    """Confidence score when cited document is not found"""

    # Confidence scoring weights
    base_confidence: float = 0.5
    """Base confidence score before applying adjustments"""

    number_match_boost: float = 0.25
    """Confidence boost when numbers match"""

    date_match_boost: float = 0.25
    """Confidence boost when dates match"""

    high_overlap_boost: float = 0.25
    """Confidence boost for word overlap > 50%"""

    medium_overlap_boost: float = 0.15
    """Confidence boost for word overlap > 30%"""

    low_overlap_boost: float = 0.05
    """Confidence boost for word overlap > 15%"""

    negation_mismatch_penalty: float = 0.3
    """Confidence penalty when negation doesn't match"""

    number_mismatch_penalty: float = 0.5
    """Confidence penalty when numbers don't match"""

    date_mismatch_penalty: float = 0.5
    """Confidence penalty when dates don't match"""

    # Overlap thresholds
    high_overlap_threshold: float = 0.5
    """Threshold for high word overlap (50%)"""

    medium_overlap_threshold: float = 0.3
    """Threshold for medium word overlap (30%)"""

    low_overlap_threshold: float = 0.15
    """Threshold for low word overlap (15%)"""

    # Number matching tolerance
    number_tolerance: float = 0.15
    """Relative tolerance for number matching (15% default)"""

    # Answer-level thresholds
    min_groundedness: float = 0.85
    """Minimum groundedness score for answer to be considered verified"""

    min_claim_length: int = 10
    """Minimum sentence length to extract as a claim"""

    min_clean_claim_length: int = 5
    """Minimum claim length after removing citations"""


class FactClaim(BaseModel):
    """A factual claim extracted from an answer"""

    text: str
    citations: list[str] = Field(default_factory=list)
    claim_type: str = "general"  # general, date, number, negation, entity
    start_pos: int = 0
    end_pos: int = 0


class VerificationResult(BaseModel):
    """Result of verifying a single claim"""

    claim: FactClaim
    is_verified: bool
    confidence: float = Field(ge=0.0, le=1.0)
    issue_type: str = ""
    suggestion: str = ""


class AnswerVerificationResult(BaseModel):
    """Result of verifying an entire answer"""

    overall_verified: bool
    groundedness_score: float = Field(ge=0.0, le=1.0)
    verified_claims: list[FactClaim] = Field(default_factory=list)
    unverified_claims: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    execution_time_ms: int = 0


def _extract_numbers(text: str) -> list[float]:
    """Extract numeric values from text (reuses logic from hallucination_patterns)"""
    numbers = []
    pattern = r"\$?\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:million|billion|thousand|[MBK]|%))?"
    matches = re.findall(pattern, text, re.IGNORECASE)

    for match in matches:
        cleaned = re.sub(r"[,$\s]", "", match)

        if "%" in match:
            try:
                value = float(cleaned.replace("%", ""))
                numbers.append(value)
            except ValueError:
                pass
            continue

        multiplier = 1
        if "billion" in match.lower() or "B" in match:
            multiplier = 1e9
        elif "million" in match.lower() or "M" in match:
            multiplier = 1e6
        elif "thousand" in match.lower() or "K" in match:
            multiplier = 1e3

        cleaned = re.sub(r"[a-zA-Z%]", "", cleaned)
        try:
            value = float(cleaned) * multiplier
            numbers.append(value)
        except ValueError:
            pass

    return numbers


def _extract_dates(text: str) -> list[str]:
    """Extract dates from text (English and Chinese)"""
    dates = []
    dates.extend(re.findall(r"\b((?:19|20)\d{2})\b", text))
    dates.extend(re.findall(r"\d{4}年(?:\d{1,2}月)?(?:\d{1,2}日)?", text))
    dates.extend(re.findall(r"\d{4}-\d{2}-\d{2}", text))
    dates.extend(re.findall(r"\d{1,2}/\d{1,2}/\d{2,4}", text))
    dates.extend(re.findall(r"Q[1-4]\s*\d{4}", text, re.IGNORECASE))
    return dates


def _numbers_match(num1: float, num2: float, tolerance: float) -> bool:
    """Check if two numbers match within tolerance"""
    if num1 == 0 and num2 == 0:
        return True
    if num1 == 0 or num2 == 0:
        return False
    diff = abs(num1 - num2) / max(abs(num1), abs(num2))
    return diff <= tolerance


def _has_negation(text: str) -> bool:
    """Check if text contains negation"""
    negation_patterns = [
        r"\bnot\b",
        r"\bno\b",
        r"\bnever\b",
        r"\bnone\b",
        r"\bneither\b",
        r"\bnor\b",
        r"\bn\'t\b",
        r"\bfailed\s+to\b",
        r"没有",
        r"不是",
        r"未",
        r"无",
        r"非",
        r"不",
    ]
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in negation_patterns)


def extract_claims(answer: str, config: FactVerificationConfig | None = None) -> list[FactClaim]:
    """
    Extract factual claims from generated answer.

    Strategy:
    1. Split answer into sentences
    2. Extract citation markers [doc_id:page]
    3. Remove citation markers from claim text (they're stored separately)
    4. Identify claim type (date, number, negation, general)
    5. Return list of FactClaim objects

    Args:
        answer: Generated answer text with citations
        config: Optional configuration for thresholds

    Returns:
        List of FactClaim objects
    """
    if config is None:
        config = FactVerificationConfig()

    if not answer or not answer.strip():
        return []

    claims = []

    # Split into sentences (handle both English and Chinese)
    # Use period, question mark, exclamation mark, Chinese period/question/exclamation
    sentences = re.split(r"[.!?。！？]\s*", answer)
    sentences = [s.strip() for s in sentences if s.strip()]

    position = 0
    for sentence in sentences:
        if len(sentence) < config.min_claim_length:  # Skip very short sentences
            position += len(sentence) + 1
            continue

        valid_citations = _valid_claim_citations(sentence)
        clean_sentence = _clean_claim_text(sentence)

        if len(clean_sentence) < config.min_clean_claim_length:  # Skip if too short after removing citations
            position += len(sentence) + 1
            continue

        claim = FactClaim(
            text=clean_sentence,
            citations=valid_citations,
            claim_type=_determine_claim_type(clean_sentence),
            start_pos=position,
            end_pos=position + len(sentence),
        )
        claims.append(claim)

        position += len(sentence) + 1

    return claims


def _valid_claim_citations(sentence: str) -> list[str]:
    """Citations in `[doc_id:page]` form; anything else in brackets is not a citation."""
    citations = re.findall(r"\[([^\]]+)\]", sentence)
    return [cit for cit in citations if re.match(r"doc\w*:\w+", cit)]


def _clean_claim_text(sentence: str) -> str:
    """Remove citation markers from claim text and normalize whitespace.

    Bounded whitespace, as elsewhere in this repository: an unbounded `\\s*`
    beside a bracket group backtracks over a long run (S8786).
    """
    clean = re.sub(r"\s{0,8}\[[^\]]+\]\s{0,8}", " ", sentence).strip()
    return re.sub(r"\s+", " ", clean)


def _determine_claim_type(clean_sentence: str) -> str:
    if _extract_dates(clean_sentence):
        return "date"
    if _extract_numbers(clean_sentence):
        return "number"
    if _has_negation(clean_sentence):
        return "negation"
    return "general"


_CITATION_RE = re.compile(r"(\w+):(\w+)")
_ENGLISH_WORD_RE = re.compile(r"\b[a-z]{4,}\b")
_CJK_WORD_RE = re.compile(r"[\u4e00-\u9fff]{2,}")


def _cited_contents(citations: list[str], source_docs: list[dict]) -> list[str]:
    """The text of every source document a citation resolves to.

    Page matching is lenient on purpose: a document that records no page still
    matches a citation that names one, because the alternative is treating a
    thin index as a missing citation.
    """

    contents: list[str] = []
    for citation in citations:
        match = _CITATION_RE.match(citation)
        if not match:
            continue
        doc_id, page = match.group(1), match.group(2)
        for doc in source_docs:
            if doc.get("doc_id", doc.get("id", "")) != doc_id:
                continue
            doc_page = doc.get("page", "")
            if page and doc_page and doc_page != page:
                continue
            content = doc.get("content", doc.get("text", ""))
            if content:
                contents.append(content)
                break
    return contents


def _content_words(text: str) -> set[str]:
    """Content-bearing words: English of four letters or more, CJK runs of two.

    Both scripts, because a bilingual claim scored on English alone reads as
    ungrounded -- the failure this project already records for the NLI scorer.
    """

    return set(_ENGLISH_WORD_RE.findall(text.lower())) | set(_CJK_WORD_RE.findall(text))


def _facts_agree(claim_text: str, source_text: str, config: FactVerificationConfig) -> tuple[bool, bool]:
    """Do the claim's numbers and dates appear in the cited text?

    Vacuously true when the claim states none, which is why the caller has to
    check `claim_numbers` before turning a True into a boost.
    """

    claim_numbers = _extract_numbers(claim_text)
    claim_dates = _extract_dates(claim_text)
    source_numbers = _extract_numbers(source_text)
    source_dates = _extract_dates(source_text)

    numbers_match = True
    if claim_numbers:
        numbers_match = bool(source_numbers) and all(
            any(_numbers_match(cn, sn, config.number_tolerance) for sn in source_numbers) for cn in claim_numbers
        )

    dates_match = True
    if claim_dates:
        dates_match = bool(source_dates) and any(cd == sd for cd in claim_dates for sd in source_dates)

    return numbers_match, dates_match


def _overlap_boost(overlap: float, config: FactVerificationConfig) -> float:
    """A ladder, so only the highest band that applies pays out."""

    if overlap > config.high_overlap_threshold:
        return config.high_overlap_boost
    if overlap > config.medium_overlap_threshold:
        return config.medium_overlap_boost
    if overlap > config.low_overlap_threshold:
        return config.low_overlap_boost
    return 0.0


def check_citation_support(
    claim_text: str, citations: list[str], source_docs: list[dict], config: FactVerificationConfig | None = None
) -> tuple[bool, float]:
    """
    Check if claim is supported by cited sources.

    Args:
        claim_text: Text of the claim
        citations: List of citation markers (e.g., ["doc1:p3"])
        source_docs: List of source documents with doc_id, page, content
        config: Optional configuration for thresholds

    Returns:
        Tuple of (is_supported, confidence_score)
    """
    if config is None:
        config = FactVerificationConfig()
    if not citations:
        return False, config.no_citation_confidence
    if not source_docs:
        return False, 0.0

    cited_contents = _cited_contents(citations, source_docs)
    if not cited_contents:
        return False, config.missing_citation_confidence

    source_text = " ".join(cited_contents)
    claim_numbers = _extract_numbers(claim_text)
    claim_dates = _extract_dates(claim_text)
    numbers_match, dates_match = _facts_agree(claim_text, source_text, config)

    claim_words = _content_words(claim_text)
    overlap = len(claim_words & _content_words(source_text)) / len(claim_words) if claim_words else 0

    confidence = config.base_confidence
    if numbers_match and claim_numbers:
        confidence += config.number_match_boost
    if dates_match and claim_dates:
        confidence += config.date_match_boost
    confidence += _overlap_boost(overlap, config)
    if _has_negation(claim_text) != _has_negation(source_text.lower()):
        confidence -= config.negation_mismatch_penalty
    if not numbers_match and claim_numbers:
        confidence -= config.number_mismatch_penalty
    if not dates_match and claim_dates:
        confidence -= config.date_mismatch_penalty

    confidence = max(0.0, min(1.0, confidence))
    return confidence >= config.min_support_confidence, confidence


def _date_mismatch_issue(claim: FactClaim, source_docs: list[dict]) -> tuple[str, str] | None:
    claim_dates = _extract_dates(claim.text)
    source_text = " ".join([doc.get("content", "") for doc in source_docs[:5]])
    source_dates = _extract_dates(source_text)
    if claim_dates and source_dates and not any(d in source_dates for d in claim_dates):
        return "date_mismatch", f"Date in claim does not match source. Verify: {', '.join(claim_dates)}"
    return None


def _number_mismatch_issue(
    claim: FactClaim, source_docs: list[dict], config: FactVerificationConfig
) -> tuple[str, str] | None:
    claim_numbers = _extract_numbers(claim.text)
    source_text = " ".join([doc.get("content", "") for doc in source_docs[:5]])
    source_numbers = _extract_numbers(source_text)
    if claim_numbers and source_numbers:
        has_match = any(
            any(_numbers_match(cn, sn, config.number_tolerance) for sn in source_numbers) for cn in claim_numbers
        )
        if not has_match:
            return (
                "number_mismatch",
                f"Number in claim does not match source (>{config.number_tolerance * 100:.0f}% difference)",
            )
    return None


def _negation_conflict_issue(claim: FactClaim, source_docs: list[dict]) -> tuple[str, str] | None:
    source_text = " ".join([doc.get("content", "") for doc in source_docs[:5]])
    if _has_negation(claim.text) != _has_negation(source_text):
        return "negation_conflict", "Claim negation conflicts with source"
    return None


def _unsupported_claim_issue(
    claim: FactClaim, source_docs: list[dict], config: FactVerificationConfig
) -> tuple[str, str]:
    """The specific reason an unsupported claim failed, or the generic one if none applies."""
    if not claim.citations:
        return "missing_citation", "Add citation [doc_id:page] to support this claim"
    issue = None
    if claim.claim_type == "date":
        issue = _date_mismatch_issue(claim, source_docs)
    elif claim.claim_type == "number":
        issue = _number_mismatch_issue(claim, source_docs, config)
    elif claim.claim_type == "negation":
        issue = _negation_conflict_issue(claim, source_docs)
    return issue or ("unsupported_claim", "Remove or hedge this claim, or add proper citation")


def verify_claim_against_source(
    claim: FactClaim, source_docs: list[dict], config: FactVerificationConfig | None = None
) -> VerificationResult:
    """
    Verify a single claim against source documents.

    Checks:
    - Citation exists and is valid
    - Claim content matches source
    - Numbers/dates are accurate
    - No contradictions or negation conflicts

    Args:
        claim: FactClaim to verify
        source_docs: List of source documents
        config: Optional configuration for thresholds

    Returns:
        VerificationResult with verification status and issues
    """
    if config is None:
        config = FactVerificationConfig()

    is_supported, confidence = check_citation_support(claim.text, claim.citations, source_docs, config)

    if not is_supported:
        issue_type, suggestion = _unsupported_claim_issue(claim, source_docs, config)
        return VerificationResult(
            claim=claim, is_verified=False, confidence=confidence, issue_type=issue_type, suggestion=suggestion
        )

    return VerificationResult(claim=claim, is_verified=True, confidence=confidence, issue_type="", suggestion="")


class FactVerificationStage:
    """Internal claim-groundedness stage owned by ``ValidationCascade``.

    Workflow:
    1. Extract factual claims from answer
    2. Verify each claim against source documents
    3. Calculate groundedness score
    4. Flag unverified claims for removal/hedging
    """

    def __init__(self, config: FactVerificationConfig | None = None):
        """
        Initialize fact verifier with configuration.

        Args:
            config: FactVerificationConfig instance or None for defaults
        """
        if config is None:
            config = FactVerificationConfig()
        self.config = config

    def verify(
        self, answer: str, source_docs: list[dict], citations: list[dict] | None = None
    ) -> AnswerVerificationResult:
        """
        Verify entire answer for factual accuracy and groundedness.

        Synchronous: it is pure computation over in-memory text, so the cascade
        runs it on a worker thread rather than on the event loop.

        Args:
            answer: Generated answer text
            source_docs: Source documents used for generation
            citations: Optional explicit citation objects (if not embedded in answer).
                Intentionally unread today -- claims cite by marker parsed out of
                `answer` itself (see `check_citation_support`). Kept in the
                signature because `ValidationCascade` passes it positionally
                (python:S1172).

        Returns:
            AnswerVerificationResult with verification details
        """
        import time

        start_time = time.time()

        if not answer or not answer.strip():
            return AnswerVerificationResult(
                overall_verified=True,
                groundedness_score=1.0,
                verified_claims=[],
                unverified_claims=[],
                issues=[],
                execution_time_ms=0,
            )

        # Extract claims
        claims = extract_claims(answer, self.config)

        if not claims:
            # No factual claims to verify
            return AnswerVerificationResult(
                overall_verified=True,
                groundedness_score=1.0,
                verified_claims=[],
                unverified_claims=[],
                issues=[],
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        # Verify each claim
        verified_claims = []
        unverified_claims = []
        issues = []

        for claim in claims:
            result = verify_claim_against_source(claim, source_docs, self.config)

            if result.is_verified:
                verified_claims.append(claim)
            else:
                unverified_claims.append(claim.text[:100])  # Truncate for display
                if result.issue_type:
                    issues.append(f"{result.issue_type}: {claim.text[:80]}")

        # Calculate groundedness score
        total_claims = len(claims)
        verified_count = len(verified_claims)
        groundedness_score = verified_count / total_claims if total_claims > 0 else 1.0

        overall_verified = groundedness_score >= self.config.min_groundedness

        elapsed = int((time.time() - start_time) * 1000)

        return AnswerVerificationResult(
            overall_verified=overall_verified,
            groundedness_score=round(groundedness_score, 3),
            verified_claims=verified_claims,
            unverified_claims=unverified_claims,
            issues=issues,
            execution_time_ms=elapsed,
        )
