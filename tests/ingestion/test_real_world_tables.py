"""Real-world scenario tests for table & spreadsheet processing pipeline.

This suite simulates realistic enterprise business scenarios:
1. Multi-sheet Excel workbook with merged cells, department budgets, and sales details.
2. Chinese CSV procurement reconciliation ledger with semicolon delimiters and amounts.
3. Multi-table Markdown document with nested/HTML structures.
4. End-to-end KnowledgeAgent routing on natural language business questions.
5. Ingestion and retrieval through TableExtractor and ChromaDB vector store.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from app.agents.knowledge.service import KnowledgeAgentService
from app.domain.knowledge import AccessScope
from app.domain.workflow import RouterDecision
from app.ingestion.chunking.splitter import split_documents
from app.ingestion.loaders.dispatch import load_document_with_evidence
from app.orchestration.request import OrchestrationRequest
from app.services.documents.ingest import _canonical_metadata, _index_tables


def Workbook():  # noqa: N802 -- stands in for openpyxl.Workbook at its call sites
    """openpyxl is the optional `office` extra and CI does not install it, so the
    Excel scenarios skip there instead of failing the whole module at collection;
    the CSV and Markdown scenarios beside them still run."""
    return pytest.importorskip("openpyxl").Workbook()


@pytest.fixture(autouse=True)
def _isolated_table_index(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Index into a recording stand-in, never the developer's `data/chroma`.

    `TableExtractor.index_table` writes to the `table_summaries` collection of the
    configured Chroma store. Run for real, this suite wrote into whatever store the
    machine had -- and failed wherever that store was built with a different
    embedding size (a 1024-dim BGE store against the 384-dim hash embeddings CI
    uses), which says nothing about table indexing.
    """
    indexed: list[str] = []

    class _RecordingStore:
        def add_texts(self, *, ids, texts, metadatas=None, **_):  # noqa: ARG002 -- mirrors Chroma's signature
            indexed.extend(ids)

    monkeypatch.setattr("app.retrievers.stores.vector.get_named_vector_store", lambda name: _RecordingStore())
    return indexed


