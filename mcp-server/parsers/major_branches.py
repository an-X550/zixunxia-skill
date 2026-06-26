"""
解析 知识库/数据层/专业内部分叉速查.md

格式：每个专业是 H2 标题，下面一个 5 列统一表格。
列：方向 | 学什么 | 去哪类雇主 | 典型路径 | 选校注意
"""

import re
from pathlib import Path
from typing import Dict, List

from .table_utils import parse_md_table, split_by_headings


def parse(skill_dir: Path) -> Dict[str, List[Dict[str, str]]]:
    """
    解析专业内部分叉速查文件。

    返回：{专业名: [{方向, 学什么, 去哪类雇主, 典型路径, 选校注意}]}
    """
    filepath = skill_dir / "知识库" / "数据层" / "专业内部分叉速查.md"
    if not filepath.exists():
        return {}

    text = filepath.read_text(encoding='utf-8')

    # 跳过文件顶部的标题和前言，从第一个 ## 开始
    # 找到第一个 H2 的位置
    first_h2 = re.search(r'^## (.+)$', text, re.MULTILINE)
    if not first_h2:
        return {}

    # 从第一个 H2 开始解析
    body = text[first_h2.start():]

    # 按 H2 分割
    sections = split_by_headings(body, level=2)

    result = {}
    for major_name, content in sections.items():
        # 去除专业名中可能的注释
        major_name = major_name.strip()

        # 提取表格
        table_text = _extract_first_table(content)
        if not table_text:
            continue

        rows = parse_md_table(table_text)
        if rows:
            result[major_name] = rows

    return result


def _extract_first_table(text: str) -> str:
    """从文本中提取第一个完整 Markdown 表格"""
    lines = text.split('\n')
    table_lines = []
    in_table = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('|'):
            in_table = True
            table_lines.append(stripped)
        elif in_table and not stripped.startswith('|'):
            # 表格结束
            break

    return '\n'.join(table_lines) if table_lines else ''
