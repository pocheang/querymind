"""Tests for table & excel enhancements (P0 & P1)."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.agents.knowledge.service import _VISUAL_QUERY_PATTERN, _matches
from app.ingestion.extraction.tables_nested import (
    detect_nested_table,
    flatten_nested_table,
    simplify_complex_table,
)
from app.ingestion.loaders.dispatch import load_document_with_evidence
from app.ingestion.loaders.office_loader import (
    _extract_sheet_rows_with_merged_cells,
    extract_markdown_tables,
)
from app.services.evidence.models import EvidenceDocument


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp(prefix="querymind_table_enh_")
    try:
        yield Path(d)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_visual_query_pattern_matches_spreadsheet_keywords():
    queries = [
        "请帮我分析销售明细报表",
        "查看客户清单和联系方式",
        "分析这份财务台账",
        "汇总这份数据表的内容",
        "Check this excel spreadsheet",
        "What are the numbers in this csv file?",
        "Please parse the xlsx columns",
        "Show sheet details",
    ]
    for q in queries:
        assert _matches(q, _VISUAL_QUERY_PATTERN), f"Expected '{q}' to match _VISUAL_QUERY_PATTERN"


def test_nested_table_detection_and_flattening():
    # 1. HTML table tag inside text
    html_table = (
        "| Category | Details |\n| --- | --- |\n| Alpha | <table><tr><td>SubA</td><td>SubB</td></tr></table> |\n"
    )
    assert detect_nested_table(html_table)
    flattened = flatten_nested_table(html_table)
    assert "<table>" not in flattened
    assert "SubA; SubB" in flattened

    # 2. Escaped pipes inside markdown cells
    escaped_table = "| ID | Sub-items | Price |\n| --- | --- | --- |\n| 1 | item1 \\| item2 \\| item3 | $10 |\n"
    assert detect_nested_table(escaped_table)
    flattened_esc = flatten_nested_table(escaped_table)
    assert "\\|" not in flattened_esc
    assert "item1; item2; item3" in flattened_esc

    # 3. Bracketed sub-tables: [| a | b |]
    bracketed_table = "| Name | Config |\n| --- | --- |\n| Server | [| host | port |] |\n"
    assert detect_nested_table(bracketed_table)
    flattened_br = flatten_nested_table(bracketed_table)
    assert "[host; port]" in flattened_br

    # 4. Normal table should not be detected as nested
    normal_table = "| Name | Age | City |\n| --- | --- | --- |\n| Alice | 30 | New York |\n| Bob | 25 | London |\n"
    assert not detect_nested_table(normal_table)
    simplified = simplify_complex_table(normal_table)
    assert "| Alice | 30 | New York |" in simplified


def test_load_document_with_evidence_extracts_tables_from_markdown(temp_dir: Path):
    md_file = temp_dir / "report.md"
    md_content = (
        "# Quarterly Performance\n\n"
        "Here is the summary table:\n\n"
        "| Quarter | Revenue | Profit |\n"
        "| --- | --- | --- |\n"
        "| Q1 | $100M | $20M |\n"
        "| Q2 | $120M | $25M |\n"
        "| Q3 | $110M | $22M |\n\n"
        "End of report.\n"
    )
    md_file.write_text(md_content, encoding="utf-8")

    parsed, docs = load_document_with_evidence(md_file)
    assert len(parsed.tables) == 1
    assert parsed.tables[0].page == 1
    assert "| Quarter | Revenue | Profit |" in parsed.tables[0].markdown
    assert "| Q1 | $100M | $20M |" in parsed.tables[0].markdown


def test_extract_markdown_tables_with_start_index():
    evidence_doc = EvidenceDocument(
        document_id="doc-test-1234567890",
        version=1,
        tenant_id="tenant-1",
        source="/docs/test.md",
        filename="test.md",
        sha256="b" * 64,
        owner_user_id="user-1",
        visibility="private",
    )
    md = "| A | B |\n|---|---|\n| 1 | 2 |\n\nSome middle text\n\n| X | Y |\n|---|---|\n| 8 | 9 |\n"
    tables = extract_markdown_tables(md, evidence_doc, page=2, start_index=10)
    assert len(tables) == 2
    assert tables[0].page == 2
    assert tables[1].page == 2
    # table_ids should be distinct and based on start_index
    assert tables[0].table_id != tables[1].table_id


def test_extract_sheet_rows_with_merged_cells():
    # Mock openpyxl sheet with merged cells
    mock_sheet = MagicMock()
    mock_sheet.max_row = 4

    # Create mock merged cell range covering A2:A4 (min_row=2, max_row=4, min_col=1, max_col=1)
    mock_range = MagicMock()
    mock_range.min_row = 2
    mock_range.max_row = 4
    mock_range.min_col = 1
    mock_range.max_col = 1
    mock_sheet.merged_cells.ranges = [mock_range]

    # Cell(2, 1) has value "Engineering"
    mock_top_left_cell = MagicMock()
    mock_top_left_cell.value = "Engineering"
    mock_sheet.cell.return_value = mock_top_left_cell

    # Create rows:
    # Row 1: Header [Department, Employee, Salary]
    # Row 2: [Engineering, Alice, 100k]
    # Row 3: [None (merged), Bob, 110k]
    # Row 4: [None (merged), Charlie, 120k]
    cell_r1 = [MagicMock(value="Department"), MagicMock(value="Employee"), MagicMock(value="Salary")]
    cell_r2 = [MagicMock(value="Engineering"), MagicMock(value="Alice"), MagicMock(value="100k")]
    cell_r3 = [MagicMock(value=None), MagicMock(value="Bob"), MagicMock(value="110k")]
    cell_r4 = [MagicMock(value=None), MagicMock(value="Charlie"), MagicMock(value="120k")]

    mock_sheet.iter_rows.return_value = [cell_r1, cell_r2, cell_r3, cell_r4]

    extracted_rows = _extract_sheet_rows_with_merged_cells(mock_sheet, max_rows=10)
    assert len(extracted_rows) == 4
    assert extracted_rows[0] == ["Department", "Employee", "Salary"]
    assert extracted_rows[1] == ["Engineering", "Alice", "100k"]
    # Row 3 and Row 4 must receive forward-filled "Engineering"
    assert extracted_rows[2] == ["Engineering", "Bob", "110k"]
    assert extracted_rows[3] == ["Engineering", "Charlie", "120k"]


def test_extract_sheet_rows_max_rows_truncation():
    mock_sheet = MagicMock()
    mock_sheet.max_row = 100
    mock_sheet.merged_cells.ranges = []
    mock_sheet.iter_rows.return_value = [[MagicMock(value=f"Item_{i}"), MagicMock(value=i)] for i in range(1, 20)]

    extracted = _extract_sheet_rows_with_merged_cells(mock_sheet, max_rows=5)
    # 5 rows + 1 truncation row
    assert len(extracted) == 6
    assert "Truncated" in str(extracted[-1][0])
