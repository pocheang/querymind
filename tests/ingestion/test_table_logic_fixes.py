"""Comprehensive tests for table processing and chunking logic fixes.

Validates:
1. Global row coordinate continuity across parent-child splitting (no row reset to 1).
2. Escaped pipe cell preservation in wide-table KV folding (no shifted or lost columns).
3. Table chunk classification (table with ### prefix is classified as "table", not "heading").
4. Wide table check scanning all rows (not just row 0).
5. Generic markdown bold bullet lists are not misclassified as KV tables.
6. Adjacent back-to-back tables are isolated into separate blocks.
7. Multi-page tables spanning 3+ pages merge completely.
"""

from __future__ import annotations

import re

from langchain_core.documents import Document

from app.ingestion.chunking.classification import classify_chunk_type
from app.ingestion.chunking.splitter import (
    _extract_document_blocks,
    _extract_markdown_cells,
    _is_kv_table_content,
    _is_markdown_table_content,
    _split_markdown_table_text,
    _split_single_table_block,
    split_documents,
)
from app.ingestion.extraction.tables import merge_cross_page_tables


def test_parent_child_global_row_coordinate_preservation() -> None:
    """Validate that child chunks inherit parent global row coordinates and do not reset to Row 1."""
    headers = "| ID | Name | Department | Score |"
    sep = "|---|---|---|---|"
    rows = [f"| {i} | Employee_{i:02d} | Dept_{i % 5} | {80 + i % 20} |" for i in range(1, 75)]
    table_text = f"### Sheet: Employees_2024\n\n{headers}\n{sep}\n" + "\n".join(rows)

    doc = Document(
        page_content=table_text,
        metadata={"source": "employees.xlsx", "document_id": "emp-01", "modality": "table"},
    )

    child_chunks, parent_records = split_documents([doc])
    assert len(parent_records) >= 2, "Expected at least 2 parent records"
    assert len(child_chunks) >= 4, "Expected multiple child chunks"

    # Verify that all parent records report total rows as 74
    for record in parent_records:
        text = record["text"]
        assert "of 74" in text, f"Parent record missing global row count (of 74): {text[:80]}"

    # Verify child chunks
    found_row_above_40 = False
    for child in child_chunks:
        content = child.page_content
        # Ensure total row is always 74, not parent-relative
        if "(Rows " in content or "(Row " in content:
            assert "of 74" in content, f"Child chunk reset total rows: {content[:100]}"
            # Ensure there are chunks with row numbers matching the second half of the table
            if any(f"Row {r} " in content or f"Rows {r}-" in content or f"-{r} of" in content for r in range(40, 75)):
                found_row_above_40 = True

    assert found_row_above_40, "Child chunks failed to preserve row coordinates into the 40-74 range"


def test_escaped_pipe_cells_in_kv_folding() -> None:
    """Validate that escaped pipes (\\|) inside cell values do not break columns in KV folding."""
    line = "| Product | Specs \\| Features | Price | Category |"
    cells = _extract_markdown_cells(line)
    assert len(cells) == 4, f"Expected 4 cells, got {len(cells)}: {cells}"
    assert cells[1] == "Specs | Features"
    assert cells[2] == "Price"
    assert cells[3] == "Category"

    # Test full table KV folding with escaped pipes
    headers = "| ID | Description | Cost |"
    sep = "|---|---|---|"
    rows = [
        "| ITEM_01 | High performance \\| Low power \\| Dual core processor unit | $150 |",
        "| ITEM_02 | Ruggedized casing \\| IP68 rated \\| Shock proof enclosure | $85 |",
    ]
    wide_headers = headers + " Extra1 | Extra2 | Extra3 | Extra4 | Extra5 |"
    wide_sep = sep + "---|---|---|---|---|"
    wide_rows = [r + " Val1 | Val2 | Val3 | Val4 | Val5 |" for r in rows]
    table_text = f"### Sheet: Hardware_BOM\n\n{wide_headers}\n{wide_sep}\n" + "\n".join(wide_rows)

    chunks = _split_single_table_block(table_text, max_chunk_size=180, row_overlap=1)
    combined = "\n".join(chunks)

    # Verify that 'Description' has the combined string with escaped pipes intact
    assert "- **Description**: High performance | Low power | Dual core processor unit" in combined
    assert "- **Cost**: $150" in combined
    assert "- **Extra5**: Val5" in combined


