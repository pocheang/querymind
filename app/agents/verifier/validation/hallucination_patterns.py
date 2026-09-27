"""
Rule-based hallucination pattern detection (Task 9).

Fast pattern matching (<5ms) for common hallucination types:
- Date mismatches
- Number mismatches (>15% tolerance)
- Entity mismatches
- Negation conflicts

Designed to complement NLI validation at cascade Level 1.
"""

import re

from pydantic import BaseModel

from app.agents.verifier.validation.claims_text import claims_text


class HallucinationPattern(BaseModel):
    """Detected hallucination pattern"""

    pattern_type: str
    severity: str  # "critical", "high", "medium", "low"
    content: str
    suggestion: str


def _extract_dates(text: str) -> set[str]:
    """
    Extract dates from text (English and Chinese).

    Patterns:
    - 4-digit years: 2020, 2021
    - Chinese dates: 2020年3月15日
    - ISO dates: 2020-03-15
    - US dates: 03/15/2020
    - Quarter dates: Q1 2020

    Returns:
        Set of date strings found in text
    """
    dates = set()

    # 4-digit years (most common)
    dates.update(re.findall(r"\b((?:19|20)\d{2})\b", text))

    # Chinese date patterns
    dates.update(re.findall(r"\d{4}年(?:\d{1,2}月)?(?:\d{1,2}日)?", text))

    # ISO dates: YYYY-MM-DD
    dates.update(re.findall(r"\d{4}-\d{2}-\d{2}", text))

    # US dates: MM/DD/YYYY or M/D/YY
    dates.update(re.findall(r"\d{1,2}/\d{1,2}/\d{2,4}", text))

    # Quarter dates: Q1 2020, Q4 2021
    dates.update(re.findall(r"Q[1-4]\s*\d{4}", text, re.IGNORECASE))

    return dates


def _extract_numbers(text: str) -> list[float]:
    """
    Extract numeric values from text.

    Handles:
    - Plain numbers: 100, 3.14
    - Numbers with commas: 1,000,000
    - Percentages: 25%
    - Currency: $100M, $5B
    - Units: million, billion, thousand

    Returns:
        List of numeric values (normalized)
    """
    numbers = []

    # Match numbers with optional units and currency
    pattern = r"\$?\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:million|billion|thousand|[MBK]|%))?"
    matches = re.findall(pattern, text, re.IGNORECASE)

    for match in matches:
        # Clean the match
        cleaned = re.sub(r"[,$\s]", "", match)

        # Handle percentages separately (keep as-is)
        if "%" in match:
            try:
                value = float(cleaned.replace("%", ""))
                numbers.append(value)
            except ValueError:
                pass
            continue

        # Handle unit multipliers
        multiplier = 1
        if "billion" in match.lower() or "B" in match:
            multiplier = 1e9
        elif "million" in match.lower() or "M" in match:
            multiplier = 1e6
        elif "thousand" in match.lower() or "K" in match:
            multiplier = 1e3

        # Remove letters and convert
        cleaned = re.sub(r"[a-zA-Z%]", "", cleaned)
        try:
            value = float(cleaned) * multiplier
            numbers.append(value)
        except ValueError:
            pass

    return numbers


def _extract_entities(text: str) -> set[str]:
    """
    Extract named entities (proper nouns) from text.

    Capitalised Latin words, single or in a run (John Smith, Acme Corp).

    There is no Chinese candidate, on purpose. It used to take every two to four
    character run, which is not how a name is shaped in running Chinese text --
    replayed over thirty real answers it reported "以下是", "个层面" and "后再试"
    as entities the sources lacked, and nothing it flagged was a name. Without a
    Chinese NER model there is no honest candidate to offer.

    Returns:
        Set of entity strings
    """
    # `[ \t]`, not `\s`: a run of capitalised words must stay on one line.
    # With `\s` it crossed paragraph breaks, and "Versions\n\nThe" was reported
    # as a name the sources lacked.
    return set(re.findall(r"\b[A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+)*\b", text))


