"""Tests for OCR text structure extraction."""

import pytest

from app.ingestion.utils.text_structure import (
    OCRTextStructurer,
    TextBlock,
    blocks_to_markdown,
    blocks_to_plain_text,
    structure_ocr_text,
)


def test_basic_paragraph():
    """Test basic paragraph detection."""
    text = "这是第一行。\n这是第二行。\n这是第三行。"
    blocks = structure_ocr_text(text)

    assert len(blocks) == 1
    assert blocks[0].type == "paragraph"
    assert "第一行" in blocks[0].content


def test_title_detection():
    """Test title detection."""
    text = """第一章 引言

这是正文内容。

第二节 背景

更多内容。"""

    blocks = structure_ocr_text(text)

    titles = [b for b in blocks if b.type == "title"]
    assert len(titles) >= 2
    assert any("第一章" in b.content for b in titles)


def test_list_detection():
    """Test list item detection."""
    text = """正文段落。

• 第一项
• 第二项
• 第三项

继续正文。"""

    blocks = structure_ocr_text(text)

    list_items = [b for b in blocks if b.type == "list_item"]
    assert len(list_items) == 3
    assert any("第一项" in b.content for b in list_items)


def test_numbered_list():
    """Test numbered list detection."""
    text = """1. 第一步
2. 第二步
3. 第三步"""

    blocks = structure_ocr_text(text)

    list_items = [b for b in blocks if b.type == "list_item"]
    assert len(list_items) == 3


def test_table_detection():
    """Test table row detection."""
    text = """| 列1 | 列2 | 列3 |
| 数据1 | 数据2 | 数据3 |"""

    blocks = structure_ocr_text(text)

    table_rows = [b for b in blocks if b.type == "table_row"]
    assert len(table_rows) == 2


def test_chinese_paragraph_merge():
    """Test Chinese paragraph line merging."""
    text = """这是第一行文字内容，
应该被合并到一起，
形成完整的段落。"""

    blocks = structure_ocr_text(text)

    assert len(blocks) == 1
    assert blocks[0].type == "paragraph"
    # 中文应该无缝连接
    assert "，应该" in blocks[0].content or "，\n应该" in blocks[0].content


def test_english_paragraph_merge():
    """Test English paragraph line merging."""
    text = """This is the first line
and this is the second line
that should be merged together."""

    blocks = structure_ocr_text(text)

    assert len(blocks) == 1
    assert blocks[0].type == "paragraph"
    # 英文应该有空格
    assert "line and" in blocks[0].content or "line\nand" in blocks[0].content


def test_mixed_content():
    """Test mixed content structure."""
    text = """第一章 测试文档

这是一个段落，包含多行
内容应该被正确识别。

主要特点：
• 特点一
• 特点二
• 特点三

1. 步骤一
2. 步骤二

| 表头1 | 表头2 |
| 数据1 | 数据2 |"""

    blocks = structure_ocr_text(text)

    # 应该包含多种类型
    types = {b.type for b in blocks}
    assert "title" in types or "paragraph" in types
    assert "list_item" in types
    assert "table_row" in types


def test_blocks_to_markdown():
    """Test converting blocks to Markdown."""
    blocks = [
        TextBlock(type="title", content="标题", level=1),
        TextBlock(type="paragraph", content="段落内容"),
        TextBlock(type="list_item", content="列表项", level=0),
    ]

    markdown = blocks_to_markdown(blocks)

    assert "# 标题" in markdown
    assert "段落内容" in markdown
    assert "- 列表项" in markdown


def test_blocks_to_plain_text():
    """Test converting blocks to plain text."""
    blocks = [
        TextBlock(type="title", content="标题", level=1),
        TextBlock(type="paragraph", content="段落内容"),
    ]

    plain = blocks_to_plain_text(blocks)

    assert "标题" in plain
    assert "段落内容" in plain
    assert "=" in plain  # Title separator


def test_empty_text():
    """Test handling empty text."""
    blocks = structure_ocr_text("")
    assert blocks == []

    blocks = structure_ocr_text("   \n\n   ")
    assert blocks == []


def test_heading_levels():
    """Test heading level detection."""
    structurer = OCRTextStructurer()

    assert structurer._get_heading_level("第一章 标题") == 1
    assert structurer._get_heading_level("第二节 小节") == 2
    assert structurer._get_heading_level("1. 一级") == 2
    assert structurer._get_heading_level("1.1. 二级") == 3


def test_code_detection():
    """Test code block detection."""
    text = """正文内容

    def hello():
        print("world")
        return True

继续正文"""

    blocks = structure_ocr_text(text)

    code_blocks = [b for b in blocks if b.type == "code"]
    assert len(code_blocks) >= 1
    assert "def hello" in code_blocks[0].content


def test_real_ocr_output():
    """Test with realistic OCR output (with noise)."""
    text = """产品说明书

第 一 章   概述

本 产 品 是 一 款 高 性 能 设 备 ， 具 有 以 下 特 点 ：

1 ． 高 效 率
2 ． 低 功 耗
3 ． 易 操 作

技 术 参 数 ：
| 参 数 | 数 值 |
| 电 压 | 220V |"""

    blocks = structure_ocr_text(text)

    # 应该能识别出基本结构
    assert len(blocks) > 0

    # 至少有段落
    paragraphs = [b for b in blocks if b.type == "paragraph"]
    assert len(paragraphs) > 0


def test_indented_lists():
    """Test nested list detection."""
    text = """• 一级项目
  • 二级项目
    • 三级项目
• 另一个一级项目"""

    blocks = structure_ocr_text(text)

    list_items = [b for b in blocks if b.type == "list_item"]
    assert len(list_items) == 4

    # 检查缩进级别
    levels = [b.level for b in list_items]
    assert max(levels) > 0  # 应该有不同的缩进级别