def test_table_chunk_classification_is_table_not_heading() -> None:
    """Validate that table chunks with ### Sheet: prefixes are classified as 'table' and not 'heading'."""
    table_chunk = """### Sheet: Financials (Rows 1-5 of 20)

| Metric | Q1 | Q2 |
|---|---|---|
| Revenue | $10M | $12M |
| Profit | $2M | $3M |
"""
    chunk_type = classify_chunk_type(table_chunk, {"modality": "table"})
    assert chunk_type == "table", f"Expected 'table', got '{chunk_type}'"

    # Even without modality hint, markdown table structure must be recognized as table
    chunk_type_raw = classify_chunk_type(table_chunk, {})
    assert chunk_type_raw == "table", f"Expected 'table' without modality hint, got '{chunk_type_raw}'"

    # Empty string should not crash
    assert classify_chunk_type("", {}) == "paragraph"
    assert classify_chunk_type("   ", {}) == "paragraph"


def test_wide_table_detection_scans_all_rows() -> None:
    """Validate that if row 0 is short, but row 2 is ultra-wide, adaptive KV folding is triggered."""
    headers = "| ColA | ColB | ColC |"
    sep = "|---|---|---|"
    rows = [
        "| 1 | Normal | Short |",
        "| 2 | " + ("SuperLongDescription " * 30) + " | Large |",
        "| 3 | Normal | Short |",
    ]
    table_text = f"### Sheet: MixedWidth\n\n{headers}\n{sep}\n" + "\n".join(rows)

    chunks = _split_single_table_block(table_text, max_chunk_size=400, row_overlap=1)
    assert len(chunks) >= 2
    # Ensure it converted to KV folding
    assert any("- **ColB**:" in c for c in chunks)


def test_regular_markdown_bullet_lists_not_misclassified_as_kv_tables() -> None:
    """Validate that regular markdown bold bullet lists are not misclassified as KV table content."""
    regular_markdown_list = """# System Configuration

- **Environment**: Production
- **Region**: us-west-2
- **ClusterSize**: 16 nodes
- **AutoScaling**: Enabled
"""
    assert not _is_kv_table_content(regular_markdown_list)
    assert not _is_markdown_table_content(regular_markdown_list)


def test_adjacent_back_to_back_tables_isolated() -> None:
    """Validate that two consecutive tables without intervening text are split into distinct blocks."""
    content = """| A1 | B1 |
|---|---|
| v1 | v2 |
| A2 | B2 |
|---|---|
| v3 | v4 |
"""
    blocks = _extract_document_blocks(content)
    assert len(blocks) == 2
    assert blocks[0][0] == "table"
    assert "| A1 | B1 |" in blocks[0][1]
    assert "| A2 | B2 |" not in blocks[0][1]

    assert blocks[1][0] == "table"
    assert "| A2 | B2 |" in blocks[1][1]


def test_multi_page_table_merging_3_pages() -> None:
    """Validate that merge_cross_page_tables seamlessly merges tables spanning 3 pages."""
    page1 = """# Section 1
Here is the multi-page table:

| ID | Value | Status |
|---|---|---|
| 1 | Val1 | Active |
| 2 | Val2 | Active |
| 3 | Val3 | Active |
"""

    page2 = """Page 2 Header
| 4 | Val4 | Active |
| 5 | Val5 | Active |
| 6 | Val6 | Active |
"""

    page3 = """| 7 | Val7 | Active |
| 8 | Val8 | Active |
| 9 | Val9 | Closed |

End of table notes.
"""

    pages = [page1, page2, page3]
    merged = merge_cross_page_tables(pages)
    assert len(merged) == 1, f"Expected 1 merged document for 3-page table, got {len(merged)}"
    merged_text = merged[0]
    assert "| 1 | Val1 |" in merged_text
    assert "| 4 | Val4 |" in merged_text
    assert "| 9 | Val9 |" in merged_text
    assert "End of table notes." in merged_text


