"""Utilities for loading evaluation datasets."""

import json
from pathlib import Path
from typing import List

from app.evaluation.models import TestQuery


def load_test_queries(file_path: str | Path) -> List[TestQuery]:
    """Load test queries from a JSON file.
    
    Args:
        file_path: Path to JSON file containing test queries
        
    Returns:
        List of TestQuery objects
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the JSON format is invalid
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Test query file not found: {file_path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if "queries" not in data:
        raise ValueError("JSON file must contain a 'queries' key")
    
    queries = []
    for query_data in data["queries"]:
        query = TestQuery(**query_data)
        queries.append(query)
    
    return queries


def save_test_queries(queries: List[TestQuery], file_path: str | Path) -> None:
    """Save test queries to a JSON file.
    
    Args:
        queries: List of TestQuery objects
        file_path: Path to output JSON file
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "queries": [query.model_dump() for query in queries]
    }
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def filter_queries_by_category(
    queries: List[TestQuery],
    category: str
) -> List[TestQuery]:
    """Filter test queries by category.
    
    Args:
        queries: List of TestQuery objects
        category: Category to filter by
        
    Returns:
        Filtered list of TestQuery objects
    """
    return [q for q in queries if q.category == category]


def filter_queries_by_difficulty(
    queries: List[TestQuery],
    difficulty: str
) -> List[TestQuery]:
    """Filter test queries by difficulty.
    
    Args:
        queries: List of TestQuery objects
        difficulty: Difficulty level to filter by (easy, medium, hard)
        
    Returns:
        Filtered list of TestQuery objects
    """
    return [q for q in queries if q.difficulty == difficulty]
