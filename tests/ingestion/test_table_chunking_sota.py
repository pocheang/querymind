"""Academic and SOTA Paper-Aligned Table Chunking Tests.

Validates the Table-RAG (SIGIR 2024), TableLlama (NAACL 2024), and StructLM (EMNLP 2024)
requirements:
1. Document block segmentation (zero trailing prose loss, zero prefix duplication).
2. Multi-table segregation (isolated headers & rows).
3. Sliding row window with row overlap for boundary continuity.
4. Adaptive KV-folding for ultra-wide tables.
5. Non-stacking coordinate labels across parent-child hierarchies.
"""

from __future__ import annotations

from langchain_core.documents import Document

from app.ingestion.chunking.splitter import (
    _extract_document_blocks,
    _split_markdown_table_text,
    _split_single_table_block,
    split_documents,
)


def test_block_segmentation_preserves_trailing_and_leading_prose() -> None:
    """Validate that text preceding and trailing a table is completely preserved without data loss."""
    content = """# Executive Summary
In fiscal year 2024, our operations expanded across 12 countries.

### Sheet: Regional_Performance

| Region | Revenue | Growth |
|---|---|---|
| North America | $120M | +15% |
| Europe | $85M | +8% |
| Asia Pacific | $95M | +22% |

Key Observation: Asia Pacific demonstrated the highest growth rate at 22%.
Recommendation: Increase capital allocation in Q3 to support infrastructure.
"""

    blocks = _extract_document_blocks(content)
    assert len(blocks) == 3
    assert blocks[0][0] == "text"
    assert "Executive Summary" in blocks[0][1]
    assert "operations expanded across 12 countries" in blocks[0][1]

    assert blocks[1][0] == "table"
    assert "Regional_Performance" in blocks[1][1]
    assert "| Region | Revenue | Growth |" in blocks[1][1]
    assert "| Asia Pacific | $95M | +22% |" in blocks[1][1]

    assert blocks[2][0] == "text"
    assert "Key Observation: Asia Pacific" in blocks[2][1]
    assert "Increase capital allocation in Q3" in blocks[2][1]


def test_split_markdown_table_text_does_not_drop_trailing_prose() -> None:
    """Ensure _split_markdown_table_text preserves trailing notes and paragraphs."""
    content = """# Overview

| Metric | Target | Actual |
|---|---|---|
| Q1_Sales | 100 | 105 |
| Q2_Sales | 120 | 118 |

Audited and approved by Financial Oversight Committee.
"""

    chunks = _split_markdown_table_text(content, max_chunk_size=500)
    assert chunks is not None
    combined = "\n\n".join(chunks)
    assert "Audited and approved by Financial Oversight Committee" in combined
    assert "Overview" in combined
    assert "| Metric | Target | Actual |" in combined


def test_multi_table_segregation_in_single_document() -> None:
    """Validate that multiple tables in one document are isolated and never conflated."""
    content = """### Table 1: Engineering_Team

| Engineer | Specialization |
|---|---|
| Alice | Distributed Systems |
| Bob | Vector Databases |

Middle Analysis: Engineering headcount grew by 20%.

### Table 2: Budget_Allocations

| Department | Budget |
|---|---|
| Engineering | $1.2M |
| Marketing | $400k |

Final Summary: All budget limits are maintained within targets.
"""

    blocks = _extract_document_blocks(content)
    assert len(blocks) == 4
    assert blocks[0][0] == "table"
    assert "Engineering_Team" in blocks[0][1]
    assert "Distributed Systems" in blocks[0][1]

    assert blocks[1][0] == "text"
    assert "Middle Analysis" in blocks[1][1]

    assert blocks[2][0] == "table"
    assert "Budget_Allocations" in blocks[2][1]
    assert "Marketing" in blocks[2][1]

    assert blocks[3][0] == "text"
    assert "Final Summary" in blocks[3][1]


def test_sliding_window_row_overlap_continuity() -> None:
    """Validate that table-rag row overlap ensures boundary row continuity between adjacent chunks."""
    headers = "| Year | Revenue | Operating_Cost | Net_Profit | Margin |"
    sep = "|---|---|---|---|---|"
    rows = [
        f"| 20{i:02d} | ${100 + i * 15}M | ${60 + i * 8}M | ${40 + i * 7}M | {25 + i % 5}% |" for i in range(10, 26)
    ]
    table_text = f"### Sheet: Annual_Financials\n\n{headers}\n{sep}\n" + "\n".join(rows)

    # Split with row_overlap = 1
    chunks = _split_single_table_block(table_text, max_chunk_size=320, row_overlap=1)
    assert len(chunks) >= 3

    # Verify that every chunk has the header and separator
    for chunk in chunks:
        assert headers in chunk
        assert sep in chunk
        assert "Sheet: Annual_Financials" in chunk

    # Check that adjacent chunks share an overlapping row
    for i in range(len(chunks) - 1):
        chunk_a_lines = [ln.strip() for ln in chunks[i].splitlines() if ln.strip().startswith("| 20")]
        chunk_b_lines = [ln.strip() for ln in chunks[i + 1].splitlines() if ln.strip().startswith("| 20")]
        # Last row of chunk A should be first row of chunk B
        assert chunk_a_lines[-1] == chunk_b_lines[0], f"Row overlap missing between chunk {i} and {i + 1}"