def test_office_loader_rows_to_markdown_truncation_note_isolated() -> None:
    """Validate that truncation notice is formatted as a note outside the markdown table pipes."""
    from app.ingestion.loaders.office_loader import _rows_to_markdown

    rows = [
        ["ColA", "ColB"],
        ["Val1", "Val2"],
        ["... [Truncated: 10000 total rows, first 5000 rows shown] ..."],
    ]
    md = _rows_to_markdown(rows, sheet_name="Sheet1")
    assert "### Sheet: Sheet1" in md
    assert "| ColA | ColB |" in md
    assert "| Val1 | Val2 |" in md
    # Truncation notice must NOT be wrapped in pipes
    assert "| ... [Truncated:" not in md
    assert "_... [Truncated: 10000 total rows, first 5000 rows shown] ..._" in md


def test_office_loader_extract_markdown_tables_requires_separator_and_retains_sheet() -> None:
    """Validate that _extract_markdown_tables checks for table separators and extracts sheet names."""
    from app.ingestion.loaders.office_loader import _extract_markdown_tables
    from app.services.evidence.models import EvidenceDocument

    doc = EvidenceDocument(
        document_id="doc-test",
        version=1,
        tenant_id="tenant-1",
        source="report.md",
        filename="report.md",
        sha256="0" * 64,
    )

    content = """### Sheet: Sales_Summary

| Region | Q1 | Q2 |
|---|---|---|
| EMEA | 100 | 120 |
| APAC | 150 | 180 |

Some text in between.

| Fake table line 1 |
| Fake table line 2 without separator |
"""

    tables = _extract_markdown_tables(content, doc)
    assert len(tables) == 1, f"Expected 1 valid table, got {len(tables)}"
    assert tables[0].sheet == "Sales_Summary"
    assert "| Region | Q1 | Q2 |" in tables[0].markdown


def test_table_extractor_format_table_as_text_no_redundant_headers() -> None:
    """Validate that TableExtractor.format_table_as_text does not output duplicate headers."""
    from app.services.multimodal.models import TableContent
    from app.services.multimodal.table_extractor import TableExtractor

    extractor = TableExtractor()
    table = TableContent(
        table_id="tbl-01",
        doc_id="doc-01",
        page_number=1,
        headers=["Col1", "Col2"],
        rows=[["A", "B"]],
        summary="Test Table",
        metadata={"sheet": "Overview"},
    )
    formatted = extractor.format_table_as_text(table)
    assert "Columns (2): Col1 | Col2" in formatted
    assert "Table: Col1 | Col2" not in formatted
    assert "A | B" in formatted


def test_merge_cross_page_tables_with_spans_preserves_page_numbers() -> None:
    """Validate that cross-page merging maintains page spans and does not drift subsequent page numbers."""
    from app.ingestion.extraction.tables import merge_cross_page_tables_with_spans

    page1 = "| A | B |\n|---|---|\n| 1 | 2 |\n"
    page2 = "| 3 | 4 |\n"
    page3 = "# Non table content on page 3\n"
    spanned = merge_cross_page_tables_with_spans([page1, page2, page3])
    assert len(spanned) == 2, f"Expected 2 documents, got {len(spanned)}"
    # First item merged pages 1 and 2
    assert spanned[0][1] == [1, 2]
    assert "| 1 | 2 |" in spanned[0][0]
    assert "| 3 | 4 |" in spanned[0][0]
    # Second item retained its true physical page 3!
    assert spanned[1][1] == [3]
    assert "Non table content on page 3" in spanned[1][0]