def _numbers_match(num1: float, num2: float, tolerance: float = 0.15) -> bool:
    """
    Check if two numbers match within tolerance.

    Args:
        num1: First number
        num2: Second number
        tolerance: Allowed relative difference (default 15%)

    Returns:
        True if numbers match within tolerance
    """
    if num1 == 0 and num2 == 0:
        return True
    if num1 == 0 or num2 == 0:
        return False

    relative_diff = abs(num1 - num2) / max(abs(num1), abs(num2))
    return relative_diff <= tolerance


def detect_date_hallucinations(answer: str, source_text: str) -> list[HallucinationPattern]:
    """
    Detect date mismatches between answer and source.

    Args:
        answer: Generated answer text
        source_text: Source document text

    Returns:
        List of detected date hallucination patterns
    """
    if not answer or not source_text:
        return []

    issues = []

    answer_dates = _extract_dates(answer)
    source_dates = _extract_dates(source_text)

    if not answer_dates or not source_dates:
        return []

    # Find dates in answer not present in source
    mismatched_dates = answer_dates - source_dates

    if mismatched_dates:
        issues.append(
            HallucinationPattern(
                pattern_type="date_mismatch",
                severity="high",
                content=f"Date(s) not in source: {', '.join(sorted(mismatched_dates))}",
                suggestion="Verify dates against source documents",
            )
        )

    return issues


def detect_number_hallucinations(answer: str, source_text: str) -> list[HallucinationPattern]:
    """
    Detect number mismatches between answer and source.

    Numbers must match within 15% tolerance.

    Args:
        answer: Generated answer text
        source_text: Source document text

    Returns:
        List of detected number hallucination patterns
    """
    if not answer or not source_text:
        return []

    issues = []

    answer_numbers = _extract_numbers(answer)
    source_numbers = _extract_numbers(source_text)

    if not answer_numbers or not source_numbers:
        return []

    # Check each answer number against source numbers
    for ans_num in answer_numbers:
        has_match = any(_numbers_match(ans_num, src_num) for src_num in source_numbers)

        if not has_match:
            # Format number for display
            if ans_num >= 1e9:
                display = f"${ans_num / 1e9:.1f}B"
            elif ans_num >= 1e6:
                display = f"${ans_num / 1e6:.1f}M"
            elif ans_num >= 1e3:
                display = f"${ans_num / 1e3:.1f}K"
            else:
                display = f"{ans_num}"

            issues.append(
                HallucinationPattern(
                    pattern_type="number_mismatch",
                    severity="high",
                    content=f"Number {display} not found in sources (within 15% tolerance)",
                    suggestion="Verify numeric claims against source",
                )
            )

    return issues


# Entity-shaped words that are never entities.
_COMMON_ENGLISH_ENTITIES = {
    "The",
    "A",
    "An",
    "In",
    "On",
    "At",
    "To",
    "For",
    "Of",
    "With",
    "CEO",
    "CFO",
    "CTO",
    "COO",
    "President",
    "Director",
    "Manager",
    "Company",
    "Corporation",
    "Inc",
    "Ltd",
    "LLC",
}


def _entity_is_in_source(entity: str, source_text: str) -> bool:
    """A multi-word name is grounded when all of its words are in the source."""

    if " " in entity:
        return all(word in source_text for word in entity.split())
    return entity in source_text


def _likely_proper_noun(entity: str) -> bool:
    """Narrow the miss list to what a reader would call a name: a run of words.

    A single capitalised word is usually just the start of a sentence.
    """

    return " " in entity


def detect_entity_hallucinations(answer: str, source_text: str) -> list[HallucinationPattern]:
    """
    Detect entity mismatches between answer and source.

    Checks proper nouns (names, organizations) in answer against source.

    Args:
        answer: Generated answer text
        source_text: Source document text

    Returns:
        List of detected entity hallucination patterns
    """
    if not answer or not source_text:
        return []

    answer_entities = _extract_entities(answer)
    if not answer_entities:
        return []
    source_entities = _extract_entities(source_text)

    mismatched = {entity for entity in answer_entities - source_entities if entity not in _COMMON_ENGLISH_ENTITIES}
    truly_missing = {e for e in mismatched if not _entity_is_in_source(e, source_text)}
    likely_names = {e for e in truly_missing if _likely_proper_noun(e)}

    if not likely_names:
        return []
    named = ", ".join(sorted(likely_names))
    return [
        HallucinationPattern(
            pattern_type="entity_mismatch",
            severity="medium",
            content=f"Entities not in source: {named}",
            suggestion="Verify entity names against source",
        )
    ]


