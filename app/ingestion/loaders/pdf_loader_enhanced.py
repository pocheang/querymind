"""Enhanced PDF loader with advanced processing."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from app.ingestion.extraction.tables import merge_cross_page_tables_with_spans
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
        from docling.document_converter import DocumentConverter  # type: ignore
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

        total_physical_pages = len(pages_content)

        # Steps 3-5: clean, merge cross-page tables, simplify nested tables (all optional)
        processed_pages = _apply_pdf_processing(
            pages_content, path, enable_cleaning, enable_table_merging, enable_nested_table_handling
        )

        # Step 6: Create Document objects
        metadata_base: dict[str, Any] = {
            "source": str(path),
            "format": "markdown",
            "converter": "docling_enhanced",
            "cleaning_enabled": enable_cleaning,
            "table_merging_enabled": enable_table_merging,
            "nested_table_handling_enabled": enable_nested_table_handling,
        }
        return _build_pdf_documents(processed_pages, metadata_base, by_page, total_physical_pages)

    except ImportError as e:
        logger.warning(f"Docling not available: {e}")
        return []
    except Exception as e:
        logger.exception(f"Enhanced PDF processing failed for {path.name}: {e}")
        return []


def _extract_pages_content(document: Any) -> list[str]:
    """Read each Docling page's markdown, dropping pages with no content."""
    pages_content: list[str] = []

    raw_pages = getattr(document, "pages", None)
    if isinstance(raw_pages, (list, tuple)):  # noqa: UP038
        for p in raw_pages:
            if hasattr(p, "export_to_markdown"):
                md = p.export_to_markdown()
                if md and md.strip():
                    pages_content.append(md.strip())
        if pages_content:
            return pages_content
    elif isinstance(raw_pages, dict):
        for p in raw_pages.values():
            if hasattr(p, "export_to_markdown"):
                md = p.export_to_markdown()
                if md and md.strip():
                    pages_content.append(md.strip())
        if pages_content:
            return pages_content

    if hasattr(document, "export_to_markdown"):
        PAGE_BREAK = "<!-- page break -->"
        try:
            full_md = document.export_to_markdown(page_break_placeholder=PAGE_BREAK)
        except Exception:
            full_md = document.export_to_markdown()

        if full_md and full_md.strip():
            if PAGE_BREAK in full_md:
                for part in full_md.split(PAGE_BREAK):
                    if part and part.strip():
                        pages_content.append(part.strip())
            else:
                pages_content.append(full_md.strip())

    return pages_content


def _apply_pdf_processing(
    pages_content: list[str],
    path: Path,
    enable_cleaning: bool,
    enable_table_merging: bool,
    enable_nested_table_handling: bool,
) -> list[tuple[str, list[int]]]:
    if enable_cleaning:
        pages_content = clean_pdf_pages(pages_content)
        logger.debug(f"Applied cleaning to {path.name}")

    if enable_table_merging:
        spanned_pages = merge_cross_page_tables_with_spans(pages_content)
        logger.debug(f"Applied table merging to {path.name}")
    else:
        spanned_pages = [(p, [idx]) for idx, p in enumerate(pages_content, start=1)]

    processed_pages: list[tuple[str, list[int]]] = []
    for page_content, span in spanned_pages:
        if enable_nested_table_handling:
            page_content = simplify_complex_table(page_content)
        processed_pages.append((page_content, span))

    if enable_nested_table_handling:
        logger.debug(f"Applied nested table handling to {path.name}")

    return processed_pages


def _build_pdf_documents(
    processed_pages: list[tuple[str, list[int]]],
    metadata_base: dict[str, Any],
    by_page: bool,
    total_physical_pages: int,
) -> list[Document]:
    if not by_page:
        full_content = "\n\n---\n\n".join(c for c, _ in processed_pages)
        return [
            Document(
                page_content=full_content,
                metadata={**metadata_base, "total_pages": total_physical_pages},
            )
        ]

    return [
        Document(
            page_content=page_content,
            metadata={
                **metadata_base,
                "page": span[0],
                "page_span": span,
                "total_pages": total_physical_pages,
            },
        )
        for page_content, span in processed_pages
    ]