def test_repeated_header_cross_page_merging() -> None:
    """Validate that multi-page tables that repeat headers and separators are cleanly merged."""
    page1 = """| Col1 | Col2 |
|---|---|
| row1 | data1 |
"""
    page2 = """| Col1 | Col2 |
|---|---|
| row2 | data2 |
"""
    merged = merge_cross_page_tables([page1, page2])
    assert len(merged) == 1, f"Expected 1 merged page, got {len(merged)}"
    assert "| row1 | data1 |" in merged[0]
    assert "| row2 | data2 |" in merged[0]
    # The repeated separator row must only appear once
    assert merged[0].count("|---|---|") == 1


def test_smart_header_sniffing_skips_title_banner() -> None:
    """Validate that an Excel sheet with a title banner in row 0 preserves column headers and title."""
    from app.ingestion.loaders.office_loader import _rows_to_markdown

    rows = [
        ["2024 Q3 Financial Summary", "", "", ""],
        ["Dept", "Budget", "Actual", "Variance"],
        ["Engineering", "100K", "95K", "-5K"],
    ]
    md = _rows_to_markdown(rows, sheet_name="Finances")
    assert "**2024 Q3 Financial Summary**" in md
    assert "| Dept | Budget | Actual | Variance |" in md
    assert "| Engineering | 100K | 95K | -5K |" in md


def test_heading_scope_chapter_start_not_polluted() -> None:
    """Validate that a chunk starting with a heading adopts that heading immediately."""
    from app.ingestion.chunking.splitter import _heading_scope

    text1 = "## 1. Introduction\nIntroductory paragraphs..."
    scope1, carried1 = _heading_scope(text1, None)
    assert scope1 == "## 1. Introduction"
    assert carried1 == "## 1. Introduction"

    text2 = "## 2. Architecture\nDetails about system design..."
    scope2, carried2 = _heading_scope(text2, carried1)
    # Must be Chapter 2, NOT Chapter 1!
    assert scope2 == "## 2. Architecture"
    assert carried2 == "## 2. Architecture"


def test_chinese_keyword_extraction() -> None:
    """Validate that Chinese keyword extraction returns meaningful Chinese terms."""
    from app.ingestion.chunking.metadata import extract_keywords

    zh_text = "本项目采用先进架构设计，支持向量数据库检索与知识图谱构建，提高模型分析准确率。"
    keywords = extract_keywords(zh_text, top_n=5)
    assert len(keywords) >= 1
    # Keywords should contain actual words from the text (length >= 2)
    assert any(len(k) >= 2 and k in zh_text for k in keywords)


def test_cross_page_merging_rejects_different_headers_with_same_col_count() -> None:
    """Validate that two consecutive pages with different tables of the same column count are NOT merged."""
    page1 = """| Employee | Department | Salary |
|---|---|---|
| Alice | HR | $50k |
"""
    page2 = """| Product | Category | Price |
|---|---|---|
| Laptop | Electronics | $1000 |
"""
    merged = merge_cross_page_tables([page1, page2])
    assert len(merged) == 2, f"Expected 2 separate pages, but got merged into {len(merged)}!"
    assert "Employee" in merged[0]
    assert "Product" in merged[1]


def test_cross_page_merging_prevents_merging_across_chapter_headings_and_keeps_notes() -> None:
    """Validate that a heading on page 2 blocks merging, and notes before repeated headers are retained."""
    page1 = """| ColA | ColB |
|---|---|
| 1 | 2 |
"""
    page2_with_heading = """## Chapter 2: Additional Metrics
| ColA | ColB |
|---|---|
| 3 | 4 |
"""
    merged1 = merge_cross_page_tables([page1, page2_with_heading])
    assert len(merged1) == 2, "Cross-page merge should not merge across chapter headings"

    page2_with_note = """*Note: Figures in thousands*
| ColA | ColB |
|---|---|
| 3 | 4 |
"""
    merged2 = merge_cross_page_tables([page1, page2_with_note])
    assert len(merged2) == 1, "Expected table to merge with note preserved"
    assert "*Note: Figures in thousands*" in merged2[0]
    assert "| 1 | 2 |" in merged2[0]
    assert "| 3 | 4 |" in merged2[0]


