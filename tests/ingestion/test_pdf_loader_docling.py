"""Tests for Docling PDF loading and page extraction in pdf_loader and pdf_loader_enhanced."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from app.ingestion.loaders.pdf_loader import (
    _extract_docling_pages_content,
    load_pdf_enhanced,
    load_pdf_with_docling,
)
from app.ingestion.loaders.pdf_loader_enhanced import _extract_pages_content


class DummyPageItem:
    """Represents a Docling v2 PageItem (only has page_no and size, no export_to_markdown)."""

    def __init__(self, page_no: int):
        self.page_no = page_no


class DummyDoclingV2Document:
    """Represents a Docling v2 DoclingDocument where pages is a dict and markdown is exported on document."""

    def __init__(self, pages_text: list[str]):
        self.pages = {i: DummyPageItem(i) for i in range(1, len(pages_text) + 1)}
        self._pages_text = pages_text

    def export_to_markdown(self, page_break_placeholder: str | None = None) -> str:
        if page_break_placeholder:
            return f"\n{page_break_placeholder}\n".join(self._pages_text)
        return "\n\n".join(self._pages_text)


class DummyLegacyPage:
    """Represents a legacy Docling v1 Page object with export_to_markdown."""

    def __init__(self, content: str):
        self._content = content

    def export_to_markdown(self) -> str:
        return self._content


class DummyLegacyDocument:
    """Represents a legacy Docling document where pages is a list of Page objects."""

    def __init__(self, pages: list[DummyLegacyPage]):
        self.pages = pages


def test_extract_docling_pages_content_docling_v2():
    """Docling v2 has pages as dict and export_to_markdown on document."""
    doc = DummyDoclingV2Document(["# Page 1 Table\n| A | B |\n|---|---|\n| 1 | 2 |", "Page 2 Content"])
    pages = _extract_docling_pages_content(doc)
    assert len(pages) == 2
    assert "Page 1 Table" in pages[0]
    assert "Page 2 Content" in pages[1]


def test_extract_docling_pages_content_legacy():
    """Legacy or mock has pages as list of objects with export_to_markdown."""
    doc = DummyLegacyDocument([DummyLegacyPage("Legacy Page 1"), DummyLegacyPage("Legacy Page 2")])
    pages = _extract_docling_pages_content(doc)
    assert len(pages) == 2
    assert pages[0] == "Legacy Page 1"
    assert pages[1] == "Legacy Page 2"


def test_extract_pages_content_enhanced_matches():
    """_extract_pages_content in pdf_loader_enhanced handles Docling v2 without crashing."""
    doc = DummyDoclingV2Document(["Section 1", "Section 2"])
    pages = _extract_pages_content(doc)
    assert len(pages) == 2
    assert pages[0] == "Section 1"
    assert pages[1] == "Section 2"


def test_load_pdf_with_docling_by_page_v2():
    """Test load_pdf_with_docling produces correct Documents for Docling v2."""
    mock_doc = DummyDoclingV2Document(["Page 1 Content", "Page 2 Content"])
    mock_result = MagicMock()
    mock_result.document = mock_doc

    mock_converter = MagicMock()
    mock_converter.convert.return_value = mock_result

    mock_module = MagicMock()
    mock_module.DocumentConverter = MagicMock(return_value=mock_converter)

    with patch.dict("sys.modules", {"docling": MagicMock(), "docling.document_converter": mock_module}):
        docs = load_pdf_with_docling(Path("test.pdf"), by_page=True)

    assert len(docs) == 2
    assert docs[0].page_content == "Page 1 Content"
    assert docs[0].metadata["page"] == 1
    assert docs[0].metadata["converter"] == "docling"
    assert docs[1].page_content == "Page 2 Content"
    assert docs[1].metadata["page"] == 2


def test_load_pdf_with_docling_not_by_page_v2():
    """Test load_pdf_with_docling with by_page=False."""
    mock_doc = DummyDoclingV2Document(["Page 1", "Page 2"])
    mock_result = MagicMock()
    mock_result.document = mock_doc

    mock_converter = MagicMock()
    mock_converter.convert.return_value = mock_result

    mock_module = MagicMock()
    mock_module.DocumentConverter = MagicMock(return_value=mock_converter)

    with patch.dict("sys.modules", {"docling": MagicMock(), "docling.document_converter": mock_module}):
        docs = load_pdf_with_docling(Path("test.pdf"), by_page=False)

    assert len(docs) == 1
    assert "Page 1" in docs[0].page_content
    assert "Page 2" in docs[0].page_content
    assert docs[0].metadata["total_pages"] == 2


def test_load_pdf_enhanced_fallback_to_docling_when_empty():
    """When _load_enhanced returns [] due to internal processing error, falls back to docling."""
    with patch("app.ingestion.loaders.pdf_loader_enhanced.load_pdf_enhanced", return_value=[]):
        with patch("app.ingestion.loaders.pdf_loader.load_pdf_with_docling") as mock_fallback:
            mock_fallback.return_value = [MagicMock()]
            res = load_pdf_enhanced(Path("dummy.pdf"))
            assert len(res) == 1
            mock_fallback.assert_called_once_with(Path("dummy.pdf"), True)
