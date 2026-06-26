"""
咨询侠知识库 MCP Server — 10 个数据查询工具

Claude Code 通过 stdio 启动并管理此进程。
数据路径：SQLite 优先，DataStore 兜底。
"""

import json
import sqlite3
import asyncio
from pathlib import Path

from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

from data_store import store
from config import DB_PATH
from db_queries import (
    get_major_card, fuzzy_match_major, get_major_branches, fuzzy_match_branch_major,
    search_majors_filtered, get_categories,
    get_province_industry, fuzzy_match_province, get_city_tiers, get_city_types,
    search_in_city_tier, search_in_city_type,
    get_school_lists, get_ministries,
    get_province_filling_config, fuzzy_match_province_config,
    get_all_provinces_config, get_filling_traps,
    get_salary_data, get_available_salary_types,
    search_all,
)

server = Server("zixunxia-knowledge")


# ── 工具列表 ──────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(name="query_major_detail", description=(
            "查询某个专业的完整决策卡片：培养计划、就业前景、深造需求、"
            "报考条件、院校依赖程度、典型方向。输入专业全名如'电气工程'或'软件工程'。"
        ), inputSchema={
            "type": "object",
            "properties": {
                "major_name": {"type": "string", "description": "专业全名"},
                "fields": {"type": "array", "items": {"type": "string"},
                    "description": "可选，指定返回的字段子集"}
            }, "required": ["major_name"]
        }),

        Tool(name="query_major_branches", description=(
            "查询某个专业的内部分叉方向。同一专业名不同方向课程、就业、选校完全不同。"
            "例如'自动化'有PLC/工业控制、机器人/智能控制、嵌入式/物联网三个方向。"
        ), inputSchema={
            "type": "object",
            "properties": {
                "major_name": {"type": "string", "description": "专业名称"}
            }, "required": ["major_name"]
        }),

        Tool(name="search_majors", description=(
            "按条件搜索/过滤专业列表。可按门类、关键词、院校依赖度范围、是否需深造筛选。"
            "Prompt1 生成专业推荐时使用此工具发现候选专业。"
        ), inputSchema={
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "门类：工学/医学/理学/经济学/管理学/法学/文学/农学/教育学/艺术学/历史学/哲学"},
                "keywords": {"type": "string", "description": "模糊匹配专业名"},
                "school_dependency_max": {"type": "integer", "description": "院校依赖度上限(1-10)"},
                "further_study_required": {"type": "boolean", "description": "是否只要需深造的专业"}
            }
        }),

        Tool(name="query_city_industry", description=(
            "查询城市或省份的产业集群、优势产业和未来重点方向。"
            "输入城市名（如'合肥'）或省份名（如'广东'），返回该地区的产业布局。"
        ), inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "城市名或省份名"}
            }, "required": ["name"]
        }),

        Tool(name="query_school_info", description=(
            "查询院校分层信息、部委直属院校、推免率。可按985/211/双一流筛选，"
            "或按部委系统（航空航天部/电子工业部/邮电部等）查行业强校。"
        ), inputSchema={
            "type": "object",
            "properties": {
                "query_type": {"type": "string",
                    "enum": ["tiers", "lists", "ministries", "tuimian", "framework"],
                    "description": "查什么：tiers=分层标签, lists=院校名单, ministries=部委强校, tuimian=推免率, framework=7维评估框架"},
                "filter": {"type": "string", "description": "按985/211/双一流过滤"},
                "ministry": {"type": "string", "description": "部委系统名，如'电子工业部'"}
            }, "required": ["query_type"]
        }),

        Tool(name="query_rules", description=(
            "查询高考志愿填报规则：投档/退档/滑档/调剂/选科/赋分/省模式/稳保策略/陷阱。"
            "可按主题查规则，或按省份查该省的志愿填报模式。"
        ), inputSchema={
            "type": "object",
            "properties": {
                "topic": {"type": "string",
                    "enum": ["投档", "退档", "滑档", "调剂", "选科", "赋分", "专业分配", "稳保策略", "位次转换", "陷阱", "批次", "提前批", "征集志愿", "平行志愿"],
                    "description": "查询的规则主题"},
                "province": {"type": "string", "description": "省份名，查询该省的志愿模式配置"}
            }
        }),

        Tool(name="query_career_data", description=(
            "查询薪资查询路径、6因素就业分析框架、工具速查表、就业四象限、行业趋势、B站资源。"
        ), inputSchema={
            "type": "object",
            "properties": {
                "query_type": {"type": "string",
                    "enum": ["salary_paths", "framework", "tools", "quadrants", "trends", "bilibili", "toolbox", "quake"],
                    "description": "数据类型"}
            }, "required": ["query_type"]
        }),

        Tool(name="search_knowledge_base", description=(
            "兜底搜索——在所有知识库数据中按关键词查找。当不确定数据属于哪个工具时使用。"
            "支持搜索专业名、院校名、城市名、规则关键词。"
        ), inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "scope": {"type": "string", "enum": ["all", "majors", "schools", "cities", "rules"],
                    "description": "搜索范围，默认全部"}
            }, "required": ["query"]
        }),

        Tool(name="query_school_by_major", description=(
            "反向查询——根据专业名查全国哪些院校是该专业的强校。"
            "数据来源：部委直属院校关系 + 专业卡片典型方向。"
            "输入专业名（如'软件工程''电子信息'），返回开设该强势专业的院校列表，"
            "含院校层次（985/211/双一流/部委直属）和方向说明。"
        ), inputSchema={
            "type": "object",
            "properties": {
                "major_name": {"type": "string", "description": "专业名，如'软件工程'、'电子信息'、'电气工程'"},
                "min_tier": {"type": "string", "enum": ["985", "211", "双一流", "全部"],
                    "description": "最低院校层次过滤，默认全部"}
            }, "required": ["major_name"]
        }),

        Tool(name="query_major_by_school", description=(
            "正向查询——根据院校名查该校有哪些强势专业。"
            "数据来源：部委直属院校关系 + 专业卡片典型方向。"
            "输入院校名（如'成电''哈工大'），返回该校的优势专业列表，"
            "含专业方向说明和优势来源。"
        ), inputSchema={
            "type": "object",
            "properties": {
                "school_name": {"type": "string", "description": "院校名，如'成电'、'哈工大'、'清华'"}
            }, "required": ["school_name"]
        }),
    ]