def test_extract_document_blocks_preserves_sheet_and_title_together() -> None:
    """Validate that multi-line headers like Sheet name and Title banner stay with the table block."""
    content = """### Sheet: Finances

**2024 Q3 Summary**

| Dept | Budget |
|---|---|
| Engineering | 100 |
"""
    blocks = _extract_document_blocks(content)
    assert len(blocks) == 1, f"Expected 1 table block with combined header, got {len(blocks)}: {blocks}"
    assert blocks[0][0] == "table"
    assert "### Sheet: Finances" in blocks[0][1]
    assert "**2024 Q3 Summary**" in blocks[0][1]


def test_multi_table_parent_row_coordinates_isolated() -> None:
    """Validate that row coordinates from table 1 do not bleed into table 2 in the same chunk."""
    content = """### Table 1 (Rows 31-40 of 50)

| T1_A | T1_B |
|---|---|
| a1 | b1 |
| a2 | b2 |

### Table 2

| T2_A | T2_B |
|---|---|
| x1 | y1 |
| x2 | y2 |
"""
    chunks = _split_markdown_table_text(
        content,
        max_chunk_size=150,
        global_row_offset=30,
        global_total_rows=50,
    )
    assert chunks is not None
    table2_chunks = [c for c in chunks if "Table 2" in c]
    assert len(table2_chunks) >= 1
    # Table 2 must NOT say "of 50" or "Row 31"
    for c in table2_chunks:
        assert "of 50" not in c, f"Table 2 was polluted with Table 1's total rows: {c}"
        assert "Row 3" not in c, f"Table 2 was polluted with Table 1's offset: {c}"


def test_small_table_with_intro_and_note_segmentation() -> None:
    """Validate that documents with table and prose preserve intro, table, and trailing notes without loss."""
    content = """Introductory paragraph before the table.

| Feature | Status |
|---|---|
| Auth | Enabled |
| Billing | Active |

Audit approved by compliance team.
"""
    chunks = _split_markdown_table_text(content, max_chunk_size=400)
    assert chunks is not None
    assert len(chunks) == 3, f"Expected 3 blocks for intro, table, and note, got {len(chunks)}"
    assert "Introductory paragraph" in chunks[0]
    assert "| Feature | Status |" in chunks[1]
    assert "Audit approved" in chunks[2]


def test_excel_header_sniffing_avoids_data_row_and_merged_title() -> None:
    """Validate that merged title banners and purely numeric rows are not chosen as headers."""
    from app.ingestion.loaders.office_loader import _rows_to_markdown

    # Case 1: Banner row forward-filled with same text
    rows_banner = [
        ["Annual Report 2024", "Annual Report 2024", "Annual Report 2024", "Annual Report 2024"],
        ["Dept", "Q1", "Q2", "Q3"],
        ["Sales", "$100", "$200", "$300"],
    ]
    md1 = _rows_to_markdown(rows_banner, sheet_name="Overview")
    assert "| Dept | Q1 | Q2 | Q3 |" in md1
    assert "**Annual Report 2024**" in md1

    # Case 2: Incomplete header vs full numeric data row
    rows_data = [
        ["Product", "Category", ""],
        ["Widget", "Hardware", "$25.50"],
    ]
    md2 = _rows_to_markdown(rows_data)
    assert "| Product | Category | Column_3 |" in md2
    assert "| Widget | Hardware | $25.50 |" in md2


def test_chinese_word_count_accurate() -> None:
    """Validate that bilingual word count accurately measures Chinese characters."""
    from app.ingestion.chunking.metadata import enhance_chunk_metadata

    zh_text = "这是一个测试段落，用于验证中文分词统计功能。本项目性能优异。"
    meta = enhance_chunk_metadata(zh_text, {}, 0, 1)
    assert meta["word_count"] >= 20, f"Expected word_count >= 20, got {meta['word_count']}"


