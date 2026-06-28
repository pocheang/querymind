"""
Tests for Cypher query validation and error handling.
"""

import pytest

from app.graph.cypher_validation import (
    CypherQueryTemplate,
    ValidationResult,
    get_query_templates,
    validate_cypher_query,
)


class TestCypherValidation:
    """Test Cypher query validation."""

    def test_validate_valid_query(self):
        """Test validation passes for valid Cypher query."""
        query = "MATCH (e:Entity {name: $entity})-[r:RELATED]-(o:Entity) RETURN e.name, r.type, o.name LIMIT 10"
        result = validate_cypher_query(query)

        assert result.is_valid
        assert result.error is None
        assert result.error_type is None

    def test_validate_query_with_syntax_error(self):
        """Test validation detects syntax errors."""
        query = "MATCH (e:Entity {name: $entity)-[r:RELATED]-(o:Entity) RETURN e.name"  # Missing closing brace
        result = validate_cypher_query(query)

        assert not result.is_valid
        assert result.error is not None
        assert result.error_type == "syntax_error"

    def test_validate_query_missing_match(self):
        """Test validation detects missing MATCH clause."""
        query = "RETURN e.name"
        result = validate_cypher_query(query)

        assert not result.is_valid
        assert result.error_type == "missing_match"

    def test_validate_query_missing_return(self):
        """Test validation detects missing RETURN clause."""
        query = "MATCH (e:Entity)"
        result = validate_cypher_query(query)

        assert not result.is_valid
        assert result.error_type == "missing_return"

    def test_validate_query_with_delete(self):
        """Test validation rejects DELETE operations."""
        query = "MATCH (e:Entity) DELETE e"
        result = validate_cypher_query(query)

        assert not result.is_valid
        assert result.error_type == "unsafe_operation"
        assert "DELETE" in result.error

    def test_validate_query_with_set(self):
        """Test validation rejects SET operations."""
        query = "MATCH (e:Entity) SET e.name = 'test'"
        result = validate_cypher_query(query)

        assert not result.is_valid
        assert result.error_type == "unsafe_operation"

    def test_validate_query_with_create(self):
        """Test validation rejects CREATE operations."""
        query = "CREATE (e:Entity {name: 'test'})"
        result = validate_cypher_query(query)

        assert not result.is_valid
        assert result.error_type == "unsafe_operation"

    def test_validate_query_with_merge(self):
        """Test validation rejects MERGE operations."""
        query = "MERGE (e:Entity {name: 'test'})"
        result = validate_cypher_query(query)

        assert not result.is_valid
        assert result.error_type == "unsafe_operation"

    def test_validate_empty_query(self):
        """Test validation handles empty query."""
        result = validate_cypher_query("")

        assert not result.is_valid
        assert result.error_type == "empty_query"

    def test_validate_query_with_limit(self):
        """Test validation accepts query with LIMIT."""
        query = "MATCH (e:Entity) RETURN e.name LIMIT 100"
        result = validate_cypher_query(query)

        assert result.is_valid

    def test_validate_query_with_where_clause(self):
        """Test validation accepts query with WHERE clause."""
        query = "MATCH (e:Entity) WHERE e.name = 'test' RETURN e.name"
        result = validate_cypher_query(query)

        assert result.is_valid

    def test_validate_query_with_optional_match(self):
        """Test validation accepts query with OPTIONAL MATCH."""
        query = "MATCH (e:Entity) OPTIONAL MATCH (e)-[r:RELATED]-(o:Entity) RETURN e.name, o.name"
        result = validate_cypher_query(query)

        assert result.is_valid


class TestQueryTemplates:
    """Test query template generation."""

    def test_get_query_templates_returns_list(self):
        """Test that get_query_templates returns a list."""
        templates = get_query_templates()

        assert isinstance(templates, list)
        assert len(templates) > 0
        assert all(isinstance(t, CypherQueryTemplate) for t in templates)

    def test_entity_search_template(self):
        """Test entity search template."""
        templates = get_query_templates()
        entity_search = next((t for t in templates if t.name == "entity_search"), None)

        assert entity_search is not None
        assert "MATCH" in entity_search.query
        assert "Entity" in entity_search.query
        assert "keywords" in entity_search.params
        assert "limit" in entity_search.params

    def test_entity_neighbors_template(self):
        """Test entity neighbors template."""
        templates = get_query_templates()
        neighbors = next((t for t in templates if t.name == "entity_neighbors"), None)

        assert neighbors is not None
        assert "MATCH" in neighbors.query
        assert "RELATED" in neighbors.query
        assert "entity" in neighbors.params

    def test_entity_paths_template(self):
        """Test entity paths template."""
        templates = get_query_templates()
        paths = next((t for t in templates if t.name == "entity_paths_2hop"), None)

        assert paths is not None
        assert "MATCH" in paths.query
        assert "RELATED" in paths.query

    def test_template_query_is_valid(self):
        """Test that all template queries are valid."""
        templates = get_query_templates()

        for template in templates:
            result = validate_cypher_query(template.query)
            assert result.is_valid, f"Template {template.name} has invalid query: {result.error}"


class TestValidationResult:
    """Test ValidationResult data class."""

    def test_validation_result_valid(self):
        """Test ValidationResult for valid query."""
        result = ValidationResult(is_valid=True, error=None, error_type=None)

        assert result.is_valid
        assert result.error is None
        assert result.error_type is None

    def test_validation_result_invalid(self):
        """Test ValidationResult for invalid query."""
        result = ValidationResult(
            is_valid=False,
            error="Syntax error",
            error_type="syntax_error"
        )

        assert not result.is_valid
        assert result.error == "Syntax error"
        assert result.error_type == "syntax_error"


class TestCypherQueryTemplate:
    """Test CypherQueryTemplate data class."""

    def test_template_creation(self):
        """Test CypherQueryTemplate creation."""
        template = CypherQueryTemplate(
            name="test_template",
            query="MATCH (e:Entity) RETURN e.name",
            params=["entity"],
            description="Test template"
        )

        assert template.name == "test_template"
        assert template.query == "MATCH (e:Entity) RETURN e.name"
        assert template.params == ["entity"]
        assert template.description == "Test template"
