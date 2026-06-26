"""
首次启动依赖检查 — 咨询侠 v2.5.0 MCP Server

用法：python check_deps.py
退出码：0=全OK, 1=有警告, 2=有错误
"""

import sys
import os
import sqlite3
from pathlib import Path


def check(label: str, fn) -> tuple:
    """Run a check, return (label, status_message, is_ok)."""
    try:
        result = fn()
        return (label, result, True)
    except Exception as e:
        return (label, f"ERROR: {e}", False)


def main():
    skill_dir = Path(os.environ.get(
        "ZIXUNXIA_SKILL_DIR",
        Path(__file__).parent.parent
    )).resolve()
    db_path = Path(os.environ.get(
        "ZIXUNXIA_DB_PATH",
        skill_dir / "撑伞侠知识库.db"
    ))
    cache_path = Path(__file__).parent / "cache" / "parsed_data.json"

    checks = []
    errors = 0

    # 1. Python version
    ver = sys.version_info
    ok = ver >= (3, 10)
    checks.append(("Python >= 3.10",
                   f"OK: Python {ver.major}.{ver.minor}.{ver.micro}" if ok
                   else f"FAIL: Python {ver.major}.{ver.minor}.{ver.micro} < 3.10",
                   ok))
    if not ok:
        errors += 1

    # 2. mcp SDK
    try:
        import mcp
        mcp_ver = getattr(mcp, '__version__', 'unknown')
        checks.append(("mcp SDK", f"OK: mcp {mcp_ver}", True))
    except ImportError:
        checks.append(("mcp SDK", "MISSING: pip install mcp>=1.0.0", False))
        errors += 1

    # 3. SQLite DB
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            tables = cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_count = len(tables)
            row_count = 0
            for t in tables:
                try:
                    row_count += cursor.execute(
                        f"SELECT COUNT(*) FROM [{t[0]}]"
                    ).fetchone()[0]
                except Exception:
                    pass
            conn.close()
            size_kb = db_path.stat().st_size / 1024
            checks.append(("SQLite DB",
                           f"OK: {table_count} tables, {row_count} rows, {size_kb:.0f}KB",
                           True))
        except Exception as e:
            checks.append(("SQLite DB",
                           f"WARN: DB exists but query failed: {e}", True))
    else:
        checks.append(("SQLite DB",
                       f"WARN: {db_path.name} not found. "
                       "8 old MCP tools work via cache. "
                       "Run build_sqlite.py for full 10-tool support.",
                       True))

    # 4. Parsed data cache
    if cache_path.exists():
        try:
            data = json.loads(cache_path.read_text(encoding='utf-8'))
            majors = len(data.get('majors', {}))
            branches = len(data.get('major_branches', {}))
            categories = len(data.get('categories', []))
            checks.append(("Parsed cache",
                           f"OK: {majors} majors, {branches} branches, "
                           f"{categories} categories",
                           True))
        except Exception as e:
            checks.append(("Parsed cache",
                           f"WARN: cache exists but corrupt: {e}", True))
    else:
        checks.append(("Parsed cache",
                       "WARN: No parsed_data.json. "
                       "Will be created on first MCP server start.",
                       True))

    # 5. Windows encoding
    if sys.platform == 'win32':
        encoding_ok = (sys.stdout.encoding or '').lower() in ('utf-8', 'utf8')
        checks.append(("Windows encoding",
                       f"{'OK' if encoding_ok else 'WARN'}: "
                       f"stdout={sys.stdout.encoding}",
                       encoding_ok))

    # 6. Markdown source files
    data_dir = skill_dir / "知识库" / "数据层"
    md_files = ["专业决策库.md", "专业内部分叉速查.md", "城市产业库.md",
                "填报规则库.md", "院校评估库.md", "行业薪资与工具箱.md"]
    missing = [f for f in md_files if not (data_dir / f).exists()]
    if missing:
        checks.append(("Markdown sources",
                       f"ERROR: Missing: {', '.join(missing)}", False))
        errors += len(missing)
    else:
        total_kb = sum((data_dir / f).stat().st_size for f in md_files) / 1024
        checks.append(("Markdown sources",
                       f"OK: {len(md_files)} files, {total_kb:.0f}KB", True))

    # 7. python-docx (optional)
    try:
        import docx
        checks.append(("python-docx", "OK: docx available", True))
    except ImportError:
        checks.append(("python-docx",
                       "WARN: not installed. DOCX export disabled. "
                       "pip install python-docx", True))

    # --- Print report ---
    print()
    print("=" * 60)
    print("  咨询侠 v2.5.0 — Dependency Check")
    print("=" * 60)
    for label, msg, ok in checks:
        icon = "[OK]" if ok else "[!!]"
        print(f"  {icon} {label}")
        print(f"       {msg}")
    print("=" * 60)

    if errors > 0:
        print(f"\n  {errors} error(s) found.")
        return 2

    warnings = sum(1 for _, msg, _ in checks if msg.startswith("WARN"))
    if warnings > 0:
        print(f"\n  {warnings} warning(s) — MCP server can still start.")
        return 1

    print("\n  All checks passed. MCP Server is ready.")
    return 0


if __name__ == "__main__":
    import json
    sys.exit(main())