# ── 工具分发 ──────────────────────────────────────────────

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    handlers = {
        "query_major_detail": _query_major_detail,
        "query_major_branches": _query_major_branches,
        "search_majors": _search_majors,
        "query_city_industry": _query_city_industry,
        "query_school_info": _query_school_info,
        "query_rules": _query_rules,
        "query_career_data": _query_career_data,
        "search_knowledge_base": _search_knowledge_base,
        "query_school_by_major": _query_school_by_major,
        "query_major_by_school": _query_major_by_school,
    }
    handler = handlers.get(name)
    if not handler:
        return [TextContent(type="text",
            text=json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False))]
    try:
        return await handler(arguments)
    except Exception as e:
        return [TextContent(type="text",
            text=json.dumps({"error": str(e)}, ensure_ascii=False))]


# ── 工具实现 ──────────────────────────────────────────────

async def _query_major_detail(args: dict) -> list[TextContent]:
    name = args.get("major_name", "").strip()
    fields = args.get("fields")

    db = _get_db()
    if db is not None:
        try:
            card = get_major_card(db, name)
            if card:
                db.close()
                if fields:
                    card = {f: card[f] for f in fields if f in card}
                return _json({"major": name, "card": card})
            suggestions = fuzzy_match_major(db, name)
            db.close()
            return _json({"error": "not_found" if not suggestions else "exact_match_not_found",
                          "suggestions": suggestions[:10]})
        except Exception:
            _safe_close(db)

    # Fallback to DataStore
    if name in store.majors:
        card = store.majors[name]
        if fields:
            card = {f: card[f] for f in fields if f in card}
        return _json({"major": name, "card": card})
    matches = [n for n in store.majors if name in n or n in name]
    return _json({"error": "not_found" if not matches else "exact_match_not_found",
                  "suggestions": matches[:10]})


