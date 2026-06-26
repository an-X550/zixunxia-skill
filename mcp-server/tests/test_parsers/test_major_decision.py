"""Tests for major_decision.py parser."""

from pathlib import Path
from parsers.major_decision import parse


def test_parse_categories(major_decision_md):
    result = parse(major_decision_md.parent.parent)
    cats = result.get('categories', [])
    assert len(cats) == 2
    assert cats[0]['门类'] == '工学'
    assert cats[1]['门类'] == '医学'


def test_parse_majors_count(major_decision_md):
    result = parse(major_decision_md.parent.parent)
    majors = result.get('majors', {})
    assert len(majors) == 2
    assert '软件工程' in majors
    assert '土木工程' in majors


def test_parse_major_fields(major_decision_md):
    result = parse(major_decision_md.parent.parent)
    card = result['majors']['软件工程']
    assert card['培养计划'] == '数据结构、操作系统、软件架构'
    assert card['就业前景'] == '互联网/金融/政务全行业覆盖'
    assert '7分' in card['院校依赖']
    assert card['典型方向'] == '清华：智能软件工程；北邮：通信软件'


def test_parse_naming_traps(major_decision_md):
    result = parse(major_decision_md.parent.parent)
    traps = result.get('naming_traps', [])
    assert len(traps) == 2
    assert traps[0]['专业名称'] == '信息与计算科学'
    assert '数学' in traps[0]['真实门类']


def test_parse_new_majors(major_decision_md):
    result = parse(major_decision_md.parent.parent)
    new_m = result.get('new_majors_2025', [])
    assert len(new_m) == 1
    assert new_m[0]['专业'] == '智能视觉工程'


def test_parse_missing_file(skill_dir):
    result = parse(major_decision_md.parent.parent)
    assert result == {}


def test_parse_empty_file(skill_dir):
    path = skill_dir / "知识库" / "数据层" / "专业决策库.md"
    path.write_text("", encoding='utf-8')
    result = parse(major_decision_md.parent.parent)
    assert isinstance(result, dict)
