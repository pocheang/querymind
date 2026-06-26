"""
Batch validation interface for Answer Validator (P1-9).

Allows validating multiple answers in parallel for better performance.
"""

from typing import List
import asyncio


async def validate_answers_batch(
    queries: List[str],
    answers: List[str],
    source_docs_list: List[List[Dict]],
    citations_list: List[List[Dict]],
) -> List[AnswerValidationResult]:
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
            print(f"{query}: {result.overall_score}")
    """
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

    # Create validation tasks for all answers in parallel
    tasks = [
        validate_answer(query, answer, source_docs, citations)
        for query, answer, source_docs, citations in zip(
            queries, answers, source_docs_list, citations_list
        )
    ]

    # Execute all validations concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle any exceptions
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Batch validation failed for index {i}: {result}")
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
        else:
            processed_results.append(result)

    return processed_results
