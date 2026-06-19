"""
Tests for custom exception hierarchy.

Validates:
    - Exception inheritance structure
    - Exception message formatting
    - Exception details preservation
    - wrap_external_exception utility
"""

import pytest
from app.core.exceptions import (
    RAGBaseException,
    VectorStoreException,
    BM25Exception,
    RerankerException,
    GraphRetrievalException,
    RouterAgentException,
    SynthesisAgentException,
    WebResearchException,
    InvalidCredentialsException,
    SessionExpiredException,
    InsufficientPermissionsException,
    OCRException,
    PDFProcessingException,
    ChunkingException,
    ConfigurationException,
    ResourceUnavailableException,
    QuotaExceededException,
    wrap_external_exception,
)


class TestExceptionHierarchy:
    """Test exception class structure."""

    def test_all_exceptions_inherit_from_base(self):
        """All custom exceptions should inherit from RAGBaseException."""
        exception_classes = [
            VectorStoreException,
            BM25Exception,
            RerankerException,
            GraphRetrievalException,
            RouterAgentException,
            SynthesisAgentException,
            WebResearchException,
            InvalidCredentialsException,
            SessionExpiredException,
            InsufficientPermissionsException,
            OCRException,
            PDFProcessingException,
            ChunkingException,
            ConfigurationException,
            ResourceUnavailableException,
            QuotaExceededException,
        ]

        for exc_class in exception_classes:
            assert issubclass(exc_class, RAGBaseException)
            assert issubclass(exc_class, Exception)

    def test_base_exception_inherits_from_exception(self):
        """RAGBaseException should inherit from built-in Exception."""
        assert issubclass(RAGBaseException, Exception)


class TestExceptionMessages:
    """Test exception message handling."""

    def test_simple_message(self):
        """Exception with simple message."""
        exc = VectorStoreException("Connection failed")
        assert str(exc) == "Connection failed"
        assert exc.message == "Connection failed"
        assert exc.details == {}

    def test_message_with_details(self):
        """Exception with message and details."""
        exc = VectorStoreException(
            "Connection failed",
            details={"host": "localhost", "port": 8000}
        )
        assert "Connection failed" in str(exc)
        assert "host=localhost" in str(exc)
        assert "port=8000" in str(exc)
        assert exc.details["host"] == "localhost"

    def test_details_preservation(self):
        """Exception details should be preserved."""
        details = {
            "user_id": "user123",
            "query": "test query",
            "error_code": 500
        }
        exc = RouterAgentException("Routing failed", details=details)

        assert exc.details["user_id"] == "user123"
        assert exc.details["query"] == "test query"
        assert exc.details["error_code"] == 500


class TestExceptionWrapping:
    """Test wrap_external_exception utility."""

    def test_wrap_stdlib_exception(self):
        """Wrap a standard library exception."""
        try:
            raise ValueError("Invalid value")
        except ValueError as e:
            wrapped = wrap_external_exception(
                e,
                ConfigurationException,
                "Configuration validation failed",
                setting="MODEL_BACKEND",
                value="invalid"
            )

            assert isinstance(wrapped, ConfigurationException)
            assert wrapped.message == "Configuration validation failed"
            assert wrapped.details["setting"] == "MODEL_BACKEND"
            assert wrapped.details["value"] == "invalid"

    def test_wrap_preserves_context(self):
        """Wrapped exception should preserve original context."""
        original_error = ConnectionError("Connection refused")

        wrapped = wrap_external_exception(
            original_error,
            ResourceUnavailableException,
            "Redis connection failed",
            host="localhost",
            port=6379
        )

        assert isinstance(wrapped, ResourceUnavailableException)
        assert wrapped.details["host"] == "localhost"
        assert wrapped.details["port"] == 6379


class TestExceptionCatching:
    """Test exception catching patterns."""

    def test_catch_specific_exception(self):
        """Should catch specific exception type."""
        with pytest.raises(VectorStoreException):
            raise VectorStoreException("Test error")

    def test_catch_base_exception(self):
        """Should catch via base exception class."""
        with pytest.raises(RAGBaseException):
            raise VectorStoreException("Test error")

    def test_catch_builtin_exception(self):
        """Should catch via built-in Exception."""
        with pytest.raises(Exception):
            raise VectorStoreException("Test error")

    def test_catch_category(self):
        """Should catch by exception category."""
        # AuthException category
        from app.core.exceptions import AuthException

        with pytest.raises(AuthException):
            raise InvalidCredentialsException("Bad password")

        with pytest.raises(AuthException):
            raise SessionExpiredException("Token expired")


class TestRealWorldScenarios:
    """Test realistic usage scenarios."""

    def test_vector_store_failure_scenario(self):
        """Simulate vector store connection failure."""
        try:
            # Simulate ChromaDB connection failure
            raise ConnectionError("Connection to ChromaDB failed")
        except ConnectionError as e:
            exc = wrap_external_exception(
                e,
                VectorStoreException,
                "Failed to connect to vector store",
                collection="local_rag_collection",
                operation="get"
            )

            assert isinstance(exc, VectorStoreException)
            assert "vector store" in exc.message.lower()
            assert exc.details["collection"] == "local_rag_collection"

    def test_authentication_failure_scenario(self):
        """Simulate authentication failure."""
        exc = InvalidCredentialsException(
            "Invalid username or password",
            details={"username": "testuser", "ip": "192.168.1.1"}
        )

        assert "password" in exc.message.lower()
        assert exc.details["username"] == "testuser"

    def test_quota_exceeded_scenario(self):
        """Simulate quota exceeded."""
        exc = QuotaExceededException(
            "Daily query limit exceeded",
            details={
                "user_id": "user123",
                "limit": 100,
                "current": 105,
                "reset_time": "2026-06-18T00:00:00Z"
            }
        )

        assert exc.details["limit"] == 100
        assert exc.details["current"] == 105
        assert "exceeded" in exc.message.lower()
