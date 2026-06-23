"""Document loaders for various file types.

This module provides a unified interface for loading documents from different file formats.
Supported formats: PDF, images (PNG, JPG, etc.), and text files.
"""

import logging
from pathlib import Path

from langchain_core.documents import Document

from app.core.config import get_settings
from app.ingestion.loaders.image_loader import load_image_file
from app.ingestion.loaders.pdf_loader import load_pdf_enhanced, load_pdf_image_ocr, load_pdf_text, load_pdf_with_docling
from app.ingestion.loaders.text_loader import load_text_file

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp", ".gif"}
TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".log", ".json", ".yaml", ".yml", ".toml", ".ini"}
SUPPORTED_EXTENSIONS = {".pdf", *IMAGE_EXTENSIONS, *TEXT_EXTENSIONS}


def _extract_charts_once(path: Path, settings) -> list[Document]:
    """
    Extract charts from PDF exactly once.

    This helper ensures charts are extracted only once regardless of fallback chain.

    Args:
        path: Path to PDF file
        settings: Application settings

    Returns:
        List of chart documents, or empty list on failure
    """
    try:
        from app.ingestion.loaders.pdf_chart_loader import extract_charts_from_pdf

        chart_docs = extract_charts_from_pdf(path, use_vision=True, vision_model=settings.pdf_chart_vision_model)

        if chart_docs:
            logger.info(f"Extracted {len(chart_docs)} charts from {path.name}")

        return chart_docs

    except Exception as e:
        logger.error(f"Chart extraction failed for {path.name}: {e}")
        return []


def _load_pdf_with_mode(path: Path, pdf_mode: str, settings) -> list[Document]:
    """
    Load PDF text content with fallback chain (no chart extraction).

    This helper separates text loading from chart extraction to avoid duplication.

    Args:
        path: Path to PDF file
        pdf_mode: PDF processing mode
        settings: Application settings

    Returns:
        List of text documents
    """
    if pdf_mode == "docling_advanced":
        # Try advanced processing
        try:
            from app.ingestion.loaders.pdf_loader_advanced import load_pdf_advanced

            advanced_docs = load_pdf_advanced(
                path,
                by_page=True,
                enable_structure=settings.pdf_enable_structure_analysis,
                enable_coreference=settings.pdf_enable_coreference,
                enable_formula_enrichment=settings.pdf_enable_formula_enrichment,
                enable_cleaning=settings.pdf_enable_cleaning,
                enable_table_merging=settings.pdf_enable_table_merging,
            )

            if advanced_docs:
                logger.info(f"Loaded {path.name} with advanced processing")
                return advanced_docs

        except Exception as e:
            logger.warning(f"Advanced processing failed for {path.name}: {e}")

        # Fallback to enhanced
        enhanced_docs = load_pdf_enhanced(
            path,
            by_page=True,
            enable_cleaning=settings.pdf_enable_cleaning,
            enable_table_merging=settings.pdf_enable_table_merging,
        )
        if enhanced_docs:
            logger.info(f"Loaded {path.name} with enhanced processing (fallback)")
            return enhanced_docs

        # Final fallback to pypdf
        logger.warning(f"Using pypdf fallback for {path.name}")
        return load_pdf_text(path)

    elif pdf_mode == "docling_enhanced":
        # Try enhanced processing
        enhanced_docs = load_pdf_enhanced(
            path,
            by_page=True,
            enable_cleaning=settings.pdf_enable_cleaning,
            enable_table_merging=settings.pdf_enable_table_merging,
            enable_nested_table_handling=True,  # Always enabled for enhanced mode
        )
        if enhanced_docs:
            logger.info(f"Loaded {path.name} with enhanced processing")
            return enhanced_docs

        # Fallback to regular docling
        docling_docs = load_pdf_with_docling(path, by_page=True)
        if docling_docs:
            logger.info(f"Loaded {path.name} with docling (fallback)")
            return docling_docs

        # Final fallback to pypdf
        logger.warning(f"Using pypdf fallback for {path.name}")
        return load_pdf_text(path)

    elif pdf_mode == "docling":
        # Try docling
        docling_docs = load_pdf_with_docling(path, by_page=True)
        if docling_docs:
            logger.info(f"Loaded {path.name} with docling")
            return docling_docs

        # Fallback to pypdf
        logger.warning(f"Using pypdf fallback for {path.name}")
        return load_pdf_text(path)

    elif pdf_mode == "hybrid":
        # Docling + OCR
        docling_docs = load_pdf_with_docling(path, by_page=True)
        ocr_docs = load_pdf_image_ocr(path)

        if docling_docs:
            logger.info(f"Loaded {path.name} with hybrid mode (docling + OCR)")
            return docling_docs + ocr_docs

        # Fallback to pypdf + OCR
        logger.warning(f"Using pypdf + OCR fallback for {path.name}")
        text_docs = load_pdf_text(path)
        return text_docs + ocr_docs

    else:  # pypdf (default)
        # Traditional approach
        logger.info(f"Loaded {path.name} with pypdf mode")
        text_docs = load_pdf_text(path)
        ocr_docs = load_pdf_image_ocr(path)
        return text_docs + ocr_docs


def _load_single_path(path: Path) -> list[Document]:
    """Load documents from a single file path."""
    if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return []

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        settings = get_settings()
        pdf_mode = settings.pdf_loader_mode.lower()

        # Step 1: Load text content with fallback chain
        text_docs = _load_pdf_with_mode(path, pdf_mode, settings)

        # Step 2: Extract charts exactly once (if enabled and text loading succeeded)
        if text_docs and settings.pdf_enable_chart_extraction:
            chart_docs = _extract_charts_once(path, settings)
            return text_docs + chart_docs

        return text_docs

    if suffix in IMAGE_EXTENSIONS:
        return load_image_file(path)

    return load_text_file(path)


def load_documents(data_dir: Path | None = None, paths: list[Path] | None = None) -> list[Document]:
    """Load documents from directory or specific paths.

    Args:
        data_dir: Directory to recursively load documents from
        paths: Specific file paths to load

    Returns:
        List of loaded Document objects
    """
    docs: list[Document] = []
    if paths is not None:
        for path in paths:
            docs.extend(_load_single_path(path))
        return docs

    if data_dir is None:
        return docs

    for path in data_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        docs.extend(_load_single_path(path))
    return docs


# Backward compatibility exports
__all__ = [
    "load_documents",
    "IMAGE_EXTENSIONS",
    "TEXT_EXTENSIONS",
    "SUPPORTED_EXTENSIONS",
]
