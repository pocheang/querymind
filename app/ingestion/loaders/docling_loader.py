"""Docling-based PDF to Markdown loader with table preservation."""

from pathlib import Path

from langchain_core.documents import Document


def load_pdf_with_docling(path: Path) -> list[Document]:
    """Load PDF and convert to Markdown using Docling.

    Docling preserves table structure by converting them to Markdown tables,
    which improves knowledge graph extraction quality.

    Args:
        path: Path to PDF file

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

        # Get Markdown export
        markdown_content = result.document.export_to_markdown()

        # Create a single document with full Markdown content
        doc = Document(
            page_content=markdown_content,
            metadata={
                "source": str(path),
                "format": "markdown",
                "converter": "docling",
            }
        )

        return [doc]

    except Exception:
        return []


def load_pdf_with_docling_by_page(path: Path) -> list[Document]:
    """Load PDF with Docling and split by pages.

    Returns one Document per page, preserving page numbers for citation.

    Args:
        path: Path to PDF file

    Returns:
        List of Document objects, one per page
    """
    try:
        from docling.document_converter import DocumentConverter
    except ImportError:
        return []

    try:
        converter = DocumentConverter()
        result = converter.convert(str(path))

        docs: list[Document] = []

        # Iterate through pages
        for page_idx, page in enumerate(result.document.pages, start=1):
            # Export page to Markdown
            page_markdown = page.export_to_markdown()

            if not page_markdown or not page_markdown.strip():
                continue

            doc = Document(
                page_content=page_markdown,
                metadata={
                    "source": str(path),
                    "page": page_idx,
                    "format": "markdown",
                    "converter": "docling",
                }
            )
            docs.append(doc)

        return docs

    except Exception:
        return []
