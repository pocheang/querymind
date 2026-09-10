"""
Session search and filter service.

Provides advanced search and filtering capabilities for sessions
based on metadata, tags, categories, and time ranges.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.services.sessions.metadata import SessionMetadataService
from app.services.sessions.service import (
    SessionCategory,
    SessionMetadata,
    get_metadata_service,
)

__all__ = [
    "SearchQuery",
    "SearchResult",
    "SessionSearchService",
]


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class SearchQuery:
    """Session search query."""

    # Text search
    q: str | None = None  # Search in name, description

    # Tag filters
    tags: list[str] | None = None  # Match any of these tags
    tags_all: list[str] | None = None  # Match all of these tags

    # Category filter
    category: SessionCategory | None = None

    # Time range filters
    created_after: datetime | None = None
    created_before: datetime | None = None
    updated_after: datetime | None = None
    updated_before: datetime | None = None

    # Query count filters
    min_queries: int | None = None
    max_queries: int | None = None

    # Sorting
    sort_by: Literal["created_at", "updated_at", "query_count"] = "updated_at"
    sort_order: Literal["asc", "desc"] = "desc"

    # Pagination
    limit: int = 50
    offset: int = 0


@dataclass
class SearchResult:
    """Session search result."""

    metadata: SessionMetadata
    score: float = 1.0  # Relevance score (0-1)
    matched_tags: list[str] | None = None  # Tags that matched the query


# ============================================================================
# Session Search Service
# ============================================================================


def _any_tags_match(metadata: SessionMetadata, query: SearchQuery) -> tuple[list[str], float] | None:
    """Score the "match any of these tags" filter; `None` means reject."""
    if not query.tags:
        return [], 1.0
    all_tags = set(metadata.tags + metadata.auto_tags)
    query_tags_set = set(query.tags)
    matched = all_tags & query_tags_set
    if not matched:
        return None
    match_ratio = len(matched) / len(query_tags_set)
    return list(matched), 0.5 + 0.5 * match_ratio


def _all_tags_match(metadata: SessionMetadata, query: SearchQuery) -> tuple[list[str], float] | None:
    """Score the "match all of these tags" filter; `None` means reject."""
    if not query.tags_all:
        return [], 1.0
    all_tags = set(metadata.tags + metadata.auto_tags)
    if not set(query.tags_all).issubset(all_tags):
        return None
    return list(query.tags_all), 1.1


def _time_range_rejects(metadata: SessionMetadata, query: SearchQuery) -> bool:
    if query.created_after and metadata.created_at < query.created_after:
        return True
    if query.created_before and metadata.created_at > query.created_before:
        return True
    if query.updated_after and metadata.updated_at < query.updated_after:
        return True
    return bool(query.updated_before and metadata.updated_at > query.updated_before)


def _query_count_rejects(metadata: SessionMetadata, query: SearchQuery) -> bool:
    if query.min_queries is not None and metadata.query_count < query.min_queries:
        return True
    return bool(query.max_queries is not None and metadata.query_count > query.max_queries)


class SessionSearchService:
    """Service for searching and filtering sessions."""

    def __init__(self, metadata_service: SessionMetadataService | None = None):
        self.metadata_service = metadata_service or get_metadata_service()

    def search(self, query: SearchQuery) -> list[SearchResult]:
        """
        Search sessions based on query criteria.

        Args:
            query: Search query

        Returns:
            List of matching sessions with scores
        """
        # Get all metadata
        all_metadata = self.metadata_service.list_all_metadata()

        # Filter by criteria
        results = []
        for metadata in all_metadata:
            score, matched_tags = self._match_metadata(metadata, query)
            if score > 0:
                results.append(
                    SearchResult(
                        metadata=metadata,
                        score=score,
                        matched_tags=matched_tags,
                    )
                )

        # Sort results
        results = self._sort_results(results, query)

        # Apply pagination
        start = query.offset
        end = start + query.limit
        return results[start:end]

    def _match_metadata(
        self,
        metadata: SessionMetadata,
        query: SearchQuery,
    ) -> tuple[float, list[str] | None]:
        """
        Check if metadata matches query and calculate score.

        Args:
            metadata: Session metadata to check
            query: Search query

        Returns:
            Tuple of (score, matched_tags)
            Score is 0 if no match, >0 if matches
        """
        score = 1.0
        matched_tags: list[str] = []

        # Text search (in description)
        if query.q:
            if not self._text_matches(metadata, query.q):
                return 0.0, None
            # Boost score for text match
            score *= 1.2

        any_match = _any_tags_match(metadata, query)
        if any_match is None:
            return 0.0, None
        matched, any_boost = any_match
        matched_tags.extend(matched)
        score *= any_boost

        all_match = _all_tags_match(metadata, query)
        if all_match is None:
            return 0.0, None
        matched, all_boost = all_match
        matched_tags.extend(matched)
        score *= all_boost

        # Category filter
        if query.category:
            if metadata.category != query.category:
                return 0.0, None
            score *= 1.05

        if _time_range_rejects(metadata, query):
            return 0.0, None

        if _query_count_rejects(metadata, query):
            return 0.0, None

        return score, matched_tags if matched_tags else None

    def _text_matches(self, metadata: SessionMetadata, query_text: str) -> bool:
        """
        Check if metadata matches text query.

        Args:
            metadata: Session metadata
            query_text: Query text

        Returns:
            True if matches
        """
        query_lower = query_text.lower()

        # Search in description
        if metadata.description:
            if query_lower in metadata.description.lower():
                return True

        # Search in tags
        for tag in metadata.tags + metadata.auto_tags:
            if query_lower in tag.lower():
                return True

        return False

    def _sort_results(
        self,
        results: list[SearchResult],
        query: SearchQuery,
    ) -> list[SearchResult]:
        """
        Sort search results.

        Args:
            results: Search results
            query: Search query with sort parameters

        Returns:
            Sorted results
        """
        # Get sort key function
        if query.sort_by == "created_at":

            def key_fn(r):
                return r.metadata.created_at
        elif query.sort_by == "updated_at":

            def key_fn(r):
                return r.metadata.updated_at
        elif query.sort_by == "query_count":

            def key_fn(r):
                return r.metadata.query_count
        else:
            # Default: sort by score
            def key_fn(r):
                return r.score

        # Sort
        reverse = query.sort_order == "desc"
        return sorted(results, key=key_fn, reverse=reverse)

    def count(self, query: SearchQuery) -> int:
        """
        Count sessions matching query (without pagination).

        Args:
            query: Search query

        Returns:
            Count of matching sessions
        """
        all_metadata = self.metadata_service.list_all_metadata()

        count = 0
        for metadata in all_metadata:
            score, _ = self._match_metadata(metadata, query)
            if score > 0:
                count += 1

        return count

    def get_facets(self) -> dict[str, list[str | int]]:
        """
        Get facets for filtering.

        Returns:
            Dictionary with available facets:
            - categories: list of categories
            - tags: list of all tags
            - query_count_range: [min, max]
        """
        all_metadata = self.metadata_service.list_all_metadata()

        categories = set()
        all_tags = set()
        query_counts = []

        for metadata in all_metadata:
            if metadata.category:
                categories.add(metadata.category)
            all_tags.update(metadata.tags)
            all_tags.update(metadata.auto_tags)
            query_counts.append(metadata.query_count)

        return {
            "categories": sorted(categories),
            "tags": sorted(all_tags),
            "query_count_range": [
                min(query_counts) if query_counts else 0,
                max(query_counts) if query_counts else 0,
            ],
        }


# ============================================================================
# Singleton Instance
# ============================================================================

_search_service_instance: SessionSearchService | None = None
