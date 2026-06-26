"""
诊断脚本：验证 stdout 编码和 JSON 中文+emoji 往返

用法：python encoding_check.py
"""

import sys
import json


def check():
    print(f"Platform: {sys.platform}")
    print(f"stdout encoding: {sys.stdout.encoding}")
    print(f"Python version: {sys.version}")

    test_data = {
        "测试": "电气工程及其自动化",
        "院校": "成电 / 西电 / 杭电",
        "emoji_ok": "OK",
        "unicode": "✅ ❌ ⚠️"
    }

    try:
        encoded = json.dumps(test_data, ensure_ascii=False)
        roundtrip = json.loads(encoded)
        assert roundtrip == test_data, f"Round-trip mismatch"
        print(f"\nOK: JSON round-trip successful ({len(encoded)} chars)")
    except Exception as e:
        print(f"\nFAIL: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(check())