def test_heading_classification_precision() -> None:
    """Validate that normal sentences or incomplete phrases are not misclassified as headings."""
    from app.ingestion.chunking.classification import classify_chunk_type

    # Ordinary English sentence without period
    s1 = "Apple announced new products yesterday and revenue grew significantly"
    assert classify_chunk_type(s1, {}) == "paragraph"

    # Ordinary Chinese sentence
    s2 = "第一季度公司实现了高速增长业务进展顺利"
    assert classify_chunk_type(s2, {}) == "paragraph"

    # Real headings
    assert classify_chunk_type("第一章 基础架构与组件", {}) == "heading"
    assert classify_chunk_type("## Section 2.1 Overview", {}) == "heading"
    assert classify_chunk_type("SYSTEM ARCHITECTURE", {}) == "heading"


def test_csv_truncates_large_tables_at_max_rows() -> None:
    """Validate that CSVs with rows exceeding MAX_TABLE_ROWS are safely truncated."""
    import shutil
    import tempfile
    from pathlib import Path

    from app.ingestion.loaders.office_loader import MAX_TABLE_ROWS, _csv_rows

    temp_dir = Path(tempfile.mkdtemp(prefix="querymind-csv-trunc-"))
    try:
        csv_file = temp_dir / "giant.csv"
        # Write header + 5005 rows
        lines = ["ColA,ColB"] + [f"valA_{i},valB_{i}" for i in range(MAX_TABLE_ROWS + 5)]
        csv_file.write_text("\n".join(lines), encoding="utf-8")

        sheets = _csv_rows(csv_file)
        assert len(sheets) == 1
        rows = sheets[0][1]
        assert any("... [Truncated:" in str(r[0]) for r in rows)
        assert len(rows) == MAX_TABLE_ROWS + 1
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_kv_folding_entity_overlap() -> None:
    """Validate that wide table KV folding preserves entity overlap across adjacent chunks."""
    headers = "| ID | Model | Description | Specs | Provider |"
    sep = "|---|---|---|---|---|"
    rows = [
        f"| ITEM_{i:02d} | Model_{i} | High density memory module for data center applications | Spec_{i} | Vendor_{i} |"
        for i in range(1, 8)
    ]
    table_text = f"### Sheet: Inventory\n\n{headers}\n{sep}\n" + "\n".join(rows)

    # Split with row_overlap=1 and small max_chunk_size to force multiple chunks
    chunks = _split_single_table_block(table_text, max_chunk_size=320, row_overlap=1)
    assert len(chunks) >= 3

    # Check that adjacent chunks share overlapping entities
    for idx in range(len(chunks) - 1):
        c1 = chunks[idx]
        c2 = chunks[idx + 1]
        # Find which ITEM_XX are in c1 and c2
        items_c1 = set(re.findall(r"ITEM_\d+", c1))
        items_c2 = set(re.findall(r"ITEM_\d+", c2))
        assert len(items_c1 & items_c2) >= 1, f"Expected entity overlap between chunk {idx} and {idx + 1}"


def test_kv_folding_oversize_cell_guard() -> None:
    """Validate that single oversized entities in KV folding are safely split into parts without exceeding budget."""
    headers = "| Key | VeryLongDescription | Note |"
    sep = "|---|---|---|"
    huge_text = "DetailedEnterpriseConfigurationClause " * 25  # ~950 chars
    row = f"| Item01 | {huge_text} | NormalNote |"
    table_text = f"### Sheet: Config\n\n{headers}\n{sep}\n{row}"

    chunks = _split_single_table_block(table_text, max_chunk_size=350, row_overlap=1)
    assert len(chunks) >= 2, f"Expected oversize entity to be partitioned, got {len(chunks)}"
    # Every chunk should be bounded
    for c in chunks:
        assert len(c) <= 450, f"Chunk exceeded size guard: {len(c)} chars"
        assert "(Part " in c or "Item01" in c


