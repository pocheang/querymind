"""Enhanced PDF loader with advanced processing."""

from pathlib import Path

from langchain_core.documents import Document

from app.ingestion.utils.nested_table_handler import simplify_complex_table
from app.ingestion.utils.pdf_cleaner import clean_pdf_pages
from app.ingestion.utils.table_merger import merge_cross_page_tables


def load_pdf_enhanced(path: Path, by_page: bool = True) -> list[Document]:
    """Load PDF with enhanced processing (cleaning, table merging, etc).

    This function uses Docling for Markdown conversion, then applies:
    - Header/footer removal
    - Cross-page table merging
    - Nested table flattening
    - Multi-column layout handling

    Args:
        path: Path to PDF file
        by_page: If True, return one Document per page

    Returns:
        List of Document objects with enhanced content
    """
    try:
        from docling.document_converter import DocumentConverter
    except ImportError:
        return []

    try:
        # Step 1: Convert PDF to Markdown using Docling
        converter = DocumentConverter()
        result = converter.convert(str(path))

        # Step 2: Extract page contents
        pages_content = []
        for page_idx, page in enumerate(result.document.pages, start=1):
            page_markdown = page.export_to_markdown()
            if page_markdown and page_markdown.strip():
                pages_content.append(page_markdown)

        if not pages_content:
            return []

        # Step 3: Clean pages (remove headers/footers)
        cleaned_pages = clean_pdf_pages(pages_content)

        # Step 4: Merge cross-page tables
        merged_pages = merge_cross_page_tables(cleaned_pages)

        # Step 5: Simplify complex tables
        processed_pages = []
        for page_content in merged_pages:
            # Simplify nested tables
            simplified = simplify_complex_table(page_content)
            processed_pages.append(simplified)

        # Step 6: Create Document objects
        if not by_page:
            # Single document
            full_content = "\n\n---\n\n".join(processed_pages)
            return [
                Document(
                    page_content=full_content,
                    metadata={
                        "source": str(path),
                        "format": "markdown",
                        "converter": "docling_enhanced",
                        "total_pages": len(processed_pages),
                    },
                )
            ]

        # One document per page
        docs = []
        for page_idx, page_content in enumerate(processed_pages, start=1):
            docs.append(
                Document(
                    page_content=page_content,
                    metadata={
                        "source": str(path),
                        "page": page_idx,
                        "format": "markdown",
                        "converter": "docling_enhanced",
                    },
                )
            )

        return docs

    except Exception:
        return []
