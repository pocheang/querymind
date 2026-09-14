"""Tests for table, Excel, CSV parsing, and header-preserving table chunking."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest
from langchain_core.documents import Document

from app.ingestion.chunking.splitter import (
    _is_markdown_table_content,
    _split_markdown_table_text,
    split_documents,
)
from app.ingestion.loaders.office_loader import (
    OFFICE_EXTENSIONS,
    _extract_markdown_tables,
    load_office_document,
    parsed_to_documents,
)
from app.services.evidence.models import EvidenceDocument
from app.services.multimodal.models import TableContent
from app.services.multimodal.table_extractor import TableExtractor


@pytest.fixture
def table_test_dir():
    # Deliberately not pytest's tmp_path: its basetemp needs directory permissions
    # that are not available on every Windows checkout.
    temp_dir = Path(tempfile.mkdtemp(prefix="querymind-table-test-"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def _doc(path: Path) -> EvidenceDocument:
    return EvidenceDocument(
        document_id="doc-test-1",
        version=1,
        tenant_id="tenant-1",
        source=str(path),
        filename=path.name,
        sha256="a" * 64,
    )


def test_csv_extension_is_in_office_extensions() -> None:
    assert ".csv" in OFFICE_EXTENSIONS
    assert ".xlsx" in OFFICE_EXTENSIONS
    assert ".xls" in OFFICE_EXTENSIONS


def test_csv_file_is_loaded_as_table_document(table_test_dir: Path) -> None:
    csv_file = table_test_dir / "quarterly_revenue.csv"
    csv_content = "Quarter,Revenue,Expenses,Profit\nQ1,1000,600,400\nQ2,1200,700,500\nQ3,1500,800,700\n"
    csv_file.write_text(csv_content, encoding="utf-8")

    evidence_doc = _doc(csv_file)
    parsed = load_office_document(csv_file, evidence_doc)

    assert parsed.parser == "csv"
    assert len(parsed.tables) == 1
    table = parsed.tables[0]
    assert table.sheet == "quarterly_revenue"
    assert "| Quarter | Revenue | Expenses | Profit |" in table.markdown
    assert "| Q1 | 1000 | 600 | 400 |" in table.markdown

    docs = parsed_to_documents(parsed)
    assert len(docs) == 1
    assert docs[0].metadata["modality"] == "table"
    assert docs[0].metadata["sheet"] == "quarterly_revenue"
    assert "quarterly_revenue" in docs[0].page_content


def test_csv_with_gbk_encoding_and_semicolon(table_test_dir: Path) -> None:
    csv_file = table_test_dir / "chinese_data.csv"
    csv_content = "姓名;部门;薪资\n张三;研发部;25000\n李四;市场部;18000\n"
    csv_file.write_bytes(csv_content.encode("gbk"))

    evidence_doc = _doc(csv_file)
    parsed = load_office_document(csv_file, evidence_doc)

    assert parsed.parser == "csv"
    assert len(parsed.tables) == 1
    table = parsed.tables[0]
    assert "| 姓名 | 部门 | 薪资 |" in table.markdown
    assert "| 张三 | 研发部 | 25000 |" in table.markdown


def test_table_aware_chunking_preserves_headers() -> None:
    # Build a markdown table with 30 rows
    headers = "| ID | Product | Quantity | Unit Price | Total Revenue | Region |"
    sep = "|---|---|---|---|---|---|"
    rows = [f"| {i} | Product_{i} | {i * 10} | {i * 5} | {i * 50} | Region_{i % 4} |" for i in range(1, 31)]
    table_text = f"### Sheet: Sales_2024\n\n{headers}\n{sep}\n" + "\n".join(rows)

    assert _is_markdown_table_content(table_text) is True

    # Split with a small chunk size to force multiple chunks
    chunks = _split_markdown_table_text(table_text, max_chunk_size=350)
    assert chunks is not None
    assert len(chunks) > 1

    # Every single chunk must retain the headers and sheet information
    for chunk in chunks:
        assert headers in chunk, f"Chunk missing header: {chunk[:100]}"
        assert sep in chunk, f"Chunk missing separator: {chunk[:100]}"
        assert "Sheet: Sales_2024" in chunk, f"Chunk missing sheet info: {chunk[:100]}"


def test_table_document_chunking_integration() -> None:
    headers = "| Dept | Employee | Score |"
    sep = "|---|---|---|"
    rows = [f"| Engineering | Dev_{i} | {80 + i} |" for i in range(1, 25)]
    table_text = f"{headers}\n{sep}\n" + "\n".join(rows)

    doc = Document(
        page_content=table_text,
        metadata={"modality": "table", "source": "test_table.xlsx", "document_id": "doc-1", "sheet": "Scores"},
    )

    child_chunks, parent_records = split_documents([doc])
    assert len(child_chunks) >= 1
    for chunk in child_chunks:
        assert chunk.metadata["modality"] == "table"
        assert headers in chunk.page_content


def test_table_extractor_summary_and_formatting() -> None:
    extractor = TableExtractor()
    table = TableContent(
        table_id="tbl-test",
        doc_id="doc-test",
        page_number=1,
        headers=["Col_A", "Col_B", "Col_C"],
        rows=[["1", "2", "3"], ["4", "5", "6"]],
        summary="Test Table Summary",
        metadata={"sheet": "Overview", "num_rows": 2, "num_cols": 3},
    )

    formatted = extractor.format_table_as_text(table)
    assert "Sheet: Overview" in formatted
    assert "Columns (3): Col_A | Col_B | Col_C" in formatted
    assert "Total Rows: 2" in formatted
    assert "1 | 2 | 3" in formatted


def test_docx_markdown_tables_extracted() -> None:
    docx_md = """
# Annual Report

Below is the revenue table:

| Year | Revenue | Growth |
|---|---|---|
| 2023 | $10M | 15% |
| 2024 | $15M | 50% |

End of table.
"""
    evidence_doc = _doc(Path("report.docx"))
    tables = _extract_markdown_tables(docx_md, evidence_doc)
    assert len(tables) == 1
    assert "| Year | Revenue | Growth |" in tables[0].markdown
    assert "| 2023 | $10M | 15% |" in tables[0].markdown
