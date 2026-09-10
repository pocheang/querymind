"""PDF loader with chart extraction support."""

import logging
from pathlib import Path

from langchain_core.documents import Document

from app.core.config import get_settings
from app.ingestion.extraction.charts import (
    chart_data_to_markdown,
    detect_chart_in_image,
    extract_chart_data_with_vision,
)

logger = logging.getLogger(__name__)


def _resolve_vision_api_key(use_vision: bool, vision_model: str, settings) -> str | None:
    if not use_vision:
        return None
    if vision_model.startswith("gpt"):
        api_key = settings.openai_api_key
        if not api_key:
            logger.warning("OpenAI API key not configured, chart extraction will fail")
        return api_key
    if vision_model.startswith("claude"):
        api_key = settings.anthropic_api_key
        if not api_key:
            logger.warning("Anthropic API key not configured, chart extraction will fail")
        return api_key
    return None


def _chart_documents_from_page(
    page, page_idx: int, path: Path, use_vision: bool, vision_model: str, api_key: str | None
) -> list[Document]:
    try:
        images = list(page.images or [])
    except Exception as e:
        logger.warning(f"Failed to extract images from page {page_idx}: {e}")
        return []

    docs = []
    for img_idx, img_obj in enumerate(images, start=1):
        img_bytes = getattr(img_obj, "data", None)
        if not img_bytes:
            continue

        detection = detect_chart_in_image(img_bytes)
        if not detection.get("is_chart"):
            continue

        if use_vision:
            chart_data = extract_chart_data_with_vision(img_bytes, model=vision_model, api_key=api_key)
            chart_text = chart_data_to_markdown(chart_data)
        else:
            chart_text = "[Chart detected but vision extraction disabled]"

        docs.append(
            Document(
                page_content=chart_text,
                metadata={
                    "source": str(path),
                    "page": page_idx,
                    "image_index": img_idx,
                    "modality": "chart",
                    "chart_type": detection.get("chart_type", "unknown"),
                    "detection_confidence": detection.get("confidence", 0.0),
                },
            )
        )
    return docs


def extract_charts_from_pdf(path: Path, use_vision: bool = True, vision_model: str = "gpt-4-vision") -> list[Document]:
    """
    Extract charts from PDF and convert to structured text.

    Args:
        path: Path to PDF file
        use_vision: Use multimodal LLM for chart extraction
        vision_model: Vision model to use (gpt-4-vision, claude-3, etc.)

    Returns:
        List of Document objects with chart data
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        return []

    docs = []
    settings = get_settings()
    api_key = _resolve_vision_api_key(use_vision, vision_model, settings)

    try:
        # Use context manager for proper resource cleanup
        with open(path, "rb") as pdf_file:
            reader = PdfReader(pdf_file)

            for page_idx, page in enumerate(reader.pages, start=1):
                docs.extend(_chart_documents_from_page(page, page_idx, path, use_vision, vision_model, api_key))

    except Exception as e:
        logger.exception(f"PDF chart extraction failed for {path.name}: {e}")
        return docs

    return docs
