from __future__ import annotations

from pathlib import Path
from typing import Any

from app.agents.catalog import AgentClass, normalize_agent_class
from app.ingestion.loaders import IMAGE_EXTENSIONS


def choose_parser_profile(path: Path, agent_class: str = "general") -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return {
            "name": "pdf_text",
            "loader_hint": "pdf",
            "enable_graph": True,
            "graph_min_confidence": 0.55,
        }
    if suffix in IMAGE_EXTENSIONS:
        return {
            "name": "image_ocr",
            "loader_hint": "image",
            "enable_graph": False,
            "graph_min_confidence": 0.75,
        }
    if normalize_agent_class(agent_class) == AgentClass.COMPLIANCE or "policy" in path.stem.lower():
        return {
            "name": "policy",
            "loader_hint": "text",
            "enable_graph": True,
            "graph_min_confidence": 0.6,
        }
    return {
        "name": "general_text",
        "loader_hint": "text",
        "enable_graph": True,
        "graph_min_confidence": 0.65,
    }
