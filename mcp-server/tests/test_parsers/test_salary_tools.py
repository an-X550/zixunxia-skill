"""Tests for salary_tools.py parser."""

from parsers.salary_tools import parse


def test_parse_salary_paths(salary_tools_md):
    result = parse(salary_tools_md.parent.parent)
    sources = result.get('salary_paths', {}).get('sources', [])
    assert len(sources) == 2
    assert sources[0]['来源'] == '国家统计局'


def test_parse_framework(salary_tools_md):
    result = parse(salary_tools_md.parent.parent)
    factors = result.get('framework', {}).get('factors', [])
    assert len(factors) == 2
    assert factors[0]['因素'] == '城市资源'


def test_parse_quadrants(salary_tools_md):
    result = parse(salary_tools_md.parent.parent)
    matrix = result.get('quadrants', {}).get('matrix', [])
    assert len(matrix) == 2  # 2 data rows


def test_parse_tools(salary_tools_md):
    result = parse(salary_tools_md.parent.parent)
    for_student = result.get('tools', {}).get('for_student', [])
    assert len(for_student) == 2


def test_parse_bilibili(salary_tools_md):
    result = parse(salary_tools_md.parent.parent)
    videos = result.get('bilibili', {}).get('videos', [])
    assert len(videos) == 2
    assert '工学' in videos[0]['门类'] or 'BV' in videos[0].get('关键B站视频', '')


def test_parse_missing_file(skill_dir):
    result = parse(skill_dir)
    assert result == {}