async def _query_major_branches(args: dict) -> list[TextContent]:
    name = args.get("major_name", "").strip()

    db = _get_db()
    if db is not None:
        try:
            branches = get_major_branches(db, name)
            if branches is not None:
                db.close()
                return _json({"major": name, "branches": branches, "count": len(branches)})
            suggestions = fuzzy_match_branch_major(db, name)
            db.close()
            return _json({"error": "not_found" if not suggestions else "exact_match_not_found",
                          "suggestions": suggestions})
        except Exception:
            _safe_close(db)

    # Fallback to DataStore
    if name in store.major_branches:
        return _json({"major": name, "branches": store.major_branches[name],
                      "count": len(store.major_branches[name])})
    matches = [n for n in store.major_branches if name in n or n in name]
    return _json({"error": "not_found" if not matches else "exact_match_not_found",
                  "suggestions": matches})


async def _search_majors(args: dict) -> list[TextContent]:
    category = args.get("category", "").strip()
    keywords = args.get("keywords", "").strip()
    dep_max = args.get("school_dependency_max")
    further_study = args.get("further_study_required")

    # No filters: return categories
    if not category and not keywords and dep_max is None and further_study is None:
        db = _get_db()
        if db is not None:
            try:
                cats = get_categories(db); db.close()
                return _json({"majors_count": len(store.majors), "categories": cats,
                              "hint": "使用 category/keywords/school_dependency_max 筛选"})
            except Exception: _safe_close(db)
        return _json({"majors_count": len(store.majors), "categories": store.categories,
                      "hint": "使用 category/keywords/school_dependency_max 筛选"})

    # SQLite path
    db = _get_db()
    if db is not None:
        try:
            results = search_majors_filtered(db, keywords, dep_max, further_study); db.close()
            return _json({"results": results, "count": len(results)})
        except Exception: _safe_close(db)

    # Fallback to DataStore
    results = []
    for name, card in store.majors.items():
        # 门类过滤（基于父章节——简单按专业名所属分类）
        if keywords and keywords not in name:
            continue
        if dep_max is not None:
            dep_str = card.get('院校依赖', '')
            try:
                dep_val = int(''.join(c for c in dep_str if c.isdigit())[:2])
            except (ValueError, IndexError):
                dep_val = 10
            if dep_val > dep_max:
                continue
        if further_study:
            shenzao = card.get('深造需求', '')
            if '本科可' in shenzao or '本科就' in shenzao:
                continue
        results.append({
            "name": name,
            "院校依赖": card.get('院校依赖', '')[:50],
            "深造需求": card.get('深造需求', '')[:80],
            "就业前景": card.get('就业前景', '')[:80],
        })

    return _json({"results": results, "count": len(results)})


async def _query_city_industry(args: dict) -> list[TextContent]:
    name = args.get("name", "").strip()
    result = {"query": name}

    db = _get_db()
    if db is not None:
        try:
            prov = get_province_industry(db, name)
            if prov:
                db.close(); result["type"] = "province"; result["data"] = prov; return _json(result)
            pmatches = fuzzy_match_province(db, name)
            if pmatches:
                prov = get_province_industry(db, pmatches[0]); db.close()
                result["type"] = "province"; result["data"] = prov
                result["matched_province"] = pmatches[0]; return _json(result)
            tier = search_in_city_tier(db, name)
            if tier: db.close(); result["type"] = "city_tier"; result["data"] = tier; return _json(result)
            ctype = search_in_city_type(db, name)
            if ctype: db.close(); result["type"] = "city_type"; result["data"] = ctype; return _json(result)
            db.close()
        except Exception: _safe_close(db)

    # Fallback to DataStore
    if name in store.cities.get('provinces', {}):
        result["type"] = "province"; result["data"] = store.cities['provinces'][name]; return _json(result)
    for pname in store.cities.get('provinces', {}):
        if name in pname or pname in name:
            result["type"] = "province"; result["data"] = store.cities['provinces'][pname]
            result["matched_province"] = pname; return _json(result)
    for tier in store.cities.get('city_tiers', []):
        if name in tier.get('代表城市', ''):
            result["type"] = "city_tier"; result["data"] = tier; return _json(result)
    for ctype in store.cities.get('city_types', []):
        if name in ctype.get('典型城市', ''):
            result["type"] = "city_type"; result["data"] = ctype; return _json(result)

    result["error"] = "not_found"
    result["available_regions"] = sorted(store.cities.get('provinces', {}).keys())[:30]
    return _json(result)


