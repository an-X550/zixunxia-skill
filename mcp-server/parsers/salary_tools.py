"""
解析 知识库/数据层/行业薪资与工具箱.md

结构：9 个 H2 章节，大部分为 Markdown 表格。
支持 query_type: salary_paths | framework | tools | quadrants | bilibili | trends | quake
"""

from pathlib import Path
from typing import Dict, List, Any

from .table_utils import parse_md_table


def parse(skill_dir: Path) -> Dict[str, Any]:
    """解析薪资与工具箱文件，返回按 query_type 索引的数据字典"""
    filepath = skill_dir / "知识库" / "数据层" / "行业薪资与工具箱.md"
    if not filepath.exists():
        return {}

    text = filepath.read_text(encoding='utf-8')
    result = {}

    # 分割为各章
    sections = _split_by_h2(text)

    # 一、薪资查询路径
    if '一、薪资查询路径' in sections:
        tables = _extract_all_tables(sections['一、薪资查询路径'])
        if tables:
            result['salary_paths'] = {
                'sources': tables[0],  # 权威数据源表
                'notes': _extract_bullet_points(sections['一、薪资查询路径'], '注意事项'),
            }

    # 二、6因素就业分析框架
    if '二、6因素就业分析框架' in sections:
        tables = _extract_all_tables(sections['二、6因素就业分析框架'])
        if tables:
            result['framework'] = {'factors': tables[0]}

    # 三、就业四象限
    if '三、就业四象限' in sections:
        tables = _extract_all_tables(sections['三、就业四象限'])
        if tables:
            result['quadrants'] = {'matrix': tables[0]}

    # 四、工具速查表
    if '四、工具速查表' in sections:
        tables = _extract_all_tables(sections['四、工具速查表'])
        result['tools'] = {
            'for_student': tables[0] if len(tables) > 0 else [],
            'for_consultant': tables[1] if len(tables) > 1 else [],
        }

    # 六、行业趋势判断框架
    if '六、行业趋势判断框架' in sections:
        tables = _extract_all_tables(sections['六、行业趋势判断框架'])
        if tables:
            result['trends'] = {
                'three_look': tables[0],
                'signals': _extract_bullet_points(sections['六、行业趋势判断框架'], '信号'),
            }

    # 七、夸克APP操作流程
    if '七、夸克APP操作流程' in sections:
        tables = _extract_all_tables(sections['七、夸克APP操作流程'])
        if tables:
            result['quake'] = {'operations': tables[0]}

    # 八、B站资源速查
    if '八、B站专业解读资源速查' in sections:
        tables = _extract_all_tables(sections['八、B站专业解读资源速查'])
        if tables:
            result['bilibili'] = {'videos': tables[0]}

    # 九、咨询侠答疑工具箱
    if '九、咨询侠答疑工具箱速查' in sections:
        tables = _extract_all_tables(sections['九、咨询侠答疑工具箱速查'])
        if tables:
            result['toolbox'] = {'qa_tools': tables[0]}

    return result


def _split_by_h2(text: str) -> Dict[str, str]:
    """按 ## 标题分割文本"""
    import re
    sections = {}
    pattern = re.compile(r'^## (.+)$', re.MULTILINE)
    matches = list(pattern.finditer(text))

    for i, m in enumerate(matches):
        heading = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[heading] = text[start:end].strip()

    return sections


def _extract_all_tables(text: str) -> List[List[Dict[str, str]]]:
    """提取文本中所有 Markdown 表格"""
    tables = []
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith('|'):
            # 从当前位置开始收集表格
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i].strip())
                i += 1
            if len(table_lines) >= 2:
                table_text = '\n'.join(table_lines)
                parsed = parse_md_table(table_text)
                if parsed:
                    tables.append(parsed)
        else:
            i += 1
    return tables


def _extract_bullet_points(text: str, keyword: str = '') -> List[str]:
    """提取章节中的 bullet point 列表"""
    import re
    # 找到关键词所在区域
    if keyword:
        pattern = re.compile(rf'### .*{keyword}.*\n(.*?)(?=###|\Z)', re.DOTALL)
        match = pattern.search(text)
        if match:
            area = match.group(1)
        else:
            area = text
    else:
        area = text

    bullets = []
    for line in area.split('\n'):
        stripped = line.strip()
        if stripped.startswith('- **') or stripped.startswith('- '):
            bullets.append(stripped.lstrip('- ').strip())
    return bullets
