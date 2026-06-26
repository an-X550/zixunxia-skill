"""
解析 知识库/数据层/城市产业库.md

结构：6 个 H2 章节。
- 一、城市格局5层体系 → 表格
- 二、城市按产业类型分类 → 表格
- 三、关键省份核心产业集群速查 → ### 省份名 + bullet list
- 四、专业-城市匹配逻辑 → 表格
- 五、城市查询SOP框架 → 散文
- 六、2025年度中小企业特色产业集群 → 表格
"""

from pathlib import Path
from typing import Dict, List, Any
import re

from .table_utils import parse_md_table


def parse(skill_dir: Path) -> Dict[str, Any]:
    filepath = skill_dir / "知识库" / "数据层" / "城市产业库.md"
    if not filepath.exists():
        return {}

    text = filepath.read_text(encoding='utf-8')
    sections = _split_by_h2(text)

    result = {
        'city_tiers': [],
        'city_types': [],
        'provinces': {},
        'major_city_match': [],
        'family_constraints': [],
        'sop_framework': '',
        'new_clusters': [],
    }

    # 一、城市格局5层体系
    if '一、城市格局5层体系' in sections:
        tables = _extract_tables(sections['一、城市格局5层体系'])
        if tables:
            result['city_tiers'] = tables[0]

    # 二、城市按产业类型分类
    if '二、城市按产业类型分类' in sections:
        tables = _extract_tables(sections['二、城市按产业类型分类'])
        if tables:
            result['city_types'] = tables[0]

    # 三、关键省份核心产业集群速查 — 按 H3 省份分割
    if '三、关键省份核心产业集群速查' in sections:
        result['provinces'] = _parse_provinces(sections['三、关键省份核心产业集群速查'])

    # 四、专业-城市匹配逻辑
    if '四、专业-城市匹配逻辑' in sections:
        tables = _extract_tables(sections['四、专业-城市匹配逻辑'])
        if len(tables) >= 1:
            result['major_city_match'] = tables[0]
        if len(tables) >= 2:
            result['family_constraints'] = tables[1]

    # 五、城市查询SOP框架
    if '五、城市查询SOP框架' in sections:
        result['sop_framework'] = sections['五、城市查询SOP框架']

    # 六、中小企业特色产业集群
    if '六、2025年度中小企业特色产业集群（第四批）' in sections:
        tables = _extract_tables(sections['六、2025年度中小企业特色产业集群（第四批）'])
        if tables:
            result['new_clusters'] = tables[0]

    return result


def _split_by_h2(text: str) -> Dict[str, str]:
    pattern = re.compile(r'^## (.+)$', re.MULTILINE)
    matches = list(pattern.finditer(text))
    sections = {}
    for i, m in enumerate(matches):
        heading = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[heading] = text[start:end].strip()
    return sections


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


def _parse_provinces(text: str) -> Dict[str, Dict]:
    """解析省份产业集群——H3 标题 + bullet list 结构"""
    provinces = {}
    # 匹配 ### 省份名（任意括号内容可选）
    pattern = re.compile(r'^### (.+?)(?:（[^）]+）)?\s*$', re.MULTILINE)
    matches = list(pattern.finditer(text))

    for i, m in enumerate(matches):
        name = m.group(1) or m.group(2)
        if not name:
            continue
        name = name.strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()

        # 解析集群列表和优劣势产业
        clusters = []
        advantages = ''
        future = ''

        for line in content.split('\n'):
            stripped = line.strip()
            if stripped.startswith('- **') or stripped.startswith('- '):
                cluster = stripped.lstrip('- ').strip()
                clusters.append(cluster)
            elif '优势产业' in stripped:
                advantages = stripped.split('：')[-1].split(':')[-1].strip()
            elif '未来重点' in stripped:
                future = stripped.split('：')[-1].split(':')[-1].strip()

        provinces[name] = {
            'clusters': clusters,
            'advantages': advantages,
            'future_focus': future,
        }

    # 也解析"其他重点省份速览"中的表格
    tables = _extract_tables(text)
    for table in tables:
        for row in table:
            if '省份' in row and '核心产业方向' in row:
                continue  # 表头
            province_name = row.get('省份', '')
            if province_name and province_name not in provinces:
                provinces[province_name] = {
                    'clusters': [],
                    'advantages': row.get('核心产业方向', ''),
                    'future_focus': '',
                    'representative_cities': row.get('代表集群城市', ''),
                }

    return provinces
