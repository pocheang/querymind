"""Every upload surface must agree with the server, and with itself.

There were FOUR lists and no two of them matched:

* `ChatComposer`'s `accept`  -- `.pdf` and seven image types
* `DocumentsPanel`'s `accept` -- those plus `.md` and `.txt`
* `SUPPORTED_CHAT_RE`        -- what the composer's handler actually keeps
* `SUPPORTED_DOC_RE`         -- what the drop zone's handler actually keeps

and `POST /documents/upload` takes all of those plus `.gif` and four Office
formats. So a `.md` was greyed out in the composer's picker while the hint below
it read "Supports PDF / images / text", and a `.docx` the server would have
indexed could not be chosen anywhere.

The first fix collapsed everything to one list, which was wrong in the other
direction: widening the composer's `accept` to all fifteen made it offer files
that `SUPPORTED_CHAT_RE` then discarded **without a word**. There really are two
sets -- a question is asked *about* a document you look at, and a corpus is
loaded in the Knowledge Base -- so what has to hold is a subset relation, not
equality.

A narrower `accept` is never a safety measure: `store_uploaded_files` validates
the suffix server-side regardless. It is a promise to whoever is choosing a file.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend" / "src"
FORMATS = FRONTEND / "lib" / "uploadFormats.ts"


def _list(name: str) -> set[str]:
    source = FORMATS.read_text(encoding="utf-8")
    block = source[source.index(name) :]
    block = block[: block.index("] as const")]
    return set(re.findall(r'"(\.[a-z0-9]+)"', block))


def _backend_extensions() -> set[str]:
    from app.ingestion.loaders.dispatch import IMAGE_EXTENSIONS
    from app.ingestion.loaders.office_loader import OFFICE_EXTENSIONS

    return {".txt", ".md", ".pdf", *IMAGE_EXTENSIONS, *OFFICE_EXTENSIONS}


def test_the_knowledge_base_offers_exactly_what_the_server_accepts():
    frontend = _list("ACCEPTED_UPLOAD_EXTENSIONS")
    backend = _backend_extensions()

    assert frontend, "the shared list parsed as empty -- this guard would then pass vacuously"
    assert frontend == backend, (
        f"only in the picker: {sorted(frontend - backend)}; only on the server: {sorted(backend - frontend)}"
    )


def test_a_question_may_attach_a_strict_subset():
    """The composer is for documents a reader looks at, and its picker must not
    offer anything its own handler will drop."""

    chat = _list("CHAT_ATTACHMENT_EXTENSIONS")
    everything = _list("ACCEPTED_UPLOAD_EXTENSIONS")

    assert chat, "the chat list parsed as empty"
    assert chat < everything, f"not a strict subset: {sorted(chat - everything)}"
    assert ".pdf" in chat


def test_the_call_site_still_builds_that_set():
    """The backend half is mirrored above, so it has to stay recognisable.

    If the endpoint's literal changes shape, this guard compares the frontend
    against a set nothing uses -- which passes, and means nothing.
    """

    source = (ROOT / "app" / "api" / "routes" / "public" / "documents.py").read_text(encoding="utf-8")

    assert 'supported_suffixes={".txt", ".md", ".pdf", *IMAGE_EXTENSIONS, *OFFICE_EXTENSIONS}' in source


@pytest.mark.parametrize(
    "component",
    [
        "pages/chat/components/ChatComposer.tsx",
        "pages/chat/components/DocumentsPanel.tsx",
        "pages/chat/hooks/useFileUpload.ts",
        "pages/chat/constants.ts",
    ],
)
def test_no_module_hand_writes_its_own_format_list(component: str):
    """Catches a regex copy as well as an `accept` string.

    The first version of this guard checked `accept=` only, and two regexes in
    `useFileUpload` -- the ones that decide what is actually kept -- went on
    disagreeing with it. A list that filters is as much a copy as a list that
    offers.
    """

    source = (FRONTEND / component).read_text(encoding="utf-8")

    assert 'accept=".' not in source, "a hand-written accept list is back"
    # A pipe-separated run of suffixes inside a regex, which is how the two
    # retired ones were written. `PDF_FILE_RE` is deliberately excluded: it
    # answers "does this belong in the PDF workbench", not "may this be
    # uploaded", and the comment above it says so.
    offenders = [
        match
        for match in re.findall(r"/\\\.\(([a-z0-9|?]+)\)\$/i", source)
        if "md" in match or "txt" in match or "docx" in match
    ]
    assert not offenders, f"an upload format list is written out again: {offenders}"


def test_the_matchers_come_from_the_lists():
    """Derived, so a picker and its handler cannot disagree about one file."""

    source = FORMATS.read_text(encoding="utf-8")

    assert "const matcher = (extensions: readonly string[]) =>" in source
    assert "export const UPLOAD_ACCEPT_RE = matcher(ACCEPTED_UPLOAD_EXTENSIONS);" in source
    assert "export const CHAT_ACCEPT_RE = matcher(CHAT_ATTACHMENT_EXTENSIONS);" in source


def test_a_rejected_file_is_named_rather_than_dropped():
    """Warning only when EVERY file was rejected loses the odd one out.

    Dropping a `.docx` beside two PDFs uploaded the PDFs and lost the third with
    no message at all, because each caller tested `if (!files.length)`.
    """

    hook = (FRONTEND / "pages" / "chat" / "hooks" / "useFileUpload.ts").read_text(encoding="utf-8")

    assert "partitionUploads" in hook
    assert "rejected.length" in hook
    assert "if (!files.length) {" not in hook, "the all-or-nothing warning is back"
    # And the three messages go through i18n rather than being English literals.
    assert 'notify("' not in hook
