"""The architecture page's API catalog lists only endpoints that exist.

It is a hand-written map in the two locale files, and it drifted the way a map
nobody checks does: it listed `/user/api-settings` (removed), `/query/stream`
(never existed) and the connectors under a prefix they never had. Every line is
now checked against `app.openapi()`, and the two languages must list the same
operations.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.api.main import app

LOCALES = Path(__file__).resolve().parents[2] / "frontend" / "src" / "i18n" / "locales"
_LINE_RE = re.compile(r"^(GET|POST|PUT|PATCH|DELETE)\s+(\S+)\s+-\s+", re.M)


def _catalog(lang: str) -> set[tuple[str, str]]:
    text = json.loads((LOCALES / f"{lang}.json").read_text(encoding="utf-8"))["architecture"]["apiEndpoints"]
    return {(method, path) for method, path in _LINE_RE.findall(text)}


def _operations() -> set[tuple[str, str]]:
    return {(method.upper(), path) for path, ops in app.openapi()["paths"].items() for method in ops}


def test_every_listed_endpoint_exists() -> None:
    real = _operations()
    for lang in ("zh", "en"):
        missing = _catalog(lang) - real
        assert not missing, f"{lang}: listed but not served: {sorted(missing)}"


def test_both_languages_list_the_same_endpoints() -> None:
    assert _catalog("zh") == _catalog("en")


def test_the_catalog_is_read_at_all() -> None:
    # A pattern that silently stopped matching would pass both tests above.
    assert ("POST", "/api/advanced-rag/query") in _catalog("en")
    assert len(_catalog("en")) >= 40
