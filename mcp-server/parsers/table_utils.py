"""
Markdown 表格解析工具

处理管道分隔的 Markdown 表格，支持：
- 对齐提示行（:--, :--:, --:）
- 多行单元格（表格内换行）
- 中文内容
"""

import re
from typing import List, Dict, Optional


def parse_md_table(text: str) -> List[Dict[str, str]]:
    """
    解析 Markdown 表格为字典列表。

    输入示例：
        | 方向 | 学什么 | 去哪类雇主 |
        |------|--------|-----------|
        | 强电 | 电力系统 | 央企 |
        | 弱电 | 电力电子 | 私企 |

    输出：
        [
            {"方向": "强电", "学什么": "电力系统", "去哪类雇主": "央企"},
            {"方向": "弱电", "学什么": "电力电子", "去哪类雇主": "私企"},
        ]
    """
    lines = text.strip().split('\n')

    # 过滤空行和非表格行
    table_lines = [l for l in lines if l.strip().startswith('|')]

    if len(table_lines) < 2:
        return []

    # 第一行是表头
    headers = _parse_row(table_lines[0])

    # 跳过分隔行（如果存在）
    start = 1
    if _is_separator(table_lines[1]):
        start = 2

    # 解析数据行
    result = []
    for line in table_lines[start:]:
        cells = _parse_row(line)
        if len(cells) == len(headers):
            row = {}
            for h, c in zip(headers, cells):
                row[h] = c.strip()
            result.append(row)
        elif cells:
            # 尝试合并到上一行（多行单元格）
            if result:
                last = result[-1]
                # 将额外内容追加到最后一个字段
                last_key = headers[-1] if len(headers) > 0 else None
                if last_key:
                    last[last_key] += ' ' + ' '.join(cells)

    return result


def _is_separator(line: str) -> bool:
    """判断是否为表格分隔行（如 |------|------|）"""
    return bool(re.match(r'^\|[\s\-:]+\|', line))


def _parse_row(line: str) -> List[str]:
    """解析单行管道分隔的单元格"""
    # 去掉首尾管道符，按 | 分割
    stripped = line.strip()
    if stripped.startswith('|'):
        stripped = stripped[1:]
    if stripped.endswith('|'):
        stripped = stripped[:-1]
    return [c.strip() for c in stripped.split('|')]


def split_by_headings(text: str, level: int = 2) -> Dict[str, str]:
    """
    按指定级别的 Markdown 标题分割文本。

    返回 {标题文本: 标题下的内容} 字典。
    """
    prefix = '#' * level + ' '
    pattern = re.compile(rf'^{prefix}(.+)$', re.MULTILINE)

    # 找到所有标题位置
    matches = list(pattern.finditer(text))

    result = {}
    for i, match in enumerate(matches):
        heading = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        result[heading] = text[start:end].strip()

    return result


def extract_table_section(text: str) -> Optional[str]:
    """
    从文本中提取第一个完整的 Markdown 表格（从 | 开始到连续非 | 行结束）。
    """
    lines = text.split('\n')
    table_start = None
    table_lines = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('|'):
            if table_start is None:
                table_start = i
            table_lines.append(stripped)
        elif table_start is not None:
            # 表格结束
            break

    return '\n'.join(table_lines) if table_lines else None
