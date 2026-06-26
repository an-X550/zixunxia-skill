"""
解析 知识库/数据层/院校评估库.md

结构：5 个 H2 章节。
- 一、院校分层体系 → 标签表 + 院校名单(逗号分隔) + 推免率表
- 二、7维评估框架 → 散文（保留原文）
- 三、部委直属院校速查 → 部委-院校-专业表
- 四、院校-专业匹配逻辑 → 散文+表格
- 五、咨询中院校维度输出原则 → 散文
"""

from pathlib import Path
from typing import Dict, List, Any
import re

from .table_utils import parse_md_table


def parse(skill_dir: Path) -> Dict[str, Any]:
    filepath = skill_dir / "知识库" / "数据层" / "院校评估库.md"
    if not filepath.exists():
        return {}

    text = filepath.read_text(encoding='utf-8')
    sections = _split_by_h2(text)

    result = {
        'tiers': {},
        'lists': {},
        'ministries': [],
        'evaluation_framework': '',
        'tuimian_rates': [],
        'matching_logic': '',
        'output_principles': '',
    }

    # 一、院校分层体系
    if '一、院校分层体系' in sections:
        sec = sections['一、院校分层体系']
        tables = _extract_tables(sec)
        if tables:
            result['tiers'] = {'labels': tables[0]}
        # 提取名单
        result['lists']['985'] = _extract_school_list(sec, '985高校名单')
        result['lists']['211'] = _extract_school_list(sec, '纯211名单')
        result['lists']['double_first_a'] = _extract_school_list(sec, '一流大学A类')
        result['lists']['double_first_b'] = _extract_school_list(sec, '一流大学B类')

    # 二、7维院校评估框架 — 保留全文
    if '二、7维院校评估框架' in sections:
        result['evaluation_framework'] = sections['二、7维院校评估框架']

    # 三、部委直属院校速查
    if '三、部委直属院校速查' in sections:
        sec = sections['三、部委直属院校速查']
        tables = _extract_tables(sec)
        if tables:
            result['ministries'] = tables[0]

    # 四、院校-专业匹配逻辑
    if '四、院校-专业匹配逻辑' in sections:
        sec = sections['四、院校-专业匹配逻辑']
        tables = _extract_tables(sec)
        if tables:
            result['tuimian_rates'] = tables[0]
        result['matching_logic'] = sec

    # 五、咨询中院校维度输出原则
    if '五、咨询中院校维度输出原则' in sections:
        result['output_principles'] = sections['五、咨询中院校维度输出原则']

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


def _extract_school_list(text: str, keyword: str) -> List[str]:
    """从文本中提取逗号/顿号分隔的院校名单"""
    lines = text.split('\n')
    start = -1
    for i, line in enumerate(lines):
        if keyword in line:
            start = i
            break
    if start < 0:
        return []

    all_names = []

    # 先检查关键词所在行本身是否有内容（如 "**一流大学A类（36所）**：北大、人大..."）
    keyword_line = lines[start].strip()
    # 移除标签部分，看是否还剩内容
    after_label = re.sub(r'\*\*[^*]+\*\*[：:]?\s*', '', keyword_line)
    after_label = re.sub(r'^###\s+\d+\.\d+\s*', '', after_label)  # 移除 H3 标题前缀
    if after_label and len(after_label) > 5:
        all_names.append(after_label)

    # 如果关键词行已有内容且下一行是新标签，直接结束
    if after_label and len(after_label) > 5:
        next_i = start + 1
        while next_i < len(lines) and not lines[next_i].strip():
            next_i += 1
        if next_i < len(lines):
            next_line = lines[next_i].strip()
            if next_line.startswith('**') and '：' in next_line:
                # 下一个就是另一个类别，只取当前行
                pass
            elif not next_line.startswith('#'):
                # 下一个是内容行，继续收集
                pass
            else:
                pass

    # 收集后续行
    i = start + 1
    while i < len(lines) and not lines[i].strip():
        i += 1

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            break
        if line.startswith('#') or line.startswith('>'):
            break
        if line.startswith('**') and '：' in line:
            # 遇到下一个标签——如果当前已有收集到内容，停止
            if all_names:
                break
            # 否则，提取该标签后的内容，然后继续（可能是长名单跨多行）
            label_content = re.sub(r'\*\*[^*]+\*\*[：:]?\s*', '', line)
            if label_content.strip():
                all_names.append(label_content)
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            continue
        line = re.sub(r'\*\*[^*]+\*\*[：:]?\s*', '', line)
        if line.strip():
            all_names.append(line)
        i += 1

    full = ' '.join(all_names)
    full = re.sub(r'\([^)]*\)', '', full)
    names = re.split(r'[、，,]', full)
    result = [n.strip() for n in names if n.strip() and len(n.strip()) >= 2]
    seen = set()
    unique = []
    for n in result:
        if n not in seen:
            seen.add(n)
            unique.append(n)
    return unique

    full = ' '.join(names_text)
    # 移除括号注释
    full = re.sub(r'\([^)]*\)', '', full)
    # 按中文顿号、逗号、英文逗号分割
    names = re.split(r'[、，,]', full)
    result = [n.strip() for n in names if n.strip() and len(n.strip()) >= 2]
    # 去重保持顺序
    seen = set()
    unique = []
    for n in result:
        if n not in seen:
            seen.add(n)
            unique.append(n)
    return unique
