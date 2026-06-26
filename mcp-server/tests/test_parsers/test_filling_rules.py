"""Tests for filling_rules.py parser."""

from parsers.filling_rules import parse


def test_parse_province_configs(filling_rules_md):
    result = parse(filling_rules_md.parent.parent)
    configs = result.get('province_configs', {})
    # Should have 浙江, 广东 + internal keys
    assert '浙江' in configs
    assert '广东' in configs


def test_parse_province_mode(filling_rules_md):
    result = parse(filling_rules_md.parent.parent)
    zj = result['province_configs']['浙江']
    assert zj['mode'] == '院校+专业'
    assert '80' in zj['count']


def test_parse_traps(filling_rules_md):
    result = parse(filling_rules_md.parent.parent)
    traps = result.get('traps', [])
    assert len(traps) == 2
    assert traps[0]['陷阱'] == '大类招生'


def test_parse_missing_file(skill_dir):
    result = parse(skill_dir)
    assert result == {}
