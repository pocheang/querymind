"""
Tests for golden dataset validation and structure.
"""

import pytest
from tests.golden_dataset import (
    get_dataset,
    get_dataset_by_complexity,
    get_dataset_by_category,
    validate_dataset,
    GOLDEN_DATASET
)


def test_dataset_has_100_queries():
    """Golden dataset must contain exactly 100 annotated queries."""
    dataset = get_dataset()
    assert len(dataset) == 100, f"Expected 100 queries, got {len(dataset)}"


def test_dataset_structure():
    """Each query must have required fields with valid values."""
    validate_dataset()


def test_dataset_query_uniqueness():
    """Queries should be mostly unique (allow some minor variations)."""
    queries = [item["query"] for item in GOLDEN_DATASET]
    unique_queries = set(queries)
    # Allow up to 5% duplicates for variations
    assert len(unique_queries) >= 95, f"Expected at least 95 unique queries, got {len(unique_queries)}"


def test_dataset_quality_score_distribution():
    """Quality scores should be well-distributed across the range."""
    scores = [item["human_quality_score"] for item in GOLDEN_DATASET]

    # Should have high quality (>0.8)
    high_quality = [s for s in scores if s >= 0.8]
    assert len(high_quality) >= 30, f"Expected at least 30 high quality queries, got {len(high_quality)}"

    # Should have medium quality (0.5-0.8)
    medium_quality = [s for s in scores if 0.5 <= s < 0.8]
    assert len(medium_quality) >= 30, f"Expected at least 30 medium quality queries, got {len(medium_quality)}"

    # Should have low quality (<0.5)
    low_quality = [s for s in scores if s < 0.5]
    assert len(low_quality) >= 10, f"Expected at least 10 low quality queries, got {len(low_quality)}"


def test_dataset_complexity_distribution():
    """Dataset should have balanced complexity distribution."""
    simple = get_dataset_by_complexity("simple")
    medium = get_dataset_by_complexity("medium")
    complex_queries = get_dataset_by_complexity("complex")

    # Each complexity should have reasonable representation
    assert len(simple) >= 20, f"Expected at least 20 simple queries, got {len(simple)}"
    assert len(medium) >= 20, f"Expected at least 20 medium queries, got {len(medium)}"
    assert len(complex_queries) >= 15, f"Expected at least 15 complex queries, got {len(complex_queries)}"


def test_dataset_category_distribution():
    """Dataset should cover multiple query categories."""
    factual = get_dataset_by_category("factual")
    analytical = get_dataset_by_category("analytical")
    procedural = get_dataset_by_category("procedural")
    comparative = get_dataset_by_category("comparative")

    # Each category should have reasonable representation
    assert len(factual) >= 20, f"Expected at least 20 factual queries, got {len(factual)}"
    assert len(analytical) >= 15, f"Expected at least 15 analytical queries, got {len(analytical)}"
    assert len(procedural) >= 10, f"Expected at least 10 procedural queries, got {len(procedural)}"
    assert len(comparative) >= 10, f"Expected at least 10 comparative queries, got {len(comparative)}"


def test_dataset_bilingual_coverage():
    """Dataset should include both English and Chinese queries."""
    english_queries = [item for item in GOLDEN_DATASET if all(ord(c) < 128 for c in item["query"])]
    chinese_queries = [item for item in GOLDEN_DATASET if any(ord(c) >= 128 for c in item["query"])]

    # Should have at least 30% of each language
    assert len(english_queries) >= 30, f"Expected at least 30 English queries, got {len(english_queries)}"
    assert len(chinese_queries) >= 30, f"Expected at least 30 Chinese queries, got {len(chinese_queries)}"


def test_dataset_route_distribution():
    """Dataset should cover multiple routing strategies."""
    routes = {}
    for item in GOLDEN_DATASET:
        route = item["expected_route"]
        routes[route] = routes.get(route, 0) + 1

    # Should have vector, hybrid, and react routes
    assert "vector" in routes, "Dataset missing 'vector' route queries"
    assert "hybrid" in routes, "Dataset missing 'hybrid' route queries"
    assert "react" in routes, "Dataset missing 'react' route queries"

    # Each route should have reasonable representation
    assert routes["vector"] >= 20, f"Expected at least 20 vector queries, got {routes['vector']}"
    assert routes["hybrid"] >= 15, f"Expected at least 15 hybrid queries, got {routes['hybrid']}"
    assert routes["react"] >= 10, f"Expected at least 10 react queries, got {routes['react']}"
