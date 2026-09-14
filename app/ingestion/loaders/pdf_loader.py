"""PDF document loader."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

try:
    from langchain_community.document_loaders import PyPDFLoader  # type: ignore
except ImportError:
    PyPDFLoader = None  # type: ignore[assignment]
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


def load_pdf_text(path: Path) -> list[Document]:
    """Load text content from PDF using PyPDFLoader."""
    if PyPDFLoader is None:
        logger.warning(f"PyPDF loading unavailable for {path.name}: langchain_community not installed")
        return []
    try:
        loader = PyPDFLoader(str(path))
        return loader.load()
    except Exception as e:
        logger.exception(f"PyPDF loading failed for {path.name}: {e}")
        return []


def load_pdf_enhanced(
    path: Path,
    by_page: bool = True,
    enable_cleaning: bool = True,
    enable_table_merging: bool = True,
    enable_nested_table_handling: bool = True,
) -> list[Document]:
    """Load PDF with enhanced processing, forwarding the processing switches.

    This wrapper took only `path` and `by_page` and forwarded only those, while
    `dispatch.py` called it with `enable_cleaning`, `enable_table_merging` and
    `enable_nested_table_handling` -- so `PDF_LOADER_MODE=docling_enhanced` and
    `docling_advanced` raised `TypeError` on the first PDF, and
    `PDF_ENABLE_CLEANING` / `PDF_ENABLE_TABLE_MERGING` were settings nothing
    could act on. The implementation underneath has supported all three from the
    start (`pdf_loader_enhanced.load_pdf_enhanced`), and `pdf_loader_advanced`
    calls it that way directly; only this forwarding layer dropped them.

    Note what the fallbacks cannot carry: `load_pdf_with_docling` has no such
    switches, so a deployment that loses the enhanced loader silently gets
    unprocessed output. That is a narrower version of the same problem and is
    logged rather than hidden.
    """

    try:
        from app.ingestion.loaders.pdf_loader_enhanced import load_pdf_enhanced as _load_enhanced

        docs = _load_enhanced(
            path,
            by_page,
            enable_cleaning=enable_cleaning,
            enable_table_merging=enable_table_merging,
            enable_nested_table_handling=enable_nested_table_handling,
        )
        if docs:
            return docs
    except ImportError as e:
        logger.warning("Enhanced loader not available (%s); falling back to docling without cleaning", e)
    except Exception as e:
        logger.exception(f"Enhanced loading failed for {path.name}: {e}")
        logger.warning("Falling back to docling for %s; cleaning and table merging will not run", path.name)

    return load_pdf_with_docling(path, by_page)


def _extract_docling_pages_content(document: Any) -> list[str]:
    """Extract per-page markdown content from a Docling document.

    Supports:
    1. Legacy/mock objects where items in document.pages have .export_to_markdown()
    2. Docling v2 where document.pages is dict[int, PageItem] and export_to_markdown
       is called on document with page_break_placeholder.
    3. Single-page fallback where document.export_to_markdown() returns full markdown.
    """
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
        except (TypeError, Exception):
            full_md = document.export_to_markdown()

        if full_md and full_md.strip():
            if PAGE_BREAK in full_md:
                for part in full_md.split(PAGE_BREAK):
                    if part and part.strip():
                        pages_content.append(part.strip())
            else:
                pages_content.append(full_md.strip())

    return pages_content


def load_pdf_with_docling(path: Path, by_page: bool = True) -> list[Document]:
    """Load PDF using Docling with Markdown conversion (preserves tables)."""
    try:
        from docling.document_converter import DocumentConverter  # type: ignore
    except ImportError as e:
        logger.warning(f"Docling not available: {e}")
        return []

    try:
        converter = DocumentConverter()
        result = converter.convert(str(path))

        if not by_page:
            markdown_content = result.document.export_to_markdown()
            metadata: dict[str, Any] = {
                "source": str(path),
                "format": "markdown",
                "converter": "docling",
            }
            if hasattr(result.document, "pages") and result.document.pages:
                metadata["total_pages"] = len(result.document.pages)
            return [
                Document(
                    page_content=markdown_content,
                    metadata=metadata,
                )
            ]

        pages_content = _extract_docling_pages_content(result.document)
        docs = [
            Document(
                page_content=page_markdown,
                metadata={
                    "source": str(path),
                    "page": page_idx,
                    "format": "markdown",
                    "converter": "docling",
                },
            )
            for page_idx, page_markdown in enumerate(pages_content, start=1)
        ]

        if not docs:
            logger.warning(f"No content extracted from {path.name} using Docling")
        return docs
    except Exception as e:
        logger.exception(f"Docling conversion failed for {path.name}: {e}")
        return []


def load_pdf_image_ocr(path: Path) -> list[Document]:
    """Extract and OCR images from PDF pages."""
    try:
        from pypdf import PdfReader
    except ImportError as e:
        logger.warning(f"pypdf not available for image OCR: {e}")
        return []

    from app.ingestion.extraction.ocr_enhanced import ocr_image_bytes_with_structure

    docs: list[Document] = []
    try:
        reader = PdfReader(str(path))
    except Exception as e:
        logger.warning(f"Failed to read PDF for image OCR {path}: {e}")
        return docs

    for page_idx, page in enumerate(reader.pages, start=1):
        try:
            images = list(page.images or [])
        except (AttributeError, TypeError) as e:
            logger.debug(f"Failed to extract images from page {page_idx}: {e}")
            images = []
        for img_idx, img_obj in enumerate(images, start=1):
            img_bytes = getattr(img_obj, "data", None)
            if not img_bytes:
                continue
            docs.extend(ocr_image_bytes_with_structure(img_bytes, source=path, page=page_idx, image_index=img_idx))
    return docs
