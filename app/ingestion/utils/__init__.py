"""Utility functions for document ingestion."""

from app.ingestion.utils.ocr_utils import (
    autorotate_image,
    build_ocr_candidates,
    normalize_ocr_text,
    ocr_image_bytes,
    parse_psm_modes,
    run_ocr_with_candidates,
    score_ocr_text,
)
from app.ingestion.utils.people_detection import (
    build_people_summary,
    detect_people_in_image,
)
from app.ingestion.utils.vision_utils import (
    build_vision_summary,
    describe_image_with_vision,
    vision_prompt,
)

__all__ = [
    "ocr_image_bytes",
    "normalize_ocr_text",
    "score_ocr_text",
    "parse_psm_modes",
    "autorotate_image",
    "build_ocr_candidates",
    "run_ocr_with_candidates",
    "describe_image_with_vision",
    "build_vision_summary",
    "vision_prompt",
    "detect_people_in_image",
    "build_people_summary",
]
