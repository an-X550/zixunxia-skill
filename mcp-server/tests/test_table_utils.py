"""Tests for table_utils.py — Markdown table parser and utilities."""

from parsers.table_utils import parse_md_table, split_by_headings


class TestParseMdTable:
    def test_basic_table(self):
        md = """| 名称 | 数量 | 备注 |
|------|------|------|
| 工学 | 277 | 最大 |
| 医学 | 60 | 院校依赖高 |"""
        result = parse_md_table(md)
        assert len(result) == 2
        assert result[0]['名称'] == '工学'
        assert result[0]['数量'] == '277'
        assert result[1]['名称'] == '医学'

    def test_table_with_separator(self):
        md = """| 门类 | 含专业数 | 院校依赖(1-10) | 核心特征 |
|:--|:--|:--|:--|
| 工学 | 277 | 6-9 | 实践性强 |"""
        result = parse_md_table(md)
        assert len(result) == 1
        assert result[0]['门类'] == '工学'

    def test_empty_input(self):
        result = parse_md_table("")
        assert result == []

    def test_single_column(self):
        md = """| 名称 |
|------|
| 工学 |
| 医学 |"""
        result = parse_md_table(md)
        assert len(result) == 2
        assert result[0]['名称'] == '工学'

    def test_bold_cells(self):
        md = """| 字段 | 内容 |
|------|------|
| **院校依赖** | **7分**。说明文字 |
| 报考条件 | 物理必选 |"""
        result = parse_md_table(md)
        assert '院校依赖' in result[0]['字段'].strip('*')
        assert '7分' in result[1]['内容']


class TestSplitByHeadings:
    def test_split_h2(self):
        text = """# 标题
intro text
## 章节一
content one
more content
## 章节二
content two"""
        sections = split_by_headings(text, level=2)
        assert '章节一' in sections
        assert '章节二' in sections
        assert 'content one\nmore content' in sections['章节一']

    def test_single_heading(self):
        text = "## 唯一章节\n只有一段内容"
        sections = split_by_headings(text, level=2)
        assert len(sections) == 1
        assert '唯一章节' in sections

    def test_no_headings(self):
        text = "没有标题的纯文本"
        sections = split_by_headings(text, level=2)
        assert len(sections) == 0