@pytest.fixture
def real_env():
    """Set up temporary directory and clean up afterwards."""
    temp_dir = Path(tempfile.mkdtemp(prefix="querymind_real_world_"))
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_real_world_excel_merged_cells_and_multisheet(real_env: Path):
    """Scenario 1: Real multi-sheet enterprise budget and sales Excel file."""
    excel_path = real_env / "2024年度企业财务与销售台账.xlsx"
    wb = Workbook()

    # Sheet 1: 部门预算明细 (with merged department cells across rows)
    ws1 = wb.active
    ws1.title = "部门预算表"
    ws1.append(["部门", "预算科目", "预算金额(万元)", "责任人"])

    # Merged rows for 技术研发部 (rows 2 to 4)
    ws1.append(["技术研发部", "大模型推理服务器集群", 85.5, "张总工"])
    ws1.append([None, "向量数据库与检索节点", 42.0, "李架构师"])
    ws1.append([None, "前端微服务与网关部署", 28.3, "王研发经理"])
    ws1.merge_cells("A2:A4")

    # Merged rows for 市场运营部 (rows 5 to 7)
    ws1.append(["市场运营部", "全国开发者生态巡回会", 50.0, "赵总监"])
    ws1.append([None, "AI产业峰会特装展位", 35.0, "孙经理"])
    ws1.append([None, "新媒体技术传播投放", 60.0, "周主管"])
    ws1.merge_cells("A5:A7")

    # Sheet 2: 华东大区订单明细 (10 transaction records)
    ws2 = wb.create_sheet(title="华东大区销售明细")
    ws2.append(["订单编号", "客户名称", "销售代表", "产品型号", "成交金额(元)", "交付状态"])
    sales_data = [
        ["ORD-2024-001", "上汽集团智能网联部", "陈晓", "QueryMind 企业版", 480000, "已交付"],
        ["ORD-2024-002", "国泰君安证券科技部", "刘伟", "Knowledge Graph 套件", 350000, "实施中"],
        ["ORD-2024-003", "宝武钢铁数字化推进办", "陈晓", "多模态检索模块", 280000, "已交付"],
        ["ORD-2024-004", "哔哩哔哩AI平台部", "王芳", "Agent 编排引擎", 520000, "试运行"],
        ["ORD-2024-005", "复星医药研发中心", "刘伟", "混合 RAG 平台", 650000, "合同签订"],
    ]
    for row in sales_data:
        ws2.append(row)

    wb.save(excel_path)
    wb.close()

    # 1. Load and parse the document
    parsed, documents = load_document_with_evidence(excel_path)

    assert len(parsed.pages) == 2, "Expected 2 pages for 2 sheets"
    assert len(parsed.tables) == 2, "Expected 2 TableBlocks extracted"

    # 2. Check Sheet 1 parsed markdown content
    sheet1_table = parsed.tables[0]
    assert sheet1_table.sheet == "部门预算表"
    assert "### Sheet: 部门预算表" in sheet1_table.markdown
    assert "| 部门 | 预算科目 | 预算金额(万元) | 责任人 |" in sheet1_table.markdown

    # CRITICAL VERIFICATION: Check merged cell forward-filling!
    # Rows 3 and 4 should contain "技术研发部" despite being empty in raw openpyxl!
    assert "| 技术研发部 | 大模型推理服务器集群 | 85.5 | 张总工 |" in sheet1_table.markdown
    assert "| 技术研发部 | 向量数据库与检索节点 | 42 | 李架构师 |" in sheet1_table.markdown
    assert "| 技术研发部 | 前端微服务与网关部署 | 28.3 | 王研发经理 |" in sheet1_table.markdown

    # Rows 6 and 7 should contain "市场运营部"!
    assert "| 市场运营部 | 全国开发者生态巡回会 | 50 | 赵总监 |" in sheet1_table.markdown
    assert "| 市场运营部 | AI产业峰会特装展位 | 35 | 孙经理 |" in sheet1_table.markdown
    assert "| 市场运营部 | 新媒体技术传播投放 | 60 | 周主管 |" in sheet1_table.markdown

    # 3. Check Sheet 2 parsed content
    sheet2_table = parsed.tables[1]
    assert sheet2_table.sheet == "华东大区销售明细"
    assert "### Sheet: 华东大区销售明细" in sheet2_table.markdown
    assert "上汽集团智能网联部" in sheet2_table.markdown
    assert "国泰君安证券科技部" in sheet2_table.markdown

    # 4. Check chunking: split_documents should preserve table headers on every child chunk
    chunks, parents = split_documents(documents)
    assert len(chunks) >= 2
    for chunk in chunks:
        content = chunk.page_content
        if "部门预算表" in content:
            assert "| 部门 | 预算科目 | 预算金额(万元) | 责任人 |" in content
            assert "| --- | --- | --- | --- |" in content
        elif "华东大区销售明细" in content:
            assert "| 订单编号 | 客户名称 | 销售代表 | 产品型号 | 成交金额(元) | 交付状态 |" in content

    # 5. Index through the multimodal table indexer
    canonical = _canonical_metadata(parsed)
    indexed_count = _index_tables(parsed, canonical)
    assert indexed_count == 2, "Expected both tables to be successfully indexed"