async def _query_school_info(args: dict) -> list[TextContent]:
    qtype = args.get("query_type", "tiers")
    result = {"query_type": qtype}

    db = _get_db()
    if qtype == "lists" and db is not None:
        try:
            lists = get_school_lists(db); db.close()
            filt = args.get("filter")
            result["lists"] = {filt: lists.get(filt, [])} if filt else lists
            return _json(result)
        except Exception: _safe_close(db)
    elif qtype == "ministries" and db is not None:
        try:
            ministry = args.get("ministry", "").strip()
            result["ministries"] = get_ministries(db, ministry); db.close()
            return _json(result)
        except Exception: _safe_close(db)

    # Fallback to DataStore (tiers, tuimian, framework are text-heavy)
    if qtype == "tiers":
        result["tiers"] = store.schools.get('tiers', {})
    elif qtype == "lists":
        result["lists"] = store.schools.get('lists', {})
        filt = args.get("filter")
        if filt:
            result["lists"] = {filt: store.schools.get('lists', {}).get(filt, [])}
    elif qtype == "ministries":
        ministry = args.get("ministry", "").strip()
        all_m = store.schools.get('ministries', [])
        result["ministries"] = [m for m in all_m if ministry in m.get('部委系统', '')] if ministry else all_m
    elif qtype == "tuimian":
        result["tuimian_rates"] = store.schools.get('tuimian_rates', [])
    elif qtype == "framework":
        result["framework"] = store.schools.get('evaluation_framework', '')
    return _json(result)


async def _query_rules(args: dict) -> list[TextContent]:
    topic = args.get("topic", "").strip()
    province = args.get("province", "").strip()
    result = {}

    # Province lookup: try SQLite first
    if province:
        db = _get_db()
        if db is not None:
            try:
                config = get_province_filling_config(db, province)
                if config:
                    db.close(); result["province"] = province; result["config"] = config; return _json(result)
                matches = fuzzy_match_province_config(db, province); db.close()
                result["error"] = "not_found" if not matches else "exact_match_not_found"
                result["suggestions"] = matches; return _json(result)
            except Exception: _safe_close(db)
        # Fallback
        configs = store.filling_rules.get('province_configs', {})
        if province in configs:
            result["province"] = province; result["config"] = configs[province]; return _json(result)
        matches = [p for p in configs if province in p or p in province]
        result["error"] = "not_found" if not matches else "exact_match_not_found"
        result["suggestions"] = matches; return _json(result)

    # Topic lookup: traps go to SQLite, rest stay on DataStore
    if topic:
        topic_map = {
            '投档': 'concepts', '退档': 'concepts', '滑档': 'concepts', '调剂': 'concepts',
            '专业分配': 'allocation_rules',
            '选科': 'subject_selection', '赋分': 'subject_selection',
            '稳保策略': 'wenbao_strategy',
            '位次转换': 'rank_conversion',
            '提前批': 'batch_strategy', '征集志愿': 'batch_strategy', '批次': 'batch_strategy',
            '平行志愿': 'batch_strategy',
            '陷阱': 'traps',
        }
        section_key = topic_map.get(topic, 'concepts')

        if section_key == 'traps':
            db = _get_db()
            if db is not None:
                try:
                    traps = get_filling_traps(db); db.close(); result["traps"] = traps; return _json(result)
                except Exception: _safe_close(db)
            result["traps"] = store.filling_rules.get('traps', []); return _json(result)

        section = store.filling_rules.get(section_key, {})
        result["topic"] = topic
        result["tables"] = section.get('tables', [])
        result["text"] = section.get('full_text', '')[:2000]
        return _json(result)

    # No params
    return _json({"available_topics": [
        "投档", "退档", "滑档", "调剂", "选科", "赋分", "专业分配",
        "稳保策略", "位次转换", "陷阱", "提前批", "征集志愿", "平行志愿"
    ], "available_provinces": sorted(
        [p for p in store.filling_rules.get('province_configs', {}) if not p.startswith('_')]
    )})


