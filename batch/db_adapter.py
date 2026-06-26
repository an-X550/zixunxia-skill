"""Thin wrapper around mcp-server/db_queries.py.

Each function opens a fresh read-only SQLite connection, calls the
corresponding db_queries function, and closes the connection.

This avoids MCP subprocess overhead in batch mode - the query functions
in db_queries.py are pure Python that accept sqlite3.Connection.
"""

import sqlite3
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

# Import batch config BEFORE injecting mcp-server into sys.path
# (mcp-server has its own config.py which would shadow batch/config.py)
from config import DB_PATH, SQLITE_CONNECTION_TIMEOUT

# Inject mcp-server into path so we can import db_queries directly
_MCP_SERVER = Path(__file__).resolve().parent.parent / "mcp-server"
if str(_MCP_SERVER) not in sys.path:
    sys.path.insert(0, str(_MCP_SERVER))

import db_queries


def _get_conn() -> sqlite3.Connection:
    """Open a read-only SQLite connection with WAL mode."""
    conn = sqlite3.connect(str(DB_PATH), timeout=SQLITE_CONNECTION_TIMEOUT)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    return conn


# ── Major queries ────────────────────────────────────────

def query_major_detail(major_name: str) -> Optional[Dict[str, Any]]:
    """Exact match for a major card. Returns card dict or None."""
    conn = _get_conn()
    try:
        return db_queries.get_major_card(conn, major_name)
    finally:
        conn.close()


def fuzzy_match_major(name: str, limit: int = 10) -> List[str]:
    """Fuzzy match major names."""
    conn = _get_conn()
    try:
        return db_queries.fuzzy_match_major(conn, name, limit)
    finally:
        conn.close()


def query_major_branches(major_name: str) -> Optional[List[Dict]]:
    """Get all internal branches for a major."""
    conn = _get_conn()
    try:
        return db_queries.get_major_branches(conn, major_name)
    finally:
        conn.close()


def search_majors(
    keyword: Optional[str] = None,
    dep_max: Optional[int] = None,
    further_study_required: bool = False,
) -> List[Dict[str, Any]]:
    """Search/filter majors."""
    conn = _get_conn()
    try:
        return db_queries.search_majors_filtered(
            conn, keyword=keyword, dep_max=dep_max,
            further_study_skip=further_study_required,
        )
    finally:
        conn.close()


def get_categories() -> List[Dict[str, str]]:
    """Get all 12 major categories."""
    conn = _get_conn()
    try:
        return db_queries.get_categories(conn)
    finally:
        conn.close()


def get_city_tiers() -> List[Dict]:
    """Get all city tiers ordered by level."""
    conn = _get_conn()
    try:
        return db_queries.get_city_tiers(conn)
    finally:
        conn.close()


def get_city_types() -> List[Dict]:
    """Get all city industry types."""
    conn = _get_conn()
    try:
        return db_queries.get_city_types(conn)
    finally:
        conn.close()


def get_major_city_match() -> List[Dict]:
    """Get all major-to-city matching rules."""
    conn = _get_conn()
    try:
        return db_queries.get_major_city_match(conn)
    finally:
        conn.close()


def query_province_config(province: str) -> Optional[Dict]:
    """Get gaokao filling config for a province."""
    conn = _get_conn()
    try:
        return db_queries.get_province_filling_config(conn, province)
    finally:
        conn.close()


def query_career_data(query_type: str) -> Optional[Any]:
    """Get salary/employment framework/tools data."""
    conn = _get_conn()
    try:
        return db_queries.get_salary_data(conn, query_type)
    finally:
        conn.close()


# ── School-by-Major (reverse lookup) ─────────────────────

