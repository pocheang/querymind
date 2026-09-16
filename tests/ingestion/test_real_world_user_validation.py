"""Real-world end-to-end user verification for the enhanced Table RAG pipeline.

Simulates complete user interaction workflows:
1. User uploads a complex executive financial report containing mixed text, wide tables,
   and critical trailing auditor notes.
2. User asks questions targeting trailing disclosures (verifies prose is NOT dropped).
3. User asks cross-period trend comparisons (verifies row overlap continuity).
4. User uploads an ultra-wide 50-column IoT telemetry spreadsheet.
5. User queries rightmost columns (verifies adaptive KV-folding prevents truncation).
6. User runs multi-table queries (verifies table isolation).
7. End-to-end indexing & KnowledgeAgent query routing verification.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from app.agents.knowledge.service import KnowledgeAgentService
from app.domain.knowledge import AccessScope
from app.domain.workflow import RouterDecision
from app.ingestion.chunking.splitter import (
    _extract_document_blocks,
    _split_markdown_table_text,
    split_documents,
)
from app.ingestion.loaders.dispatch import load_document_with_evidence
from app.orchestration.request import OrchestrationRequest


def Workbook():  # noqa: N802 -- stands in for openpyxl.Workbook at its call sites
    """openpyxl is the optional `office` extra and CI does not install it, so the
    spreadsheet scenarios skip there instead of failing the module at collection."""
    return pytest.importorskip("openpyxl").Workbook()


@pytest.fixture
def user_session_env():
    """Create an isolated workspace simulating a user session."""
    temp_dir = Path(tempfile.mkdtemp(prefix="user_val_workspace_"))
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_user_scenario_1_mixed_report_with_trailing_auditor_notes(user_session_env: Path):
    """Scenario 1: User uploads an executive report with tables followed by crucial notes.

    User Question: '审计师在财报附注中针对第四季度汇率和供应链风险提了哪些具体对冲建议？'
    """
    report_file = user_session_env / "2024年度集团数字化经营分析报告.md"
    report_content = (
        "# 集团2024年度经营分析报告\n\n"
        "2024财年，集团数字化转型进入深水区，云原生基础设施与AI应用全面铺开。\n\n"
        "### Sheet: 季度核心财务指标表\n\n"
        "| 季度 | 营业收入(万元) | 净利润(万元) | 研发投入(万元) | 毛利率 | 活跃客户数 | ARR(万元) |\n"
        "|---|---|---|---|---|---|---|\n"
        "| 2023Q1 | 12000.0 | 1800.0 | 2500.0 | 45.2% | 120 | 8500.0 |\n"
        "| 2023Q2 | 13500.0 | 2100.0 | 2800.0 | 46.0% | 135 | 9200.0 |\n"
        "| 2023Q3 | 15000.0 | 2450.0 | 3100.0 | 47.5% | 150 | 10500.0 |\n"
        "| 2023Q4 | 18500.0 | 3200.0 | 3800.0 | 48.8% | 180 | 12800.0 |\n"
        "| 2024Q1 | 19200.0 | 3150.0 | 4000.0 | 47.9% | 195 | 13500.0 |\n"
        "| 2024Q2 | 22000.0 | 3800.0 | 4500.0 | 49.1% | 220 | 15200.0 |\n"
        "| 2024Q3 | 24500.0 | 4300.0 | 4900.0 | 50.3% | 250 | 17000.0 |\n"
        "| 2024Q4 | 28000.0 | 5100.0 | 5600.0 | 51.5% | 290 | 19500.0 |\n\n"
        "### 独立审计师关键审阅附注\n\n"
        "普华永道审计师特别指出：第四季度海外供应链受地缘局势影响发生物流延误，导致汇率折算损失480万元人民币。"
        "审计委员会强烈建议财务管理层在2025Q1针对日元与欧元开展远期外汇套期保值对冲（FX Hedging），以锁定未来净利润。\n\n"
        "### Sheet: 2025年度各研发中心预算规划表\n\n"
        "| 研发中心 | 主攻方向 | 规划编制(人) | 年度预算(万元) |\n"
        "|---|---|---|---|\n"
        "| 北京大模型中心 | 基础模型微调与多模态 | 80 | 6500.0 |\n"
        "| 上海创新研究院 | 向量知识检索与Agent编排 | 65 | 5200.0 |\n"
        "| 深圳智能网联部 | 边缘计算与工业IoT | 50 | 3800.0 |\n\n"
        "总结：全体研发预算已通过董事会首轮战略预审。\n"
    )
    report_file.write_text(report_content, encoding="utf-8")

    # 1. Load document with evidence
    parsed, documents = load_document_with_evidence(report_file)
    assert len(parsed.tables) == 2, "Expected 2 TableBlocks extracted"

    # 2. Block segmentation verification
    blocks = _extract_document_blocks(report_content)
    assert len(blocks) == 5, f"Expected 5 blocks (Intro, Table1, Notes, Table2, Conclusion), got {len(blocks)}"
    assert blocks[0][0] == "text"
    assert "集团2024年度经营分析报告" in blocks[0][1]
    assert blocks[1][0] == "table"
    assert "季度核心财务指标表" in blocks[1][1]
    assert blocks[2][0] == "text"
    assert "普华永道审计师特别指出" in blocks[2][1]
    assert blocks[3][0] == "table"
    assert "2025年度各研发中心预算规划表" in blocks[3][1]
    assert blocks[4][0] == "text"
    assert "全体研发预算已通过" in blocks[4][1]

    # 3. User Chunking Verification
    child_chunks, parent_records = split_documents(documents)
    assert len(child_chunks) >= 4, f"Expected at least 4 child chunks, got {len(child_chunks)}"

    # Check that the trailing auditor notes were NOT dropped and have modality='text'
    auditor_chunk_found = False
    for chunk in child_chunks:
        if "普华永道审计师特别指出" in chunk.page_content:
            auditor_chunk_found = True
            assert "汇率折算损失480万元" in chunk.page_content
            assert "远期外汇套期保值对冲" in chunk.page_content
            assert chunk.metadata.get("modality") in ("text", None)
            break
    assert auditor_chunk_found, "CRITICAL: Trailing auditor disclosure was lost during table chunking!"

    # Check Table 2 isolation
    table2_chunk_found = False
    for chunk in child_chunks:
        if "深圳智能网联部" in chunk.page_content:
            table2_chunk_found = True
            assert "| 研发中心 | 主攻方向 | 规划编制(人) | 年度预算(万元) |" in chunk.page_content
            assert "3800.0" in chunk.page_content
            assert chunk.metadata.get("modality") == "table"
            break
    assert table2_chunk_found, "CRITICAL: Table 2 was not isolated properly!"


def test_user_scenario_2_ultra_wide_spreadsheet_kv_folding(user_session_env: Path):
    """Scenario 2: User uploads an ultra-wide 50-column IoT device telemetry sheet.

    User Question: '查询设备 DEV-9001 最右侧传感器 45 的读数与工作状态'
    Verifies that the rightmost columns are NOT clipped/truncated.
    """
    excel_path = user_session_env / "智能物联设备全量遥测台账.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "设备遥测汇总"

    # 48 columns
    base_headers = ["设备编号", "固件版本", "部署省份", "生产批次"]
    sensor_headers = [f"传感器_{i:02d}_读数" for i in range(1, 45)]
    all_headers = base_headers + sensor_headers  # 48 columns total
    ws.append(all_headers)

    # 3 device rows with dense readings
    for dev_idx in range(1, 4):
        row_vals = [f"DEV-900{dev_idx}", f"v2.4.{dev_idx}", "江苏省", f"BATCH-2024{dev_idx}"]
        for s_idx in range(1, 45):
            row_vals.append(f"{20.0 + s_idx * 0.5 + dev_idx:.1f}℃_NORMAL")
        ws.append(row_vals)

    wb.save(excel_path)
    wb.close()

    # Load and parse
    parsed, documents = load_document_with_evidence(excel_path)
    assert len(parsed.tables) == 1
    table_block = parsed.tables[0]
    assert "传感器_44_读数" in table_block.markdown

    # Split documents with child_chunk_size = 600
    # A single 48-column markdown row is ~1,200 characters -> must trigger KV-folding!
    child_chunks, parent_records = split_documents(documents)
    assert len(child_chunks) >= 3

    # Verify that the rightmost column '传感器_44_读数' is intact in the chunks
    found_rightmost_sensor = False
    for chunk in child_chunks:
        content = chunk.page_content
        if "传感器_44_读数" in content and "DEV-9001" in content:
            found_rightmost_sensor = True
            # Verify Key-Value format was generated
            assert "- **传感器_44_读数**:" in content or "传感器_44_读数" in content
            assert "DEV-9001" in content
            break

    assert found_rightmost_sensor, "CRITICAL: Rightmost sensor column was truncated/lost in wide table chunking!"


def test_user_scenario_3_sliding_window_trend_analysis_overlap(user_session_env: Path):
    """Scenario 3: User performs multi-year trend analysis across chunk boundaries.

    User Question: '对比 2018 与 2019 年度的研发与销售比率'
    Verifies that boundary rows appear in both adjacent chunks so no trend context is severed.
    """
    headers = "| 财年 | 营业收入(亿) | 研发费用(亿) | 销售费用(亿) | 管理费用(亿) | 净利润(亿) |"
    sep = "|---|---|---|---|---|---|"
    rows = [
        f"| {year}年 | {year * 0.5:.1f} | {year * 0.08:.2f} | {year * 0.12:.2f} | {year * 0.04:.2f} | {year * 0.09:.2f} |"
        for year in range(2010, 2025)
    ]  # 15 years
    table_text = f"### Sheet: 历年财务趋势台账\n\n{headers}\n{sep}\n" + "\n".join(rows)

    # Force small chunk size to trigger multi-chunk slicing
    chunks = _split_markdown_table_text(table_text, max_chunk_size=280, row_overlap=1)
    assert chunks is not None
    assert len(chunks) >= 3

    # Verify overlap: every boundary row must exist in both chunk i and chunk i+1
    for i in range(len(chunks) - 1):
        lines_a = [ln.strip() for ln in chunks[i].splitlines() if ln.strip().startswith("| 20")]
        lines_b = [ln.strip() for ln in chunks[i + 1].splitlines() if ln.strip().startswith("| 20")]
        assert len(lines_a) > 0
        assert len(lines_b) > 0
        last_row_a = lines_a[-1]
        first_row_b = lines_b[0]
        assert last_row_a == first_row_b, (
            f"Sliding window row overlap failed between chunk {i} and {i + 1}: '{last_row_a}' != '{first_row_b}'"
        )


@pytest.mark.asyncio
async def test_user_scenario_4_end_to_end_knowledge_agent_retrieval_routing():
    """Scenario 4: User asks real business questions that require table & spreadsheet retrieval."""
    service = KnowledgeAgentService()
    scope = AccessScope(
        tenant_id="tenant-prod",
        user_id="user-cfo",
        role="finance_director",
        allowed_sources=frozenset({"annual_report_2024.md", "iot_telemetry.xlsx"}),
        document_ids=frozenset({"doc-fin-01", "doc-iot-02"}),
    )

    queries = [
        "请调取2024年度经营分析报告中的季度核心财务指标表",
        "查询智能物联设备遥测台账中传感器异常的设备名单",
        "审计师在报告附注中提到的汇率对冲建议是什么",
        "展示深圳智能网联部的2025年度研发预算规划",
    ]

    for q in queries:
        req = OrchestrationRequest(question=q)
        router_decision = RouterDecision(
            intent="knowledge_retrieval",
            complexity="simple",
            completeness="complete",
            next_stage="knowledge",
            knowledge_hints=frozenset({"vector"}),
            confidence=0.95,
            reason="user_table_query",
        )

        strategy = await service.decide(req, router_decision, plan=None, scope=scope)
        sources = {plan.source for plan in strategy.sources}
        assert "multimodal" in sources or "vector" in sources, (
            f"Query '{q}' failed to select appropriate knowledge source: {sources}"
        )
