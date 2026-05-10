"""Document loaders for various file types.

This module provides a unified interface for loading documents from different file formats.
Supported formats: PDF, images (PNG, JPG, etc.), and text files.
"""

from pathlib import Path

from langchain_core.documents import Document

from app.core.config import get_settings
from app.ingestion.loaders.image_loader import load_image_file
from app.ingestion.loaders.pdf_loader import load_pdf_image_ocr, load_pdf_text, load_pdf_with_docling, load_pdf_enhanced
from app.ingestion.loaders.text_loader import load_text_file

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp", ".gif"}
TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".log", ".json", ".yaml", ".yml", ".toml", ".ini"}
SUPPORTED_EXTENSIONS = {".pdf", *IMAGE_EXTENSIONS, *TEXT_EXTENSIONS}


def _load_single_path(path: Path) -> list[Document]:
    """Load documents from a single file path."""
    if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return []

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        settings = get_settings()
        pdf_mode = settings.pdf_loader_mode.lower()

        # Check if chart extraction is enabled
        extract_charts = settings.pdf_enable_chart_extraction

        if pdf_mode == "docling_advanced":
            # Use advanced processing (structure, coreference, formulas)
            from app.ingestion.loaders.pdf_loader_advanced import load_pdf_advanced
            advanced_docs = load_pdf_advanced(
                path,
                by_page=True,
                enable_structure=settings.pdf_enable_structure_analysis,
                enable_coreference=settings.pdf_enable_coreference,
                enable_formula_enrichment=settings.pdf_enable_formula_enrichment
            )
            if advanced_docs:
                if extract_charts:
                    from app.ingestion.loaders.pdf_chart_loader import extract_charts_from_pdf
                    chart_docs = extract_charts_from_pdf(path, use_vision=True, vision_model=settings.pdf_chart_vision_model)
                    return advanced_docs + chart_docs
                return advanced_docs
            # Fallback to enhanced
            enhanced_docs = load_pdf_enhanced(path, by_page=True)
            if enhanced_docs:
                return enhanced_docs
            return load_pdf_text(path)

        elif pdf_mode == "docling_enhanced":
            # Use Docling with advanced processing (cleaning, table merging)
            enhanced_docs = load_pdf_enhanced(path, by_page=True)
            if enhanced_docs:
                # Add chart extraction if enabled
                if extract_charts:
                    from app.ingestion.loaders.pdf_chart_loader import extract_charts_from_pdf
                    chart_docs = extract_charts_from_pdf(path, use_vision=True, vision_model=settings.pdf_chart_vision_model)
                    return enhanced_docs + chart_docs
                return enhanced_docs
            # Fallback to regular Docling
            docling_docs = load_pdf_with_docling(path, by_page=True)
            if docling_docs:
                if extract_charts:
                    from app.ingestion.loaders.pdf_chart_loader import extract_charts_from_pdf
                    chart_docs = extract_charts_from_pdf(path, use_vision=True, vision_model=settings.pdf_chart_vision_model)
                    return docling_docs + chart_docs
                return docling_docs
            # Final fallback to PyPDF
            text_docs = load_pdf_text(path)
            if extract_charts:
                from app.ingestion.loaders.pdf_chart_loader import extract_charts_from_pdf
                chart_docs = extract_charts_from_pdf(path, use_vision=True, vision_model=settings.pdf_chart_vision_model)
                return text_docs + chart_docs
            return text_docs

        elif pdf_mode == "docling":
            # Use Docling only (preserves tables as Markdown)
            docling_docs = load_pdf_with_docling(path, by_page=True)
            if docling_docs:
                if extract_charts:
                    from app.ingestion.loaders.pdf_chart_loader import extract_charts_from_pdf
                    chart_docs = extract_charts_from_pdf(path, use_vision=True, vision_model=settings.pdf_chart_vision_model)
                    return docling_docs + chart_docs
                return docling_docs
            # Fallback to PyPDF if Docling fails
            text_docs = load_pdf_text(path)
            if extract_charts:
                from app.ingestion.loaders.pdf_chart_loader import extract_charts_from_pdf
                chart_docs = extract_charts_from_pdf(path, use_vision=True, vision_model=settings.pdf_chart_vision_model)
                return text_docs + chart_docs
            return text_docs

        elif pdf_mode == "hybrid":
            # Use Docling for text + OCR for images
            docling_docs = load_pdf_with_docling(path, by_page=True)
            ocr_docs = load_pdf_image_ocr(path)
            if docling_docs:
                result = docling_docs + ocr_docs
                if extract_charts:
                    from app.ingestion.loaders.pdf_chart_loader import extract_charts_from_pdf
                    chart_docs = extract_charts_from_pdf(path, use_vision=True, vision_model=settings.pdf_chart_vision_model)
                    return result + chart_docs
                return result
            # Fallback to PyPDF if Docling fails
            text_docs = load_pdf_text(path)
            result = text_docs + ocr_docs
            if extract_charts:
                from app.ingestion.loaders.pdf_chart_loader import extract_charts_from_pdf
                chart_docs = extract_charts_from_pdf(path, use_vision=True, vision_model=settings.pdf_chart_vision_model)
                return result + chart_docs
            return result

        else:  # pypdf (default)
            # Traditional approach
            text_docs = load_pdf_text(path)
            ocr_docs = load_pdf_image_ocr(path)
            result = text_docs + ocr_docs
            if extract_charts:
                from app.ingestion.loaders.pdf_chart_loader import extract_charts_from_pdf
                chart_docs = extract_charts_from_pdf(path, use_vision=True, vision_model=settings.pdf_chart_vision_model)
                return result + chart_docs
            return result

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
