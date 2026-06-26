"""Tests for city_industry.py parser."""

from parsers.city_industry import parse


def test_parse_provinces(city_industry_md):
    result = parse(city_industry_md.parent.parent)
    provinces = result.get('provinces', {})
    assert '浙江' in provinces
    assert '江苏' in provinces


def test_parse_province_data(city_industry_md):
    result = parse(city_industry_md.parent.parent)
    zj = result['provinces']['浙江']
    assert len(zj['clusters']) > 0
    assert zj['advantages'] == '纺织、机械'
    assert zj['future_focus'] == '先进制造'


def test_parse_city_tiers(city_industry_md):
    result = parse(city_industry_md.parent.parent)
    tiers = result.get('city_tiers', [])
    assert len(tiers) == 2


def test_parse_city_types(city_industry_md):
    result = parse(city_industry_md.parent.parent)
    types = result.get('city_types', [])
    assert len(types) == 1
    assert types[0]['类型'] == '科技创新型'


def test_parse_major_city_match(city_industry_md):
    result = parse(city_industry_md.parent.parent)
    matches = result.get('major_city_match', [])
    assert len(matches) == 2
    assert matches[0]['专业方向'] == '计算机/AI'


def test_parse_missing_file(skill_dir):
    result = parse(skill_dir)
    assert result == {}