def test_real_world_csv_procurement_ledger(real_env: Path):
    """Scenario 2: Real enterprise CSV procurement ledger with semicolons and amounts."""
    csv_path = real_env / "2024Q3供应链采购对账单.csv"
    csv_content = (
        "采购批次;供应商名称;物资类别;结算金额;付款状态\n"
        "PO-20240901;华为技术有限公司;算力服务器;1280000.00;已付讫\n"
        "PO-20240902;中兴通讯股份有限公司;高速网络交换机;450000.00;审核中\n"
        "PO-20240903;上海泛微网络科技;协同办公平台;180000.00;待付款\n"
        "PO-20240904;北京百度网讯科技;AI标注服务;95000.00;已付讫\n"
        "PO-20240905;阿里云计算有限公司;云存储资源池;320000.00;待对账\n"
    )
    csv_path.write_text(csv_content, encoding="utf-8")

    parsed, documents = load_document_with_evidence(csv_path)

    assert len(parsed.tables) == 1
    table = parsed.tables[0]
    assert "| 采购批次 | 供应商名称 | 物资类别 | 结算金额 | 付款状态 |" in table.markdown
    assert "| PO-20240901 | 华为技术有限公司 | 算力服务器 | 1280000.00 | 已付讫 |" in table.markdown
    assert "| PO-20240903 | 上海泛微网络科技 | 协同办公平台 | 180000.00 | 待付款 |" in table.markdown

    # Verify indexing
    canonical = _canonical_metadata(parsed)
    assert _index_tables(parsed, canonical) == 1


def test_real_world_markdown_with_embedded_tables(real_env: Path):
    """Scenario 3: Real markdown specification document with embedded table."""
    md_path = real_env / "系统集群架构规格表.md"
    md_content = (
        "# 智询系统集群部署规范\n\n"
        "以下为生产环境各组件的硬件资源规格表：\n\n"
        "| 模块名称 | 实例数 | CPU核心 | 内存(GB) | 存储规格 | 高可用模式 |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| API网关 | 3 | 4C | 8GB | 50GB SSD | 多活负载均衡 |\n"
        "| LangGraph编排节点 | 4 | 8C | 16GB | 100GB SSD | 状态检查点持久化 |\n"
        "| Chroma向量引擎 | 2 | 16C | 64GB | 500GB NVMe | 主从备份 |\n"
        "| Neo4j图数据库 | 2 | 8C | 32GB | 200GB NVMe | 读写分离集群 |\n\n"
        "部署说明：所有节点运行于独立安全隔离子网。\n"
    )
    md_path.write_text(md_content, encoding="utf-8")

    parsed, documents = load_document_with_evidence(md_path)

    # Markdown document now has TableBlock extracted!
    assert len(parsed.tables) == 1
    tbl = parsed.tables[0]
    assert "| 模块名称 | 实例数 | CPU核心 | 内存(GB) | 存储规格 | 高可用模式 |" in tbl.markdown
    assert "LangGraph编排节点" in tbl.markdown
    assert "Chroma向量引擎" in tbl.markdown

    # Verify table indexing works on Markdown-extracted tables
    canonical = _canonical_metadata(parsed)
    assert _index_tables(parsed, canonical) == 1


@pytest.mark.asyncio
async def test_real_world_business_query_routing():
    """Scenario 4: Test KnowledgeAgentService routing on real-world business queries."""
    service = KnowledgeAgentService()
    scope = AccessScope(
        tenant_id="tenant-acme",
        user_id="user-ops",
        role="analyst",
        allowed_sources=frozenset({"doc-sales-1"}),
        document_ids=frozenset({"doc-sales-1"}),
    )

    test_queries = [
        ("请查询华东大区销售明细报表中的大额订单", "报表"),
        ("查看供应链采购对账单里的待付款供应商", "对账单/清单"),
        ("这份财务台账里各部门的预算总额是多少？", "台账"),
        ("分析这份excel里的销售利润率", "excel"),
        ("请解析csv文件中的所有异常流水记录", "csv"),
        ("列出数据表里的所有客户名单", "数据表"),
        ("Check the spreadsheet sheet for Q3 totals", "spreadsheet/sheet"),
    ]

    for question, rationale in test_queries:
        req = OrchestrationRequest(question=question)
        router_decision = RouterDecision(
            intent="knowledge_retrieval",
            complexity="simple",
            completeness="complete",
            next_stage="knowledge",
            knowledge_hints=frozenset({"vector"}),
            confidence=0.9,
            reason="user_business_query",
        )

        strategy = await service.decide(req, router_decision, plan=None, scope=scope)
        sources = {plan.source for plan in strategy.sources}

        assert "multimodal" in sources, (
            f"Query '{question}' ({rationale}) failed to route to 'multimodal'. Selected sources: {sources}"
        )
