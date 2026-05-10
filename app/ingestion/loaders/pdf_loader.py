"""PDF document loader."""

from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document


def load_pdf_text(path: Path) -> list[Document]:
    """Load text content from PDF using PyPDFLoader."""
    loader = PyPDFLoader(str(path))
    return loader.load()


def load_pdf_enhanced(path: Path, by_page: bool = True) -> list[Document]:
    """Load PDF with enhanced processing (cleaning, table merging, etc).

    This uses Docling + advanced processing:
    - Header/footer removal
    - Cross-page table merging
    - Nested table flattening

    Args:
        path: Path to PDF file
        by_page: If True, return one Document per page

    Returns:
        List of Document objects with enhanced content
    """
    try:
        from app.ingestion.loaders.pdf_loader_enhanced import load_pdf_enhanced as _load_enhanced
        return _load_enhanced(path, by_page)
    except Exception:
        # Fallback to regular Docling
        return load_pdf_with_docling(path, by_page)


def load_pdf_with_docling(path: Path, by_page: bool = True) -> list[Document]:
    """Load PDF using Docling with Markdown conversion (preserves tables).

    Args:
        path: Path to PDF file
        by_page: If True, return one Document per page. If False, return single Document.

    Returns:
        List of Document objects with Markdown-formatted content
    """
    try:
        from docling.document_converter import DocumentConverter
    except ImportError:
        return []

    try:
        converter = DocumentConverter()
        result = converter.convert(str(path))

        if not by_page:
            # Single document with full content
            markdown_content = result.document.export_to_markdown()
            return [Document(
                page_content=markdown_content,
                metadata={
                    "source": str(path),
                    "format": "markdown",
                    "converter": "docling",
                }
            )]

        # One document per page
        docs: list[Document] = []
        for page_idx, page in enumerate(result.document.pages, start=1):
            page_markdown = page.export_to_markdown()
            if page_markdown and page_markdown.strip():
                docs.append(Document(
                    page_content=page_markdown,
                    metadata={
                        "source": str(path),
                        "page": page_idx,
                        "format": "markdown",
                        "converter": "docling",
                    }
                ))
        return docs

    except Exception:
        return []


def load_pdf_image_ocr(path: Path) -> list[Document]:
    """Extract and OCR images from PDF pages."""
    try:
        from pypdf import PdfReader
    except Exception:
        return []

    from app.ingestion.utils.ocr_enhanced import ocr_image_bytes_with_structure

    docs: list[Document] = []
    try:
        reader = PdfReader(str(path))
    except Exception:
        return docs

    for page_idx, page in enumerate(reader.pages, start=1):
        try:
            images = list(page.images or [])
        except Exception:
            images = []
        for img_idx, img_obj in enumerate(images, start=1):
            img_bytes = getattr(img_obj, "data", None)
            if not img_bytes:
                continue
            docs.extend(ocr_image_bytes_with_structure(img_bytes, source=path, page=page_idx, image_index=img_idx))
    return docs