def test_adaptive_kv_folding_for_ultra_wide_tables() -> None:
    """Validate that ultra-wide tables with many columns adapt into Key-Value records (TableLlama NAACL 2024)."""
    # Create an ultra-wide table with 30 columns
    columns = [f"Feature_Column_{c}" for c in range(1, 31)]
    headers = "| " + " | ".join(columns) + " |"
    sep = "|" + "---|" * len(columns)
    rows = ["| " + " | ".join([f"Val_R{r}_C{c}_LongDescription" for c in range(1, 31)]) + " |" for r in range(1, 5)]
    wide_table = f"### Sheet: Wide_Telemetry\n\n{headers}\n{sep}\n" + "\n".join(rows)

    # Single row is ~800+ chars, chunk size set to 400
    chunks = _split_single_table_block(wide_table, max_chunk_size=400, row_overlap=1)
    assert len(chunks) >= 4

    combined_chunks = "\n".join(chunks)
    assert "- **Feature_Column_1**:" in combined_chunks
    assert "- **Feature_Column_30**:" in combined_chunks

    for chunk in chunks:
        # Check that each sub-part converted into Key-Value pairs with header propagation
        assert "- **Feature_Column_" in chunk
        assert "(Row " in chunk
        assert "Sheet: Wide_Telemetry" in chunk


def test_parent_child_table_chunking_prevents_label_stacking() -> None:
    """Ensure that coordinate labels (Rows X-Y of Z) do not stack up across parent-child chunking passes."""
    headers = "| SKU | Item_Name | Price | Stock | Rating |"
    sep = "|---|---|---|---|---|"
    rows = [f"| SKU_{i:03d} | Product_{i} | ${i * 12}.99 | {i * 10} | 4.{i % 9} |" for i in range(1, 35)]
    table_text = f"### Sheet: Inventory_2024\n\n{headers}\n{sep}\n" + "\n".join(rows)

    doc = Document(
        page_content=table_text,
        metadata={"source": "inventory.xlsx", "document_id": "inv-001", "modality": "table"},
    )

    child_chunks, parent_records = split_documents([doc])
    assert len(child_chunks) > 1
    assert len(parent_records) >= 1

    for child in child_chunks:
        content = child.page_content
        # Ensure there is at most one '(Rows ' or '(Row ' marker per chunk (no nesting!)
        assert content.count("(Rows ") + content.count("(Row ") <= 1, f"Stacked label detected: {content[:120]}"
        assert "Sheet: Inventory_2024" in content
        assert headers in content or "- **SKU**:" in content


def test_mixed_document_modality_assignment() -> None:
    """Validate that in a mixed document, table chunks receive modality='table' and text chunks receive modality='text'."""
    mixed_doc_text = """# Corporate Policy on Travel

All employees must submit receipts within 30 days of trip completion.

### Sheet: Reimbursement_Limits

| Category | Tier_1_Limit | Tier_2_Limit |
|---|---|---|
| Lodging | $250/night | $180/night |
| Meals | $75/day | $50/day |
| Incidentals | $25/day | $15/day |

Exceptions require vice-presidential approval in writing.
"""

    doc = Document(
        page_content=mixed_doc_text,
        metadata={"source": "travel_policy.md", "document_id": "pol-01"},
    )

    child_chunks, parent_records = split_documents([doc])
    assert len(child_chunks) >= 3

    # Find the table chunk and text chunks
    table_found = False
    text_found = False
    for chunk in child_chunks:
        if "Reimbursement_Limits" in chunk.page_content:
            table_found = True
            assert chunk.metadata["modality"] == "table"
        elif "Corporate Policy on Travel" in chunk.page_content:
            text_found = True
            assert chunk.metadata.get("modality") in ("text", None)
        elif "Exceptions require vice-presidential" in chunk.page_content:
            assert chunk.metadata.get("modality") in ("text", None)

    assert table_found, "Table chunk was not identified"
    assert text_found, "Leading text chunk was not identified"