# Negation patterns (English and Chinese)
_NEGATION_PATTERNS = [
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


# Chinese content-word candidates for the negation check's overlap comparison.
# Not entities: it takes every two to four character run, which is what made it
# useless as an entity candidate (see `_extract_entities`), and is what an
# overlap measure wants.
_CJK_WORD_RE = re.compile(r"[一-鿿]{2,4}")


def _has_negation(text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in _NEGATION_PATTERNS)


def _content_words(text: str) -> tuple[set[str], set[str]]:
    """Key content words for overlap comparison: English 3+ chars plus CJK runs.

    Returns (all content words, the CJK subset alone) -- the caller needs the
    subset on its own for a Chinese-only overlap check.
    """
    words = set(re.findall(r"\b\w{3,}\b", text.lower()))
    chinese = set(_CJK_WORD_RE.findall(text))
    words.update(chinese)
    return words, chinese


def _count_stem_matches(answer_words: set[str], source_words: set[str]) -> int:
    """Words of at least 4 chars where one is a 4-char prefix of the other.

    e.g. "profitable" vs "profitability" -- simple stemming without an NLP
    dependency.
    """
    stem_matches = 0
    for ans_word in answer_words:
        if len(ans_word) < 4:
            continue
        for src_word in source_words:
            if len(src_word) < 4:
                continue
            if ans_word.startswith(src_word[:4]) or src_word.startswith(ans_word[:4]):
                stem_matches += 1
                break
    return stem_matches


def detect_negation_hallucinations(answer: str, source_text: str) -> list[HallucinationPattern]:
    """
    Detect negation conflicts between answer and source.

    Flags cases where:
    - Answer negates what source affirms
    - Answer affirms what source negates

    Args:
        answer: Generated answer text
        source_text: Source document text

    Returns:
        List of detected negation hallucination patterns
    """
    if not answer or not source_text:
        return []

    if _has_negation(answer) == _has_negation(source_text):
        return []

    answer_words, answer_chinese = _content_words(answer)
    source_words, source_chinese = _content_words(source_text)
    shared_words = answer_words & source_words
    stem_matches = _count_stem_matches(answer_words, source_words)

    # If significant overlap, likely discussing same topic with opposite polarity
    # Threshold: at least 1 shared word + 1 stem match, OR 2 shared words, OR 1 Chinese word overlap
    has_chinese_overlap = len(answer_chinese & source_chinese) >= 1
    has_word_overlap = len(shared_words) >= 2 or (len(shared_words) >= 1 and stem_matches >= 1)

    if not (has_chinese_overlap or has_word_overlap or stem_matches >= 2):
        return []

    return [
        HallucinationPattern(
            pattern_type="negation_conflict",
            severity="high",
            content="Answer negation conflicts with source",
            suggestion="Verify answer doesn't contradict source",
        )
    ]


def detect_all_patterns(answer: str, source_text: str) -> list[HallucinationPattern]:
    """
    Run all hallucination pattern detectors.

    Combines:
    - Date validation
    - Number validation
    - Entity validation
    - Negation detection

    Target: <5ms total

    Args:
        answer: Generated answer text
        source_text: Source document text (concatenated from source_docs)

    Returns:
        List of all detected hallucination patterns
    """
    all_issues = []
    # The claims, not the markup: citation markers read as the number 1, list
    # and heading ordinals as numbers, and Title Case headings as names. See
    # `claims_text` for what was measured.
    answer = claims_text(answer)

    # Run all detectors
    all_issues.extend(detect_date_hallucinations(answer, source_text))
    all_issues.extend(detect_number_hallucinations(answer, source_text))
    all_issues.extend(detect_entity_hallucinations(answer, source_text))
    all_issues.extend(detect_negation_hallucinations(answer, source_text))

    return all_issues
