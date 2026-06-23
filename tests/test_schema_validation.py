"""Test schema validation for QueryRequest."""

import pytest
from pydantic import ValidationError

from app.core.schemas import QueryRequest


def test_force_language_valid_values():
    """Test that force_language accepts valid values."""
    # Valid: empty string (auto-detect)
    req1 = QueryRequest(question="test", force_language="")
    assert req1.force_language == ""

    # Valid: 'zh'
    req2 = QueryRequest(question="test", force_language="zh")
    assert req2.force_language == "zh"

    # Valid: 'en'
    req3 = QueryRequest(question="test", force_language="en")
    assert req3.force_language == "en"


def test_force_language_invalid_values():
    """Test that force_language rejects invalid values."""
    # Invalid: 'fr'
    with pytest.raises(ValidationError) as exc_info:
        QueryRequest(question="test", force_language="fr")

    assert "force_language must be 'zh', 'en', or empty string" in str(exc_info.value)

    # Invalid: 'es'
    with pytest.raises(ValidationError) as exc_info:
        QueryRequest(question="test", force_language="es")

    assert "force_language must be 'zh', 'en', or empty string" in str(exc_info.value)

    # Invalid: random string
    with pytest.raises(ValidationError) as exc_info:
        QueryRequest(question="test", force_language="invalid")

    assert "force_language must be 'zh', 'en', or empty string" in str(exc_info.value)


def test_force_language_default():
    """Test that force_language defaults to empty string."""
    req = QueryRequest(question="test")
    assert req.force_language == ""