async def _query_career_data(args: dict) -> list[TextContent]:
    qtype = args.get("query_type", "salary_paths")

    db = _get_db()
    if db is not None:
        try:
            data = get_salary_data(db, qtype)
            db.close()
            if data is not None:
                return _json({qtype: data})
        except Exception:
            _safe_close(db)

    # Fallback to DataStore
    data = store.salary.get(qtype)
    if data is not None:
        return _json({qtype: data})
    return _json({"error": f"未知 query_type: {qtype}",
                  "available": list(store.salary.keys())})


async def _search_knowledge_base(args: dict) -> list[TextContent]:
    query = args.get("query", "").strip()
    scope = args.get("scope", "all")

    db = _get_db()
    if db is not None:
        try:
            results = search_all(db, query, scope); db.close()
            return _json({"query": query, "results": results, "count": len(results)})
        except Exception: _safe_close(db)

    results = store.search(query, scope)
    return _json({"query": query, "results": results, "count": len(results)})


# ── SQLite 工具实现 ───────────────────────────────────────

def _get_db() -> sqlite3.Connection | None:
    """获取 SQLite 连接，数据库不存在时返回 None"""
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


async def _query_school_by_major(args: dict) -> list[TextContent]:
    major_name = args.get("major_name", "").strip()
    min_tier = args.get("min_tier", "全部")

    db = _get_db()
    if db is None:
        return _json({"error": "数据库未构建，请先运行 build_sqlite.py"})

    try:
        # 1. 从 school_major_strength 查院校-专业关系
        results = []
        seen_schools = set()

        # 精确匹配 + 模糊匹配专业名
        for query, match_type in [(major_name, "exact"), (f"%{major_name}%", "fuzzy")]:
            if match_type == "fuzzy" and results:
                break  # 精确匹配有结果就跳过模糊

            rows = db.execute(
                """SELECT sms.school_name, sms.major_name, sms.direction_note, sms.source,
                          s.is_985, s.is_211, s.is_double_first_class, s.dfc_tier
                   FROM school_major_strength sms
                   LEFT JOIN schools s ON s.name = sms.school_name
                   WHERE sms.major_name LIKE ?
                   ORDER BY s.is_985 DESC, s.is_211 DESC, s.is_double_first_class DESC""",
                (query,)
            ).fetchall()

            for row in rows:
                school = row['school_name']
                if school in seen_schools:
                    continue
                seen_schools.add(school)

                # 层级过滤
                tier_label = _school_tier_label(row)
                if min_tier == "985" and not row['is_985']:
                    continue
                if min_tier == "211" and not (row['is_985'] or row['is_211']):
                    continue
                if min_tier == "双一流" and not row['is_double_first_class']:
                    continue

                results.append({
                    "school": school,
                    "tier": tier_label,
                    "major": row['major_name'],
                    "direction": row['direction_note'],
                    "source": row['source'],
                })

        # 2. 也从部委直属表补充查询（按强势专业关键词模糊匹配）
        ministry_rows = db.execute(
            """SELECT ma.school_name, ma.ministry_system, ma.strength_majors,
                      s.is_985, s.is_211, s.is_double_first_class
               FROM ministry_affiliations ma
               LEFT JOIN schools s ON s.name = ma.school_name
               WHERE ma.strength_majors LIKE ?
               ORDER BY s.is_985 DESC, s.is_211 DESC""",
            (f"%{major_name}%",)
        ).fetchall()

        for row in ministry_rows:
            school = row['school_name']
            if school in seen_schools:
                continue
            seen_schools.add(school)

            tier_label = _school_tier_label(row)
            if min_tier == "985" and not row['is_985']:
                continue
            if min_tier == "211" and not (row['is_985'] or row['is_211']):
                continue
            if min_tier == "双一流" and not row['is_double_first_class']:
                continue

            results.append({
                "school": school,
                "tier": tier_label,
                "major": major_name,
                "direction": f"{row['ministry_system']}部委直属 — {row['strength_majors']}",
                "source": "ministry_affiliation",
            })

        db.close()

        # 也查专业卡片中是否有该专业（确认专业名存在）
        if not results:
            return _json({
                "major": major_name,
                "results": [],
                "count": 0,
                "hint": f"未找到'{major_name}'的院校强校记录。可尝试 query_major_detail 确认专业全名，或 search_knowledge_base 搜索相关专业。"
            })

        return _json({
            "major": major_name,
            "results": results,
            "count": len(results),
            "tier_filter": min_tier,
        })

    except Exception as e:
        try:
            db.close()
        except Exception:
            pass
        return _json({"error": str(e)})


