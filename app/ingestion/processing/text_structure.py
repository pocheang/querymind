"""OCR text structure extraction and normalization."""

import re
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class TextBlock:
    """Structured text block with type and content."""

    type: Literal["title", "heading", "paragraph", "list_item", "table_row", "code", "unknown"]
    content: str
    level: int = 0  # For headings: 1-6, for lists: indent level
    confidence: float = 1.0
    metadata: dict = field(default_factory=dict)


class OCRTextStructurer:
    """Extract structure from OCR text."""

    def __init__(self):
        # 编译正则表达式（性能优化）
        self.title_patterns = [
            re.compile(r"^[A-Z\s]{3,30}$"),
            re.compile(r"^第[一二三四五六七八九十\d]+[章节部分]"),
            re.compile(r"^Chapter\s+\d+", re.IGNORECASE),
            re.compile(r"^\d+\.\s*[A-Z]"),
        ]

        # 列表模式
        self.list_patterns = [
            re.compile(r"^[\s]*[•·●○■□▪▫]\s+"),  # 项目符号
            re.compile(r"^[\s]*[\d]+[.、)]\s+"),  # 数字列表
            re.compile(r"^[\s]*[a-zA-Z][.、)]\s+"),  # 字母列表
            re.compile(r"^[\s]*[(（][一二三四五六七八九十\d]+[)）]\s+"),  # 括号列表
            re.compile(r"^[\s]*[一二三四五六七八九十]+、\s*"),  # 中文顿号列表
        ]

        # 表格模式
        self.table_patterns = [
            # A cell does not contain its own delimiter (python:S8786); these
            # answer a yes/no question, so matching to the first one is the
            # same answer as matching to the last.
            re.compile(r"[|｜][^|｜\n]+[|｜]"),
            re.compile(r"\t[^\t\n]+\t"),
        ]

        # CJK 标点符号
        self.cjk_punctuation = '。，、；：！？""（）【】《》'

    def structure_text(self, text: str) -> list[TextBlock]:
        """将 OCR 文本转换为结构化块."""
        if not text or not text.strip():
            return []

        lines = text.splitlines()
        blocks: list[TextBlock] = []

        i = 0
        while i < len(lines):
            line = lines[i].rstrip()

            # 跳过空行
            if not line.strip():
                i += 1
                continue

            # 检测标题
            if self._is_title(line):
                blocks.append(
                    TextBlock(type="title", content=line.strip(), level=self._get_heading_level(line), confidence=0.8)
                )
                i += 1
                continue

            # 检测列表
            list_match = self._match_list(line)
            if list_match:
                indent_level = len(line) - len(line.lstrip())
                # 移除列表前缀，只保留内容
                clean_content = self._remove_list_prefix(line.strip())
                blocks.append(
                    TextBlock(
                        type="list_item",
                        content=clean_content,
                        level=indent_level // 2,  # 假设每级缩进2个空格
                        confidence=0.9,
                        metadata={"raw": line.strip()},
                    )
                )
                i += 1
                continue

            # 检测表格行
            if self._is_table_row(line):
                blocks.append(TextBlock(type="table_row", content=line.strip(), confidence=0.7))
                i += 1
                continue

            # 检测代码块（缩进 + 特殊字符）
            if self._is_code_line(line):
                block, i = self._consume_code_block(lines, i)
                blocks.append(block)
                continue

            # 合并段落（连续的普通行）
            block, i = self._consume_paragraph(lines, i)
            blocks.append(block)

        return blocks

    def _consume_code_block(self, lines: list[str], start: int) -> tuple[TextBlock, int]:
        """Collect the contiguous run of code-classified lines starting at `start`."""
        i = start
        code_lines = [lines[i].rstrip()]
        i += 1
        while i < len(lines) and self._is_code_line(lines[i]):
            code_lines.append(lines[i])
            i += 1
        return TextBlock(type="code", content="\n".join(code_lines), confidence=0.6), i

    def _consume_paragraph(self, lines: list[str], start: int) -> tuple[TextBlock, int]:
        """Collect contiguous plain lines starting at `start` into one paragraph block."""
        i = start
        para_lines = [lines[i].rstrip()]
        i += 1
        while i < len(lines):
            next_line = lines[i].rstrip()
            if not next_line.strip():
                break
            if self._is_title(next_line) or self._match_list(next_line) or self._is_table_row(next_line):
                break
            para_lines.append(next_line)
            i += 1
        content = self._merge_paragraph_lines(para_lines)
        return TextBlock(type="paragraph", content=content, confidence=1.0), i

    def _is_title(self, line: str) -> bool:
        """判断是否为标题."""
        stripped = line.strip()
        if not stripped or len(stripped) > 100:
            return False

        for pattern in self.title_patterns:
            if pattern.match(stripped):
                return True

        # 短行 + 全大写/数字开头
        if len(stripped) < 50:
            if stripped.isupper() or re.match(r"^\d+\.?\s+[A-Z]", stripped):
                return True

        return False

    def _get_heading_level(self, line: str) -> int:
        """获取标题级别 (1-6)."""
        stripped = line.strip()

        # Markdown 风格
        if stripped.startswith("#"):
            return min(6, stripped.count("#"))

        # 中文章节
        if re.match(r"^第[一二三四五六七八九十]章", stripped):
            return 1
        if re.match(r"^第[一二三四五六七八九十]节", stripped):
            return 2

        # 数字层级
        if re.match(r"^\d+\.\s", stripped):
            return 2
        if re.match(r"^\d+\.\d+\.\s", stripped):
            return 3

        # 默认
        return 1 if len(stripped) < 30 else 2

    def _match_list(self, line: str) -> re.Match | None:
        """匹配列表项."""
        for pattern in self.list_patterns:
            match = pattern.match(line)
            if match:
                return match
        return None

    def _remove_list_prefix(self, line: str) -> str:
        """移除列表前缀，只保留内容."""
        match = self._match_list(line)
        if match:
            # 移除匹配的前缀部分
            return line[match.end() :].strip()
        return line

    def _is_table_row(self, line: str) -> bool:
        """判断是否为表格行."""
        for pattern in self.table_patterns:
            if pattern.search(line):
                return True
        return False

    def _is_code_line(self, line: str) -> bool:
        """判断是否为代码行."""
        stripped = line.strip()
        if not stripped:
            return False

        # 缩进 + 特殊字符
        indent = len(line) - len(line.lstrip())
        if indent >= 4:
            # 包含代码特征字符
            code_chars = ["{", "}", "(", ")", ";", "=", "<", ">", "[", "]"]
            if any(ch in stripped for ch in code_chars):
                return True

        return False

    def _paragraph_join_prefix(self, prev: str) -> str:
        """The separator to place before the next line, based on how `prev` ends.

        Chinese, or a line ending in Chinese punctuation, joins with nothing;
        an alphanumeric (English) ending gets a space so words don't run
        together.
        """
        last_char = prev[-1]
        if self._is_cjk_char(last_char) or last_char in self.cjk_punctuation:
            return ""
        if last_char.isalnum():
            return " "
        return ""

    def _merge_paragraph_lines(self, lines: list[str]) -> str:
        """智能合并段落行."""
        if not lines:
            return ""

        if len(lines) == 1:
            return lines[0].strip()

        merged: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if not merged:
                merged.append(stripped)
                continue
            merged.append(self._paragraph_join_prefix(merged[-1]) + stripped)

        return "".join(merged)

    def _is_cjk_char(self, char: str) -> bool:
        """判断是否为中日韩字符."""
        if not char:
            return False
        code = ord(char)
        return (
            0x4E00 <= code <= 0x9FFF  # CJK 统一汉字
            or 0x3400 <= code <= 0x4DBF  # CJK 扩展 A
            or 0x20000 <= code <= 0x2A6DF
        )  # CJK 扩展 B


def structure_ocr_text(text: str) -> list[TextBlock]:
    """便捷函数：结构化 OCR 文本."""
    structurer = OCRTextStructurer()
    return structurer.structure_text(text)


def blocks_to_markdown(blocks: list[TextBlock]) -> str:
    """将结构化块转换为 Markdown."""
    lines = []

    for block in blocks:
        if block.type == "title":
            prefix = "#" * block.level
            lines.append(f"{prefix} {block.content}\n")

        elif block.type == "heading":
            prefix = "#" * min(block.level, 6)
            lines.append(f"{prefix} {block.content}\n")

        elif block.type == "paragraph":
            lines.append(f"{block.content}\n")

        elif block.type == "list_item":
            indent = "  " * block.level
            # 修复：不重复列表标记
            lines.append(f"{indent}- {block.content}")

        elif block.type == "table_row":
            lines.append(f"{block.content}")

        elif block.type == "code":
            lines.append(f"```\n{block.content}\n```\n")

        else:
            lines.append(f"{block.content}\n")

    return "\n".join(lines)
