"""
Centralized SQLite query functions for all 10 MCP tools.

Design:
- One function per conceptual query (tools may call multiple)
- All accept sqlite3.Connection + parameters
- Return dict/list ready for JSON serialization
- No MCP types — pure data layer
"""

import re
import sqlite3
from typing import Optional, List, Dict, Any


# ── Major Cards ──────────────────────────────────────────

def get_major_card(db: sqlite3.Connection, major_name: str) -> Optional[Dict[str, Any]]:
    """Exact match for a major card by name."""
    row = db.execute(
        """SELECT name, category, subcategory, training_plan, employment_outlook,
                  further_study, admission_req, school_dependency,
                  school_dependency_detail, typical_directions
           FROM major_cards WHERE name = ?""",
        (major_name,)
    ).fetchone()
    if not row:
        return None
    return dict(row)


def fuzzy_match_major(db: sqlite3.Connection, name: str, limit: int = 10) -> List[str]:
    """Fuzzy match major names."""
    rows = db.execute(
        "SELECT name FROM major_cards WHERE name LIKE ? LIMIT ?",
        (f"%{name}%", limit)
    ).fetchall()
    return [r['name'] for r in rows]


# ── Major Branches ───────────────────────────────────────

def get_major_branches(db: sqlite3.Connection, major_name: str) -> Optional[List[Dict]]:
    """Get all branches for a major."""
    rows = db.execute(
        """SELECT branch_name, curriculum, employers, career_path, school_notes
           FROM major_branches WHERE major_name = ?""",
        (major_name,)
    ).fetchall()
    if not rows:
        return None
    return [dict(r) for r in rows]


def fuzzy_match_branch_major(db: sqlite3.Connection, name: str) -> List[str]:
    """Fuzzy match branch major names."""
    rows = db.execute(
        "SELECT DISTINCT major_name FROM major_branches WHERE major_name LIKE ?",
        (f"%{name}%",)
    ).fetchall()
    return [r['major_name'] for r in rows]


# ── Major Search ─────────────────────────────────────────

def search_majors_filtered(
    db: sqlite3.Connection,
    keyword: Optional[str] = None,
    dep_max: Optional[int] = None,
    further_study_skip: bool = False,
) -> List[Dict[str, Any]]:
    """Search/filter majors with optional filters."""
    query = """SELECT name, school_dependency, further_study, employment_outlook
               FROM major_cards WHERE 1=1"""
    params: list = []

    if keyword:
        query += " AND name LIKE ?"
        params.append(f"%{keyword}%")
    if further_study_skip:
        query += " AND further_study NOT LIKE ? AND further_study NOT LIKE ?"
        params.extend(["%本科可%", "%本科就%"])

    rows = db.execute(query, params).fetchall()
    results = []
    for row in rows:
        dep_val = _parse_dep_val(row['school_dependency'])
        if dep_max is not None and dep_val > dep_max:
            continue
        results.append({
            "name": row['name'],
            "院校依赖": (row['school_dependency'] or '')[:50],
            "深造需求": (row['further_study'] or '')[:80],
            "就业前景": (row['employment_outlook'] or '')[:80],
        })
    return results


def get_categories(db: sqlite3.Connection) -> List[Dict[str, str]]:
    """Get all major categories."""
    rows = db.execute(
        "SELECT name, major_count, school_dependency, core_features FROM major_categories"
    ).fetchall()
    return [dict(r) for r in rows]


# ── City Industry ───────────────────────────────────────

def get_province_industry(db: sqlite3.Connection, province_name: str) -> Optional[Dict]:
    """Exact match for province industry data."""
    row = db.execute(
        """SELECT province_name, clusters, advantage_industries, future_focus
           FROM province_industries WHERE province_name = ?""",
        (province_name,)
    ).fetchone()
    if not row:
        return None
    return dict(row)


def fuzzy_match_province(db: sqlite3.Connection, name: str) -> List[str]:
    """Fuzzy match province names."""
    rows = db.execute(
        "SELECT province_name FROM province_industries WHERE province_name LIKE ? LIMIT 5",
        (f"%{name}%",)
    ).fetchall()
    return [r['province_name'] for r in rows]


def get_city_tiers(db: sqlite3.Connection) -> List[Dict]:
    """Get all city tiers."""
    rows = db.execute(
        """SELECT tier_level, tier_name, features, representative_cities
           FROM city_tiers ORDER BY tier_level"""
    ).fetchall()
    return [dict(r) for r in rows]


def get_city_types(db: sqlite3.Connection) -> List[Dict]:
    """Get all city types."""
    rows = db.execute(
        "SELECT type_name, features, typical_cities FROM city_types"
    ).fetchall()
    return [dict(r) for r in rows]


def search_in_city_tier(db: sqlite3.Connection, city_name: str) -> Optional[Dict]:
    """Search for a city in tier representative_cities field."""
    rows = db.execute(
        """SELECT tier_level, tier_name, features, representative_cities
           FROM city_tiers WHERE representative_cities LIKE ?""",
        (f"%{city_name}%",)
    ).fetchall()
    return dict(rows[0]) if rows else None


def search_in_city_type(db: sqlite3.Connection, city_name: str) -> Optional[Dict]:
    """Search for a city in type typical_cities field."""
    rows = db.execute(
        """SELECT type_name, features, typical_cities
           FROM city_types WHERE typical_cities LIKE ?""",
        (f"%{city_name}%",)
    ).fetchall()
    return dict(rows[0]) if rows else None