async def _query_major_by_school(args: dict) -> list[TextContent]:
    school_name = args.get("school_name", "").strip()

    db = _get_db()
    if db is None:
        return _json({"error": "数据库未构建，请先运行 build_sqlite.py"})

    try:
        results = []
        seen_majors = set()

        # 1. 查院校基本信息
        school_info = db.execute(
            "SELECT name, is_985, is_211, is_double_first_class, dfc_tier FROM schools WHERE name LIKE ?",
            (f"%{school_name}%",)
        ).fetchall()

        # 2. 从 school_major_strength 查
        for query in [school_name, f"%{school_name}%"]:
            rows = db.execute(
                """SELECT school_name, major_name, direction_note, source
                   FROM school_major_strength
                   WHERE school_name LIKE ?
                   ORDER BY major_name""",
                (query,)
            ).fetchall()

            for row in rows:
                key = row['major_name']
                if key in seen_majors:
                    continue
                seen_majors.add(key)
                results.append({
                    "major": row['major_name'],
                    "direction": row['direction_note'],
                    "source": row['source'],
                })

            if results:
                break

        # 3. 从部委直属查该校的强势专业
        ministry_rows = db.execute(
            """SELECT ministry_system, strength_majors
               FROM ministry_affiliations
               WHERE school_name LIKE ?
               ORDER BY ministry_system""",
            (f"%{school_name}%",)
        ).fetchall()

        for row in ministry_rows:
            results.append({
                "major": row['strength_majors'],
                "direction": f"{row['ministry_system']}部委直属强校",
                "source": "ministry_affiliation",
            })

        db.close()

        # 构建院校信息
        school_tier = None
        if school_info:
            first = school_info[0]
            school_tier = _school_tier_label(first)

        if not results:
            return _json({
                "school": school_name,
                "tier": school_tier,
                "results": [],
                "count": 0,
                "hint": f"未找到'{school_name}'的强势专业记录。可尝试 query_school_info 查院校分层和部委归属。"
            })

        return _json({
            "school": school_name,
            "tier": school_tier,
            "results": results,
            "count": len(results),
        })

    except Exception as e:
        try:
            db.close()
        except Exception:
            pass
        return _json({"error": str(e)})


def _school_tier_label(row) -> str | None:
    """从数据库行推断院校层级标签"""
    if row['is_985']:
        return '985'
    if row['is_211']:
        return '211'
    if row['is_double_first_class']:
        return f"双一流{row['dfc_tier'] or ''}"
    return None


def _json(data: dict) -> list[TextContent]:
    return [TextContent(type="text",
        text=json.dumps(data, ensure_ascii=False, indent=2))]


# ── 入口 ──────────────────────────────────────────────────

async def main():
    # Windows encoding safeguard: force UTF-8 for stdio MCP transport
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except (AttributeError, OSError):
            import io
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer, encoding='utf-8', errors='replace')

    print("[zixunxia-knowledge] Initializing...", flush=True)
    store.initialize()
    print(f"[zixunxia-knowledge] Ready. {len(store.majors)} majors, "
          f"{len(store.major_branches)} branches, "
          f"{len(store.categories)} categories.", flush=True)

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream,
                         server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
