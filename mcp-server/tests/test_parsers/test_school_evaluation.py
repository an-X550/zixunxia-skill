"""Tests for school_evaluation.py parser."""

from parsers.school_evaluation import parse


def test_parse_school_lists(school_evaluation_md):
    result = parse(school_evaluation_md.parent.parent)
    lists = result.get('lists', {})
    assert '985' in lists
    assert len(lists['985']) == 3  # 北大、清华、浙大
    assert '北大' in lists['985']
    assert '北邮' in lists.get('211', [])


def test_parse_ministries(school_evaluation_md):
    result = parse(school_evaluation_md.parent.parent)
    ministries = result.get('ministries', [])
    assert len(ministries) == 2
    assert ministries[0]['部委系统'] == '电子工业部'
    assert '成电' in ministries[0]['代表院校']


def test_parse_ministry_majors(school_evaluation_md):
    result = parse(school_evaluation_md.parent.parent)
    m = result['ministries'][0]
    assert '电子信息' in m['强势专业']
    assert '计算机' in m['强势专业']


def test_parse_tiers(school_evaluation_md):
    result = parse(school_evaluation_md.parent.parent)
    tiers = result.get('tiers', {})
    assert 'labels' in tiers


def test_parse_missing_file(skill_dir):
    result = parse(skill_dir)
    assert result == {}