def get_major_city_match(db: sqlite3.Connection) -> List[Dict]:
    """Get all major-city matching rules."""
    rows = db.execute(
        "SELECT major_direction, preferred_city_feature, representative_cities FROM major_city_match"
    ).fetchall()
    return [dict(r) for r in rows]


# ── School Info ──────────────────────────────────────────

def get_school_lists(db: sqlite3.Connection) -> Dict[str, List[str]]:
    """Get school tier lists from schools table."""
    return {
        "985": [r['name'] for r in db.execute(
            "SELECT name FROM schools WHERE is_985=1").fetchall()],
        "211": [r['name'] for r in db.execute(
            "SELECT name FROM schools WHERE is_211=1 AND is_985=0").fetchall()],
        "double_first_a": [r['name'] for r in db.execute(
            "SELECT name FROM schools WHERE is_double_first_class=1 AND dfc_tier='A'").fetchall()],
        "double_first_b": [r['name'] for r in db.execute(
            "SELECT name FROM schools WHERE is_double_first_class=1 AND dfc_tier='B'").fetchall()],
    }


def get_ministries(db: sqlite3.Connection, ministry_filter: Optional[str] = None) -> List[Dict]:
    """Get ministry affiliations, optionally filtered."""
    if ministry_filter:
        rows = db.execute(
            """SELECT ministry_system, school_name, strength_majors
               FROM ministry_affiliations WHERE ministry_system LIKE ?""",
            (f"%{ministry_filter}%",)
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT ministry_system, school_name, strength_majors FROM ministry_affiliations"
        ).fetchall()
    return [dict(r) for r in rows]


# ── Filling Rules ───────────────────────────────────────

def get_province_filling_config(db: sqlite3.Connection, province: str) -> Optional[Dict]:
    """Get filling config for a province."""
    row = db.execute(
        """SELECT province_name, filling_mode, max_choices, has_tiaji_risk
           FROM province_filling_config WHERE province_name = ?""",
        (province,)
    ).fetchone()
    if not row:
        return None
    return dict(row)


def fuzzy_match_province_config(db: sqlite3.Connection, name: str) -> List[str]:
    """Fuzzy match province names in filling config."""
    rows = db.execute(
        "SELECT province_name FROM province_filling_config WHERE province_name LIKE ?",
        (f"%{name}%",)
    ).fetchall()
    return [r['province_name'] for r in rows]


def get_all_provinces_config(db: sqlite3.Connection) -> List[Dict]:
    """Get all province filling configs."""
    rows = db.execute(
        "SELECT province_name, filling_mode, max_choices, has_tiaji_risk FROM province_filling_config"
    ).fetchall()
    return [dict(r) for r in rows]


def get_filling_traps(db: sqlite3.Connection) -> List[Dict]:
    """Get all filling traps."""
    rows = db.execute("SELECT trap_name, description FROM filling_traps").fetchall()
    return [dict(r) for r in rows]


# ── Career / Salary ──────────────────────────────────────

def get_salary_data(db: sqlite3.Connection, query_type: str) -> Optional[Any]:
    """Map salary query types to SQLite tables."""
    if query_type == "salary_paths":
        rows = db.execute(
            "SELECT source_name, content, query_method FROM salary_sources"
        ).fetchall()
        return [dict(r) for r in rows]
    elif query_type == "framework":
        rows = db.execute(
            "SELECT factor_name, description FROM employment_factors"
        ).fetchall()
        return [dict(r) for r in rows]
    elif query_type in ("tools", "toolbox"):
        audience = "学生" if query_type == "tools" else "咨询侠"
        rows = db.execute(
            "SELECT purpose, tool_name, operation FROM tool_references WHERE audience=?",
            (audience,)
        ).fetchall()
        return [dict(r) for r in rows]
    elif query_type == "bilibili":
        rows = db.execute(
            "SELECT category, video_info, bv_number FROM bilibili_resources"
        ).fetchall()
        return [dict(r) for r in rows]
    # For types not stored in SQLite, return None (caller falls back to DataStore)
    return None


def get_available_salary_types() -> List[str]:
    """List salary query types available in SQLite."""
    return ["salary_paths", "framework", "tools", "toolbox", "bilibili"]


# ── Full-Text Search ─────────────────────────────────────

def search_all(db: sqlite3.Connection, query: str, scope: str = "all") -> List[Dict]:
    """Cross-table keyword search, returns max 20 results."""
    results: List[Dict] = []

    if scope in ("all", "majors"):
        for row in db.execute(
            "SELECT name FROM major_cards WHERE name LIKE ? LIMIT 10",
            (f"%{query}%",)
        ).fetchall():
            results.append({"source": "major_cards", "type": "major", "name": row['name']})
        for row in db.execute(
            "SELECT DISTINCT major_name FROM major_branches WHERE major_name LIKE ? LIMIT 10",
            (f"%{query}%",)
        ).fetchall():
            if not any(r.get('name') == row['major_name'] for r in results):
                results.append({"source": "major_branches", "type": "branches",
                               "name": row['major_name']})

    if scope in ("all", "schools"):
        for row in db.execute(
            "SELECT name FROM schools WHERE name LIKE ? LIMIT 10",
            (f"%{query}%",)
        ).fetchall():
            results.append({"source": "schools", "type": "school", "name": row['name']})

    return results[:20]


# ── Helpers ──────────────────────────────────────────────

def _parse_dep_val(text: str) -> int:
    """Extract dependency value from text like '**7分**' or '7'."""
    if not text:
        return 10
    nums = re.findall(r'\d+', str(text))
    if nums:
        try:
            return int(nums[0])
        except (ValueError, IndexError):
            return 10
    return 10
