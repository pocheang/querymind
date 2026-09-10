"""Enhanced PDF loader with advanced processing."""

import logging
from pathlib import Path

from langchain_core.documents import Document

from app.ingestion.extraction.tables import merge_cross_page_tables
from app.ingestion.extraction.tables_nested import simplify_complex_table
from app.ingestion.processing.cleaning import clean_pdf_pages

logger = logging.getLogger(__name__)


def load_pdf_enhanced(
    path: Path,
    by_page: bool = True,
    enable_cleaning: bool = True,
    enable_table_merging: bool = True,
    enable_nested_table_handling: bool = True,
) -> list[Document]:
    """Load PDF with configurable enhanced processing.

    This function uses Docling for Markdown conversion, then applies
    optional processing steps based on configuration.

    Args:
        path: Path to PDF file
        by_page: If True, return one Document per page
        enable_cleaning: Remove headers/footers
        enable_table_merging: Merge cross-page tables
        enable_nested_table_handling: Simplify nested tables

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
        pages_content = _extract_pages_content(result.document)
        if not pages_content:
            logger.warning(f"No content extracted from {path.name}")
            return []

        # Steps 3-5: clean, merge cross-page tables, simplify nested tables (all optional)
        processed_pages = _apply_pdf_processing(
            pages_content, path, enable_cleaning, enable_table_merging, enable_nested_table_handling
        )

        # Step 6: Create Document objects
        metadata_base = {
            "source": str(path),
            "format": "markdown",
            "converter": "docling_enhanced",
            "cleaning_enabled": enable_cleaning,
            "table_merging_enabled": enable_table_merging,
            "nested_table_handling_enabled": enable_nested_table_handling,
        }
        return _build_pdf_documents(processed_pages, metadata_base, by_page)

    except ImportError as e:
        logger.warning(f"Docling not available: {e}")
        return []
    except Exception as e:
        logger.exception(f"Enhanced PDF processing failed for {path.name}: {e}")
        return []


def _extract_pages_content(document) -> list[str]:
    """Read each Docling page's markdown, dropping pages with no content."""
    pages_content = []
    for page in document.pages:
        page_markdown = page.export_to_markdown()
        if page_markdown and page_markdown.strip():
            pages_content.append(page_markdown)
    return pages_content


def _apply_pdf_processing(
    pages_content: list[str],
    path: Path,
    enable_cleaning: bool,
    enable_table_merging: bool,
    enable_nested_table_handling: bool,
) -> list[str]:
    if enable_cleaning:
        pages_content = clean_pdf_pages(pages_content)
        logger.debug(f"Applied cleaning to {path.name}")

    if enable_table_merging:
        pages_content = merge_cross_page_tables(pages_content)
        logger.debug(f"Applied table merging to {path.name}")

    processed_pages = []
    for page_content in pages_content:
        if enable_nested_table_handling:
            page_content = simplify_complex_table(page_content)
        processed_pages.append(page_content)

    if enable_nested_table_handling:
        logger.debug(f"Applied nested table handling to {path.name}")

    return processed_pages


def _build_pdf_documents(processed_pages: list[str], metadata_base: dict, by_page: bool) -> list[Document]:
    if not by_page:
        full_content = "\n\n---\n\n".join(processed_pages)
        return [
            Document(
                page_content=full_content,
                metadata={**metadata_base, "total_pages": len(processed_pages)},
            )
        ]

    return [
        Document(page_content=page_content, metadata={**metadata_base, "page": page_idx})
        for page_idx, page_content in enumerate(processed_pages, start=1)
    ]
