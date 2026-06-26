"""
解析 知识库/数据层/专业决策库.md

结构：
- 一、12学科门类速查 → 4列表格
- 二~五：各门类专业卡片 → H3(门类) → H4(专业名) → 2列字段表
- 六、专业名称误区速查表 → 4列表格
- 七、2025新增专业方向速查 → 表格
"""

from pathlib import Path
from typing import Dict, List, Any
import re

from .table_utils import parse_md_table


def parse(skill_dir: Path) -> Dict[str, Any]:
    filepath = skill_dir / "知识库" / "数据层" / "专业决策库.md"
    if not filepath.exists():
        return {}

    text = filepath.read_text(encoding='utf-8')
    result = {
        'categories': [],        # 12门类速查
        'majors': {},            # {专业名: {6字段}}
        'naming_traps': [],      # 60+名称误区
        'new_majors_2025': [],   # 2025新增专业
        'section_vii': '',       # Prompt1 检索提示
    }

    # 一、12学科门类速查
    cat_match = re.search(r'## 一、12学科门类速查\n(.*?)(?=\n## |\n---)', text, re.DOTALL)
    if cat_match:
        tables = _extract_tables(cat_match.group(1))
        if tables:
            result['categories'] = tables[0]

    # 二~五、各门类专业卡片
    # 找 "## 二、" 到 "## 六、" 之间的内容
    start_m = re.search(r'^## 二、', text, re.MULTILINE)
    end_m = re.search(r'^## 六、', text, re.MULTILINE)
    if start_m and end_m:
        major_body = text[start_m.start():end_m.start()]
        result['majors'] = _parse_major_cards(major_body)
    elif start_m:
        major_body = text[start_m.start():]
        result['majors'] = _parse_major_cards(major_body)

    # 六、专业名称误区速查表
    trap_match = re.search(r'## 六、专业名称误区速查表.*?\n(.*?)(?=\n## |\n---)', text, re.DOTALL)
    if trap_match:
        tables = _extract_tables(trap_match.group(0))
        if tables:
            result['naming_traps'] = tables[0]

    # 七、2025年新增专业
    new_match = re.search(r'## 七、2025年新增专业方向速查\n(.*?)(?=\n## |\n---|\Z)', text, re.DOTALL)
    if new_match:
        tables = _extract_tables(new_match.group(0))
        if tables:
            result['new_majors_2025'] = tables[0]

    return result


def _parse_major_cards(text: str) -> Dict[str, Dict[str, str]]:
    """解析专业卡片——H4 标题 + 2列字段表"""
    majors = {}

    # 按 H4 标题分割
    pattern = re.compile(r'^#### (.+)$', re.MULTILINE)
    matches = list(pattern.finditer(text))

    for i, m in enumerate(matches):
        name = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()

        # 提取2列表格
        tables = _extract_tables(content)
        if tables:
            # 将 字段|内容 格式转为 dict
            card = {}
            for row in tables[0]:
                field = row.get('字段', '').strip().strip('*')
                value = row.get('内容', '')
                if field:
                    card[field] = value
            if card:
                majors[name] = card

    return majors


def _extract_tables(text: str) -> List[List[Dict[str, str]]]:
    tables = []
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith('|'):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i].strip())
                i += 1
            if len(table_lines) >= 2:
                parsed = parse_md_table('\n'.join(table_lines))
                if parsed:
                    tables.append(parsed)
        else:
            i += 1
    return tables
