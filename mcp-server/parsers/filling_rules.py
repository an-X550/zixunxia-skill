"""
解析 知识库/数据层/填报规则库.md

结构：9 个 H2 章节，混有表格和散文。
- 一、录取流程核心概念 → 定义表 + 散文
- 二、专业分配规则 → 定义表 + 对比表
- 三、新高考选科与赋分 → 表格
- 四、志愿填报模式与各省归属 → 省模式表（核心）
- 五~九：散文 + 表格混合
"""

from pathlib import Path
from typing import Dict, List, Any
import re

from .table_utils import parse_md_table


def parse(skill_dir: Path) -> Dict[str, Any]:
    filepath = skill_dir / "知识库" / "数据层" / "填报规则库.md"
    if not filepath.exists():
        return {}

    text = filepath.read_text(encoding='utf-8')
    sections = _split_by_h2(text)

    result = {
        'concepts': {},          # 一、核心概念
        'allocation_rules': {},  # 二、专业分配规则
        'subject_selection': {}, # 三、选科与赋分
        'province_configs': {},  # 四、各省模式 + 志愿数量
        'batch_strategy': {},    # 五、分批录取
        'wenbao_strategy': {},   # 六、稳保策略
        'rank_conversion': {},   # 七、位次转换
        'traps': [],             # 八、常见填报陷阱
        'ai_boundary': '',       # 九、咨询中AI边界
    }

    for heading, content in sections.items():
        tables = _extract_tables(content)

        if '录取流程核心概念' in heading:
            result['concepts'] = {
                'tables': tables,
                'full_text': content,
            }

        elif '专业分配规则' in heading:
            result['allocation_rules'] = {
                'tables': tables,
                'full_text': content,
            }

        elif '新高考选科' in heading:
            result['subject_selection'] = {
                'tables': tables,
                'full_text': content,
            }

        elif '志愿填报模式' in heading:
            # 核心：解析省模式表
            if tables:
                for t in tables:
                    if '省份' in t[0] and '模式' in t[0]:
                        for row in t:
                            province = row.get('省份', '').strip()
                            if province:
                                result['province_configs'][province] = {
                                    'mode': row.get('模式', ''),
                                    'count': row.get('志愿数量', ''),
                                }
            result['province_configs']['_tables'] = tables
            result['province_configs']['_text'] = content

        elif '分批录取' in heading:
            result['batch_strategy'] = {
                'tables': tables,
                'full_text': content,
            }

        elif '稳保策略' in heading:
            result['wenbao_strategy'] = {
                'tables': tables,
                'full_text': content,
            }

        elif '位次转换' in heading:
            result['rank_conversion'] = {
                'tables': tables,
                'full_text': content,
            }

        elif '常见填报陷阱' in heading:
            if tables:
                result['traps'] = tables[0]

        elif '咨询中回答' in heading:
            result['ai_boundary'] = content

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
