"""The regulation texts that ship with the application, and how they reach the shared corpus.

The compliance specialist's gap analysis cites the text of a law or marks the
clause 无法判断, so these files are what makes it answer rather than decline.
What must hold: they are the texts they claim to be (article counts against the
official structure, a source line on each), they reach the backend image, init
copies them without ever overwriting an administrator's copy, and once placed
they are labelled compliance by their folder.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.agents.catalog import AgentClass
from app.services.documents import bundled_corpus
from app.services.documents.bundled_corpus import (
    BUNDLED_ROOT,
    bundled_files,
    index_bundled_corpus,
    install_bundled_corpus,
)
from app.services.documents.domain_labels import folder_label

REPO = Path(__file__).resolve().parents[2]
COMPLIANCE = BUNDLED_ROOT / "compliance"

# Articles in each text, as the official versions number them. The 2025
# amendment added two articles to the Cybersecurity Law (79 -> 81).
EXPECTED_ARTICLES = {
    "中华人民共和国网络安全法.md": 81,
    "中华人民共和国数据安全法.md": 55,
    "中华人民共和国个人信息保护法.md": 74,
    "GDPR-Regulation-EU-2016-679.md": 99,
}
# Each article heading names its law: a chunk holding one article must still say
# which law it is, or a question naming the law matches the title block instead.
_CN_ARTICLE = re.compile(r"^#### \S{2,12}法 第[一二三四五六七八九十百零]+条$", re.MULTILINE)
_EU_ARTICLE = re.compile(r"^#### GDPR Article \d{1,3} -- ", re.MULTILINE)


def test_the_four_regulations_ship() -> None:
    assert sorted(path.name for path in COMPLIANCE.iterdir()) == sorted(EXPECTED_ARTICLES)


@pytest.mark.parametrize(("name", "articles"), sorted(EXPECTED_ARTICLES.items()))
def test_each_text_is_complete(name: str, articles: int) -> None:
    text = (COMPLIANCE / name).read_text(encoding="utf-8")
    pattern = _EU_ARTICLE if name.startswith("GDPR") else _CN_ARTICLE

    assert len(pattern.findall(text)) == articles


@pytest.mark.parametrize("name", sorted(EXPECTED_ARTICLES))
def test_each_text_names_its_source_and_says_the_official_text_prevails(name: str) -> None:
    header = (COMPLIANCE / name).read_text(encoding="utf-8")[:1200]

    assert re.search(r"https?://\S+\.(?:gov\.cn|europa\.eu)", header), "no official source URL"
    assert ("以官方公布文本为准" in header) or ("Only the Official Journal text is authentic" in header)


def test_the_cybersecurity_law_is_the_2025_amended_text() -> None:
    header = (COMPLIANCE / "中华人民共和国网络安全法.md").read_text(encoding="utf-8")[:600]
    assert "2025年10月28日" in header and "修正" in header


def test_the_texts_reach_the_backend_image() -> None:
    """`.dockerignore` drops `*.md`; the corpus needs its exception after that line."""

    lines = [line.strip() for line in (REPO / ".dockerignore").read_text(encoding="utf-8").splitlines()]
    assert "!config/corpus/**" in lines
    assert lines.index("!config/corpus/**") > lines.index("*.md"), "an exception before *.md is overridden by it"


# --- install -----------------------------------------------------------------------------


def _bundle(tmp_path: Path) -> Path:
    root = tmp_path / "bundle"
    (root / "compliance").mkdir(parents=True)
    (root / "compliance" / "law.md").write_text("# law\n", encoding="utf-8")
    (root / "compliance" / "gdpr.md").write_text("# gdpr\n", encoding="utf-8")
    return root


def test_install_copies_what_is_missing(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    report = install_bundled_corpus(docs, _bundle(tmp_path))

    assert sorted(path.name for path in report.copied) == ["gdpr.md", "law.md"]
    assert (docs / "compliance" / "law.md").read_text(encoding="utf-8") == "# law\n"
    assert not list(docs.rglob(".*.partial"))


def test_install_never_overwrites_an_administrators_copy(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    (docs / "compliance").mkdir(parents=True)
    (docs / "compliance" / "law.md").write_text("edited by an administrator\n", encoding="utf-8")

    report = install_bundled_corpus(docs, _bundle(tmp_path))

    assert [path.name for path in report.kept] == ["law.md"]
    assert (docs / "compliance" / "law.md").read_text(encoding="utf-8") == "edited by an administrator\n"


def test_install_twice_copies_nothing_the_second_time(tmp_path: Path) -> None:
    docs, root = tmp_path / "docs", _bundle(tmp_path)
    install_bundled_corpus(docs, root)

    assert install_bundled_corpus(docs, root).copied == []


def test_no_bundle_is_no_work(tmp_path: Path) -> None:
    assert bundled_files(tmp_path / "missing") == []


def test_an_installed_text_is_labelled_compliance(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    install_bundled_corpus(docs, _bundle(tmp_path))

    assert folder_label(str(docs / "compliance" / "law.md"), str(docs.resolve())) == AgentClass.COMPLIANCE


# --- index -------------------------------------------------------------------------------


@pytest.fixture
def ingested(monkeypatch: pytest.MonkeyPatch) -> list[list[Path]]:
    calls: list[list[Path]] = []
    import app.services.documents.ingest as ingest

    monkeypatch.setattr(ingest, "ingest_paths", lambda paths: calls.append(list(paths)))
    return calls


def test_index_takes_only_what_the_corpus_does_not_hold(tmp_path: Path, monkeypatch, ingested) -> None:
    docs = tmp_path / "docs"
    monkeypatch.setattr(bundled_corpus, "_indexed_sources", lambda: {str((docs / "compliance" / "law.md").resolve())})

    report = index_bundled_corpus(docs, root=_bundle(tmp_path))

    assert [[path.name for path in call] for call in ingested] == [["gdpr.md"]]
    assert [path.name for path in report.already_indexed] == ["law.md"]


def test_force_reindexes_everything(tmp_path: Path, monkeypatch, ingested) -> None:
    docs = tmp_path / "docs"
    monkeypatch.setattr(bundled_corpus, "_indexed_sources", lambda: {"anything"})

    index_bundled_corpus(docs, force=True, root=_bundle(tmp_path))

    assert [sorted(path.name for path in call) for call in ingested] == [["gdpr.md", "law.md"]]


def test_nothing_to_index_calls_no_ingest(tmp_path: Path, monkeypatch, ingested) -> None:
    docs, root = tmp_path / "docs", _bundle(tmp_path)
    held = {str((docs / "compliance" / name).resolve()) for name in ("law.md", "gdpr.md")}
    monkeypatch.setattr(bundled_corpus, "_indexed_sources", lambda: held)

    index_bundled_corpus(docs, root=root)

    assert ingested == []
