"""Tests for major_branches.py parser."""

from parsers.major_branches import parse


def test_parse_branches_structure(major_branches_md):
    result = parse(major_branches_md.parent.parent)
    assert isinstance(result, dict)
    assert '自动化' in result
    assert '土木工程' in result


def test_parse_branch_count(major_branches_md):
    result = parse(major_branches_md.parent.parent)
    auto_branches = result['自动化']
    assert len(auto_branches) == 2


def test_parse_branch_columns(major_branches_md):
    result = parse(major_branches_md.parent.parent)
    branch = result['自动化'][0]
    assert '方向' in branch
    assert '学什么' in branch
    assert '去哪类雇主' in branch
    assert '典型路径' in branch
    assert '选校注意' in branch


def test_parse_missing_file(skill_dir):
    result = parse(skill_dir)
    assert result == {}
