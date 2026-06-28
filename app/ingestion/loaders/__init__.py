"""Document loaders by file type."""

import importlib.util
from pathlib import Path

from langchain_core.documents import Document

_loaders_file = str(Path(__file__).parent.parent / "loaders.py")
_spec = importlib.util.spec_from_file_location("app.ingestion._loaders_impl", _loaders_file)
loaders_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(loaders_module)

from app.ingestion.loaders.image_loader import load_image_file
from app.ingestion.loaders.pdf_loader import load_pdf_image_ocr, load_pdf_text
from app.ingestion.loaders.text_loader import load_text_file
from app.ingestion.utils.ocr_utils import normalize_ocr_text, parse_psm_modes
from app.ingestion.utils.people_detection import build_people_summary, detect_people_in_image
from app.ingestion.utils.vision_utils import build_vision_summary, describe_image_with_vision

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp", ".gif"}
TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".log", ".json", ".yaml", ".yml", ".toml", ".ini"}
SUPPORTED_EXTENSIONS = {".pdf", *IMAGE_EXTENSIONS, *TEXT_EXTENSIONS}

_load_pdf_text = load_pdf_text
_load_pdf_image_ocr = load_pdf_image_ocr
_load_image_file = load_image_file
_parse_psm_modes = parse_psm_modes
_normalize_ocr_text = normalize_ocr_text
_detect_people_in_image = detect_people_in_image
_build_people_summary = build_people_summary
_describe_image_with_vision = describe_image_with_vision
_build_vision_summary = build_vision_summary


def _sync_compat_aliases() -> None:
    """Mirror package-level monkeypatches into the implementation module."""
    loaders_module._load_pdf_text = _load_pdf_text
    loaders_module._load_pdf_image_ocr = _load_pdf_image_ocr
    loaders_module._load_image_file = _load_image_file
    loaders_module._load_text_file = load_text_file


def _load_single_path(path: Path) -> list[Document]:
    """Load a single supported file into LangChain documents."""
    _sync_compat_aliases()
    return loaders_module._load_single_path(path)


def load_documents(data_dir: Path | None = None, paths: list[Path] | None = None) -> list[Document]:
    """Compatibility loader used by ingestion services."""
    _sync_compat_aliases()
    return loaders_module.load_documents(data_dir=data_dir, paths=paths)


__all__ = [
    "load_documents",
    "load_pdf_text",
    "load_pdf_image_ocr",
    "load_image_file",
    "load_text_file",
    "_load_pdf_text",
    "_load_pdf_image_ocr",
    "_load_image_file",
    "_parse_psm_modes",
    "_normalize_ocr_text",
    "_detect_people_in_image",
    "_build_people_summary",
    "_describe_image_with_vision",
    "_build_vision_summary",
    "IMAGE_EXTENSIONS",
    "TEXT_EXTENSIONS",
    "SUPPORTED_EXTENSIONS",
]
