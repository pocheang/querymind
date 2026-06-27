"""
Batch validation interface for Answer Validator (P1-9).

Allows validating multiple answers in parallel for better performance.
"""

import asyncio
import logging
import time

from app.agents.answer_validator_agent import validate_answer
from app.agents.quality_models import (
    AnswerValidationResult,
    AnswerValidationDetails,
    AnswerIssue,
)

logger = logging.getLogger(__name__)

# Concurrency limit to prevent resource exhaustion
_MAX_CONCURRENT_VALIDATIONS = 10


async def validate_answers_batch(
    queries: list[str],
    answers: list[str],
    source_docs_list: list[list[dict]],
    citations_list: list[list[dict]],
    max_concurrent: int = _MAX_CONCURRENT_VALIDATIONS,
) -> list[AnswerValidationResult]:
    """
    Validate multiple answers in parallel (P1-9 enhancement).

    This is significantly faster than validating answers one by one,
    especially when dealing with multiple queries from the same session
    or batch processing scenarios.

    Args:
        queries: List of original queries
        answers: List of generated answers
        source_docs_list: List of source document lists (one per answer)
        citations_list: List of citation lists (one per answer)
        max_concurrent: Maximum number of concurrent validations (default: 10)

    Returns:
        List of AnswerValidationResult objects (same order as input)

    Example:
        queries = ["What is X?", "What is Y?"]
        answers = ["X is...", "Y is..."]
        source_docs = [[{...}], [{...}]]
        citations = [[{...}], [{...}]]

        results = await validate_answers_batch(
            queries, answers, source_docs, citations
        )

        for query, result in zip(queries, results):
            logger.info(f"{query}: {result.overall_score}")
    """
    # Input validation
    if not isinstance(queries, list):
        raise TypeError(f"queries must be a list, got {type(queries).__name__}")
    if not isinstance(answers, list):
        raise TypeError(f"answers must be a list, got {type(answers).__name__}")
    if not isinstance(source_docs_list, list):
        raise TypeError(f"source_docs_list must be a list, got {type(source_docs_list).__name__}")
    if not isinstance(citations_list, list):
        raise TypeError(f"citations_list must be a list, got {type(citations_list).__name__}")

    # Validate input lengths
    n = len(queries)
    if not (len(answers) == len(source_docs_list) == len(citations_list) == n):
        raise ValueError(
            f"Input length mismatch: queries={len(queries)}, "
            f"answers={len(answers)}, source_docs={len(source_docs_list)}, "
            f"citations={len(citations_list)}"
        )

    if n == 0:
        return []

    # Validate max_concurrent parameter
    if not isinstance(max_concurrent, int) or max_concurrent < 1:
        raise ValueError(f"max_concurrent must be a positive integer, got {max_concurrent}")

    # Validate string inputs are not empty
    for i, query in enumerate(queries):
        if not isinstance(query, str):
            raise TypeError(f"queries[{i}] must be a string, got {type(query).__name__}")
        if not query.strip():
            logger.warning(f"queries[{i}] is empty or whitespace-only")

    for i, answer in enumerate(answers):
        if not isinstance(answer, str):
            raise TypeError(f"answers[{i}] must be a string, got {type(answer).__name__}")
        if not answer.strip():
            logger.warning(f"answers[{i}] is empty or whitespace-only")

    # Use semaphore to limit concurrent validations and prevent resource exhaustion
    semaphore = asyncio.Semaphore(max_concurrent)
    start_time = time.time()
    logger.info(f"Starting batch validation: {n} answers with max_concurrent={max_concurrent}")

    async def validate_with_semaphore(query, answer, source_docs, citations, index):
        async with semaphore:
            try:
                validation_start = time.time()
                result = await validate_answer(query, answer, source_docs, citations)
                validation_time = time.time() - validation_start
                logger.debug(f"Validation {index + 1}/{n} completed in {validation_time:.2f}s")
                return index, result
            except Exception as e:
                logger.error(f"Batch validation failed for index {index}: {e}")
                return index, e

    # Create validation tasks for all answers with concurrency control
    tasks = [
        validate_with_semaphore(query, answer, source_docs, citations, i)
        for i, (query, answer, source_docs, citations) in enumerate(
            zip(queries, answers, source_docs_list, citations_list)
        )
    ]

    # Execute all validations with concurrency limit
    results_with_indices = await asyncio.gather(*tasks)

    # Sort by original index to maintain order
    results_with_indices.sort(key=lambda x: x[0])

    # Handle any exceptions and build final results
    processed_results = []
    failed_count = 0
    for index, result in results_with_indices:
        if isinstance(result, Exception):
            # Return a failed validation result
            processed_results.append(
                AnswerValidationResult(
                    is_valid=False,
                    overall_score=0.0,
                    validation_details=AnswerValidationDetails(
                        factual_consistency=0.0,
                        hallucination_risk=1.0,
                        citation_completeness=0.0,
                        answer_quality=0.0,
                        safety_score=0.0,
                    ),
                    issues=[
                        AnswerIssue(
                            type="validation_error",
                            severity="critical",
                            content=str(result),
                            suggestion="Retry validation",
                        )
                    ],
                    action="regenerate",
                    execution_time_ms=0,
                    validation_method="error",
                )
            )
            failed_count += 1
        else:
            processed_results.append(result)

    # Performance summary
    total_time = time.time() - start_time
    success_count = n - failed_count
    avg_time = total_time / n if n > 0 else 0

    logger.info(
        f"Batch validation completed: {success_count}/{n} successful in {total_time:.2f}s "
        f"(avg {avg_time:.2f}s per validation, {failed_count} failed)"
    )

    return processed_results