def test_cross_page_table_isolation_preserves_subsequent_headings_on_page2() -> None:
    """Validate that subsequent chapters on page 2 are not swallowed into page 1 when merging tables."""
    page1 = """# Section 1
Here is the table:

| Col1 | Col2 |
|---|---|
| A1 | B1 |
| A2 | B2 |
"""
    page2 = """| A3 | B3 |
| A4 | B4 |

## Chapter 2: System Architecture

Architecture overview and details about component interfaces that must stay on page 2.
"""
    from app.ingestion.extraction.tables import merge_cross_page_tables_with_spans

    spanned = merge_cross_page_tables_with_spans([page1, page2])
    assert len(spanned) == 2, f"Expected 2 separate documents, got {len(spanned)}"

    # Page 1 table has continuation rows A3 | B3
    assert "| A3 | B3 |" in spanned[0][0]
    assert "| A4 | B4 |" in spanned[0][0]
    # Chapter 2 must NOT be in document 1!
    assert "Chapter 2: System Architecture" not in spanned[0][0]

    # Document 2 retains Chapter 2 and its physical page
    assert "Chapter 2: System Architecture" in spanned[1][0]
    assert spanned[1][1] == [2]


def test_procedure_classification_priority_over_list() -> None:
    """Validate that action procedure instructions are classified as procedure, not list."""
    procedure_text = """To configure the cluster:
1. Open the administration dashboard
2. Configure the network security groups
3. Run the deployment verification command
"""
    assert classify_chunk_type(procedure_text, {}) == "procedure"

    # Regular shopping list remains list
    shopping_list = """Grocery items:
1. Apples
2. Bananas
3. Oranges
"""
    assert classify_chunk_type(shopping_list, {}) == "list"


def test_table_stopwords_not_extracted_as_keywords() -> None:
    """Validate that structural table words like sheet, rows, column are filtered from keywords."""
    from app.ingestion.chunking.metadata import extract_keywords

    table_chunk = """### Sheet: Quarterly_Finances (Rows 1-10 of 50)
- **Column_1**: Revenue
- **Column_2**: $50M
- **Column_3**: Operating margin expansion in semiconductors
"""
    keywords = extract_keywords(table_chunk, top_n=5)
    for noise in ("sheet", "rows", "column", "column_1", "column_2", "total"):
        assert noise not in keywords, f"Structural noise word '{noise}' found in keywords: {keywords}"
    assert any("semiconductor" in k or "revenue" in k or "margin" in k or "finance" in k for k in keywords)


def test_entity_numbers_filters_table_row_coordinates() -> None:
    """Validate that row coordinate labels (Rows 1-20 of 50) do not pollute entity numbers."""
    from app.ingestion.chunking.metadata import extract_entities

    text = """### Sheet: Financials (Rows 1-20 of 50)
The enterprise recorded ISO-27001 compliance with 4096 bit encryption keys."""
    entities = extract_entities(text)
    numbers = entities.get("numbers", [])
    # 27001 and 4096 are real entity numbers
    assert "27001" in numbers or "4096" in numbers
    # 50 from 'of 50' should not dominate
    assert "1" not in numbers and "20" not in numbers


def test_table_child_chunks_inherit_table_id_and_columns() -> None:
    """Validate that table child chunks inherit table_id and get table_columns and row range."""
    from langchain_core.documents import Document

    from app.ingestion.chunking.splitter import split_documents_enhanced

    # 30-row table that will split into multiple child chunks
    header = "| Region | Revenue | Cost | Profit | Margin |\n|---|---|---|---|---|\n"
    rows = "\n".join(f"| Region_{i} | ${100 + i}k | ${60 + i}k | ${40}k | 40% |" for i in range(1, 31))
    table_content = f"### Regional Financials\n\n{header}{rows}"

    doc = Document(
        page_content=table_content,
        metadata={"document_id": "doc-fin-101", "table_id": "tbl-fin-101", "modality": "table"},
    )
    children, parents = split_documents_enhanced([doc])

    assert len(children) >= 2, f"Expected table to split into multiple chunks, got {len(children)}"
    for child in children:
        assert child.metadata.get("table_id") == "tbl-fin-101"
        assert child.metadata.get("modality") == "table"
        assert "Region" in child.metadata.get("table_columns", "")
        assert "Revenue" in child.metadata.get("table_columns", "")
        assert "table_row_range" in child.metadata
        assert child.metadata.get("total_table_rows") == 30
        assert child.metadata.get("importance_score", 0) >= 0.85

    # Parent record check
    assert len(parents) >= 1
    assert parents[0]["metadata"].get("table_id") == "tbl-fin-101"
    assert "Region" in parents[0]["metadata"].get("table_columns", "")