def query_school_by_major(
    major_name: str, min_tier: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Find schools strong in a given major. Cross-table SQL join."""
    conn = _get_conn()
    try:
        tier_map = {"985": "is_985 = 1", "211": "is_211 = 1", "双一流": "is_double_first_class = 1"}
        tier_clause = tier_map.get(min_tier, "1=1") if min_tier else "1=1"

        results: List[Dict] = []
        for row in conn.execute(
            f"""SELECT sms.school_name, sms.major_name, sms.direction_note, sms.source,
                       s.is_985, s.is_211, s.is_double_first_class, s.dfc_tier
                FROM school_major_strength sms
                LEFT JOIN schools s ON s.name = sms.school_name
                WHERE sms.major_name LIKE ? AND ({tier_clause})
                ORDER BY s.is_985 DESC, s.is_211 DESC, s.is_double_first_class DESC""",
            (f"%{major_name}%",),
        ).fetchall():
            row_d = dict(row)
            tier_parts = []
            if row_d["is_985"]: tier_parts.append("985")
            if row_d["is_211"]: tier_parts.append("211")
            if row_d["is_double_first_class"]: tier_parts.append(f"双一流{row_d['dfc_tier'] or ''}")
            results.append({
                "school": row_d["school_name"], "tier": "/".join(tier_parts) or "其他",
                "major": row_d["major_name"], "direction": row_d["direction_note"] or "",
                "source": row_d["source"] or "",
            })

        # Supplement from ministry_affiliations
        for row in conn.execute(
            f"""SELECT ma.school_name, ma.strength_majors, ma.ministry_system,
                       s.is_985, s.is_211, s.is_double_first_class, s.dfc_tier
                FROM ministry_affiliations ma
                LEFT JOIN schools s ON s.name = ma.school_name
                WHERE ma.strength_majors LIKE ? AND ({tier_clause})""",
            (f"%{major_name}%",),
        ).fetchall():
            row_d = dict(row)
            if not any(r["school"] == row_d["school_name"] for r in results):
                tier_parts = []
                if row_d["is_985"]: tier_parts.append("985")
                if row_d["is_211"]: tier_parts.append("211")
                if row_d["is_double_first_class"]: tier_parts.append(f"双一流{row_d['dfc_tier'] or ''}")
                results.append({
                    "school": row_d["school_name"], "tier": "/".join(tier_parts) or "其他",
                    "major": major_name, "direction": row_d["strength_majors"] or "",
                    "source": f"ministry:{row_d['ministry_system']}",
                })

        if not results:
            return {"major": major_name, "results": [], "count": 0, "hint": "未找到匹配院校"}
        return {"major": major_name, "results": results, "count": len(results), "tier_filter": min_tier or "全部"}
    finally:
        conn.close()


def query_major_by_school(school_name: str) -> Optional[Dict[str, Any]]:
    """Find strong majors at a given school."""
    conn = _get_conn()
    try:
        srow = conn.execute(
            "SELECT name, is_985, is_211, is_double_first_class, dfc_tier FROM schools WHERE name LIKE ?",
            (f"%{school_name}%",),
        ).fetchone()
        results: List[Dict] = []
        for row in conn.execute(
            "SELECT school_name, major_name, direction_note, source FROM school_major_strength WHERE school_name LIKE ?",
            (f"%{school_name}%",),
        ).fetchall():
            results.append({"major": row["major_name"], "direction": row["direction_note"] or "", "source": row["source"] or ""})
        for row in conn.execute(
            "SELECT school_name, strength_majors, ministry_system FROM ministry_affiliations WHERE school_name LIKE ?",
            (f"%{school_name}%",),
        ).fetchall():
            for m in (row["strength_majors"] or "").split("/"):
                m = m.strip()
                if m and not any(r["major"] == m for r in results):
                    results.append({"major": m, "direction": row["ministry_system"] or "", "source": "ministry_affiliation"})

        tier_label = ""
        if srow:
            if srow["is_985"]: tier_label = "985"
            elif srow["is_211"]: tier_label = "211"
            elif srow["is_double_first_class"]: tier_label = f"双一流{srow['dfc_tier'] or ''}"
        return {"school": school_name, "tier": tier_label or "未知", "results": results, "count": len(results)}
    finally:
        conn.close()


# ── City Industry (combined search) ───────────────────────

def query_city_industry(name: str) -> Optional[Dict[str, Any]]:
    """Search province industry, city tier, or city type by name."""
    conn = _get_conn()
    try:
        # Try province first
        result = db_queries.get_province_industry(conn, name)
        if result:
            return {"type": "province", "data": dict(result)}
        # Try city tier
        result = db_queries.search_in_city_tier(conn, name)
        if result:
            return {"type": "city_tier", "data": dict(result)}
        # Try city type
        result = db_queries.search_in_city_type(conn, name)
        if result:
            return {"type": "city_type", "data": dict(result)}
        return None
    finally:
        conn.close()
