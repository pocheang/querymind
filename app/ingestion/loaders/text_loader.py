"""Text file loader."""

from pathlib import Path

try:
    from langchain_community.document_loaders import TextLoader  # type: ignore
except ImportError:
    TextLoader = None  # type: ignore[assignment]
from langchain_core.documents import Document


def load_text_file(path: Path) -> list[Document]:
    """Load text file with encoding fallback."""
    for enc in ("utf-8", "gb18030"):
        try:
            text = path.read_text(encoding=enc)
            return [Document(page_content=text, metadata={"source": str(path)})]
        except UnicodeDecodeError:
            continue
    # Keep compatibility with custom/legacy TextLoader behavior in tests.
    if TextLoader is not None:
        loader = TextLoader(str(path), encoding="gb18030")
        return loader.load()
    text = path.read_text(encoding="gb18030", errors="replace")
    return [Document(page_content=text, metadata={"source": str(path)})]