def test_table_child_chunks_auto_generate_table_id_if_missing() -> None:
    """Validate that when table_id is missing from base metadata, a deterministic one is assigned."""
    from langchain_core.documents import Document

    from app.ingestion.chunking.splitter import split_documents_enhanced

    header = "| Product | Units | Price |\n|---|---|---|\n"
    rows = "\n".join(f"| Prod_{i} | {i * 10} | ${i * 5} |" for i in range(1, 25))
    table_content = f"{header}{rows}"

    doc = Document(
        page_content=table_content,
        metadata={"document_id": "doc-sales-99"},
    )
    children, parents = split_documents_enhanced([doc])

    assert len(children) >= 2
    first_tbl_id = children[0].metadata.get("table_id")
    assert first_tbl_id is not None and first_tbl_id.startswith("tbl-")
    # All children from the same parent table block must share the identical table_id
    for child in children:
        assert child.metadata.get("table_id") == first_tbl_id
        assert "Product" in child.metadata.get("table_columns", "")


def test_table_importance_score_high_density_boost() -> None:
    """Validate importance scoring boosts table type and structured column/number density."""
    from app.ingestion.chunking.metadata import calculate_importance_score

    # Standard paragraph
    para_score = calculate_importance_score("Some general overview paragraph.", "paragraph", {})
    assert para_score <= 0.65

    # Plain table without columns or numbers
    plain_tbl = calculate_importance_score("Some minimal table content.", "table", {})
    assert plain_tbl >= 0.75

    # Table with structured columns
    structured_tbl = calculate_importance_score(
        "Some table content with 300 chars " * 10,
        "table",
        {"table_columns": "Region, Revenue, Cost"},
    )
    assert structured_tbl >= 0.85

    # Table with high-density numbers
    dense_num_tbl = calculate_importance_score(
        "Financial results " * 20,
        "table",
        {"entities": {"numbers": ["1000", "2000", "3000", "4000"]}},
    )
    assert dense_num_tbl >= 0.85


def test_ingest_index_one_table_enriches_summary_and_metadata() -> None:
    """Validate that _index_one_table creates TableContent with columns and dimensions in summary."""
    from unittest.mock import MagicMock

    from app.ingestion.loaders.office_loader import TableBlock
    from app.services.documents.ingest import _index_one_table

    mock_extractor = MagicMock()
    table_block = TableBlock(
        table_id="tbl-ledger-88",
        page=3,
        sheet="Q3_Summary",
        markdown="| Account | Debit | Credit |\n|---|---|---|\n| Cash | $50,000 | $0 |\n| Revenue | $0 | $50,000 |",
    )
    canonical = {
        "document_id": "doc-fin-77",
        "tenant_id": "tenant-abc",
        "owner_user_id": "user-1",
    }

    result = _index_one_table(mock_extractor, table_block, canonical)
    assert result is True
    mock_extractor.index_table.assert_called_once()
    call_arg = mock_extractor.index_table.call_args[0][0]

    assert call_arg.table_id == "tbl-ledger-88"
    assert "sheet: Q3_Summary" in call_arg.summary
    assert "columns: Account, Debit, Credit" in call_arg.summary
    assert "2 rows, 3 columns" in call_arg.summary
    assert call_arg.metadata["table_id"] == "tbl-ledger-88"
    assert call_arg.metadata["sheet"] == "Q3_Summary"
    assert call_arg.metadata["num_rows"] == 2
    assert call_arg.metadata["num_cols"] == 3
