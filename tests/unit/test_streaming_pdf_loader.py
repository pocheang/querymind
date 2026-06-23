"""Tests for streaming PDF loader."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest


# Mock langchain_core.documents.Document
class MockDocument:
    def __init__(self, page_content: str, metadata: dict):
        self.page_content = page_content
        self.metadata = metadata


@pytest.fixture(autouse=True)
def mock_langchain():
    """Mock langchain dependencies."""
    mock_module = SimpleNamespace()
    mock_module.Document = MockDocument
    sys.modules["langchain_core.documents"] = mock_module
    yield
    if "langchain_core.documents" in sys.modules:
        del sys.modules["langchain_core.documents"]


def test_load_pdf_streaming_yields_documents_in_chunks():
    """Test that streaming loader yields documents in chunks using page_range."""
    from app.ingestion.utils.streaming_pdf_loader import load_pdf_streaming

    # Mock docling components
    mock_document = Mock()
    mock_document.pages = {1: Mock(), 2: Mock(), 3: Mock()}
    mock_document.export_to_markdown.return_value = "Chunk content"

    # First call: get page count (returns all pages)
    mock_result_full = Mock()
    mock_result_full.document = mock_document
    mock_result_full.document.pages = {1: Mock(), 2: Mock(), 3: Mock()}

    # Subsequent calls: return chunks
    mock_result_chunk1 = Mock()
    mock_result_chunk1.document = Mock()
    mock_result_chunk1.document.export_to_markdown.return_value = "Chunk 1-2 content"

    mock_result_chunk2 = Mock()
    mock_result_chunk2.document = Mock()
    mock_result_chunk2.document.export_to_markdown.return_value = "Chunk 3 content"

    mock_converter = Mock()
    # First call gets page count, then chunk conversions
    mock_converter.convert.side_effect = [
        mock_result_full,  # Get total pages
        mock_result_chunk1,  # Chunk 1-2
        mock_result_chunk2,  # Chunk 3
    ]

    # Mock sys.modules to inject our mock DocumentConverter
    mock_docling_module = Mock()
    mock_docling_module.DocumentConverter = Mock(return_value=mock_converter)

    with patch.dict("sys.modules", {"docling.document_converter": mock_docling_module}):
        # Create a fake PDF path
        pdf_path = Path("test.pdf")

        # Mock path.exists() to return True
        with patch.object(Path, "exists", return_value=True):
            # Process with chunk_pages=2
            docs = list(load_pdf_streaming(pdf_path, chunk_pages=2))

        # Should yield 2 documents (one per chunk)
        assert len(docs) == 2

        # Check first document (chunk 1-2)
        assert docs[0].page_content == "Chunk 1-2 content"
        assert docs[0].metadata["page_range"] == "1-2"
        assert docs[0].metadata["total_pages"] == 3
        assert docs[0].metadata["chunk_size"] == 2

        # Check second document (chunk 3)
        assert docs[1].page_content == "Chunk 3 content"
        assert docs[1].metadata["page_range"] == "3-3"


def test_load_pdf_streaming_skips_empty_pages():
    """Test that empty chunks are skipped."""
    from app.ingestion.utils.streaming_pdf_loader import load_pdf_streaming

    # Mock docling components
    mock_document = Mock()
    mock_document.pages = {1: Mock(), 2: Mock(), 3: Mock()}

    # First call: get page count
    mock_result_full = Mock()
    mock_result_full.document = Mock()
    mock_result_full.document.pages = {1: Mock(), 2: Mock(), 3: Mock()}

    # Chunk 1: has content
    mock_result_chunk1 = Mock()
    mock_result_chunk1.document = Mock()
    mock_result_chunk1.document.export_to_markdown.return_value = "Chunk 1 content"

    # Chunk 2: empty
    mock_result_chunk2 = Mock()
    mock_result_chunk2.document = Mock()
    mock_result_chunk2.document.export_to_markdown.return_value = ""

    # Chunk 3: has content
    mock_result_chunk3 = Mock()
    mock_result_chunk3.document = Mock()
    mock_result_chunk3.document.export_to_markdown.return_value = "Chunk 3 content"

    mock_converter = Mock()
    mock_converter.convert.side_effect = [
        mock_result_full,
        mock_result_chunk1,
        mock_result_chunk2,
        mock_result_chunk3,
    ]

    mock_docling_module = Mock()
    mock_docling_module.DocumentConverter = Mock(return_value=mock_converter)

    with patch.dict("sys.modules", {"docling.document_converter": mock_docling_module}):
        pdf_path = Path("test.pdf")
        with patch.object(Path, "exists", return_value=True):
            docs = list(load_pdf_streaming(pdf_path, chunk_pages=1))

        # Should only yield 2 documents (empty chunk skipped)
        assert len(docs) == 2
        assert docs[0].page_content == "Chunk 1 content"
        assert docs[1].page_content == "Chunk 3 content"


def test_load_pdf_streaming_handles_missing_file():
    """Test that missing file is handled gracefully."""
    from app.ingestion.utils.streaming_pdf_loader import load_pdf_streaming

    mock_docling_module = Mock()
    mock_docling_module.DocumentConverter = Mock()

    with patch.dict("sys.modules", {"docling.document_converter": mock_docling_module}):
        pdf_path = Path("/nonexistent/file.pdf")
        docs = list(load_pdf_streaming(pdf_path))

        # Should return empty iterator
        assert len(docs) == 0


def test_load_pdf_streaming_handles_docling_import_error():
    """Test that missing docling dependency is handled."""
    # We need to test this by mocking sys.modules before import
    import importlib
    import sys

    # Save original modules
    original_docling = sys.modules.get("docling")
    original_converter = sys.modules.get("docling.document_converter")

    try:
        # Remove the modules to simulate ImportError
        if "docling.document_converter" in sys.modules:
            del sys.modules["docling.document_converter"]
        if "docling" in sys.modules:
            del sys.modules["docling"]

        # Mock the module to raise ImportError
        sys.modules["docling"] = None
        sys.modules["docling.document_converter"] = None

        # Force reimport of the streaming_pdf_loader module
        from app.ingestion.utils import streaming_pdf_loader

        importlib.reload(streaming_pdf_loader)

        pdf_path = Path("test.pdf")
        with patch.object(Path, "exists", return_value=True):
            docs = list(streaming_pdf_loader.load_pdf_streaming(pdf_path))

        # Should return empty iterator due to ImportError
        assert len(docs) == 0
    finally:
        # Restore original state - critical for test isolation
        if "docling.document_converter" in sys.modules:
            del sys.modules["docling.document_converter"]
        if "docling" in sys.modules:
            del sys.modules["docling"]

        if original_converter is not None:
            sys.modules["docling.document_converter"] = original_converter
        if original_docling is not None:
            sys.modules["docling"] = original_docling

        # Reload the module again to restore normal state
        from app.ingestion.utils import streaming_pdf_loader

        importlib.reload(streaming_pdf_loader)


def test_load_pdf_streaming_continues_on_page_error():
    """Test that processing continues if one chunk fails."""
    from app.ingestion.utils.streaming_pdf_loader import load_pdf_streaming

    # Mock docling components
    mock_document = Mock()
    mock_document.pages = {1: Mock(), 2: Mock(), 3: Mock()}

    # First call: get page count
    mock_result_full = Mock()
    mock_result_full.document = Mock()
    mock_result_full.document.pages = {1: Mock(), 2: Mock(), 3: Mock()}

    # Chunk 1: success
    mock_result_chunk1 = Mock()
    mock_result_chunk1.document = Mock()
    mock_result_chunk1.document.export_to_markdown.return_value = "Chunk 1 content"

    # Chunk 2: error
    mock_result_chunk2 = Mock()
    mock_result_chunk2.document = Mock()
    mock_result_chunk2.document.export_to_markdown.side_effect = Exception("Chunk error")

    # Chunk 3: success
    mock_result_chunk3 = Mock()
    mock_result_chunk3.document = Mock()
    mock_result_chunk3.document.export_to_markdown.return_value = "Chunk 3 content"

    mock_converter = Mock()
    mock_converter.convert.side_effect = [
        mock_result_full,
        mock_result_chunk1,
        mock_result_chunk2,
        mock_result_chunk3,
    ]

    mock_docling_module = Mock()
    mock_docling_module.DocumentConverter = Mock(return_value=mock_converter)

    with patch.dict("sys.modules", {"docling.document_converter": mock_docling_module}):
        pdf_path = Path("test.pdf")
        with patch.object(Path, "exists", return_value=True):
            docs = list(load_pdf_streaming(pdf_path, chunk_pages=1))

        # Should yield 2 documents (error chunk skipped)
        assert len(docs) == 2
        assert docs[0].page_content == "Chunk 1 content"
        assert docs[1].page_content == "Chunk 3 content"


def test_load_pdf_streaming_is_iterator():
    """Test that function returns an iterator, not a list."""
    from app.ingestion.utils.streaming_pdf_loader import load_pdf_streaming

    mock_document = Mock()
    mock_document.pages = {1: Mock()}

    mock_result = Mock()
    mock_result.document = mock_document

    mock_result_chunk = Mock()
    mock_result_chunk.document = Mock()
    mock_result_chunk.document.export_to_markdown.return_value = "Content"

    mock_converter = Mock()
    mock_converter.convert.side_effect = [mock_result, mock_result_chunk]

    mock_docling_module = Mock()
    mock_docling_module.DocumentConverter = Mock(return_value=mock_converter)

    with patch.dict("sys.modules", {"docling.document_converter": mock_docling_module}):
        pdf_path = Path("test.pdf")
        with patch.object(Path, "exists", return_value=True):
            result = load_pdf_streaming(pdf_path)

            # Should be a generator/iterator
            assert hasattr(result, "__iter__")
            assert hasattr(result, "__next__")
