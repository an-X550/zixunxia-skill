"""
build_sqlite.py — 从知识库 Markdown 文件构建撑伞侠知识库.db

复用现有 6 个解析器，将结构化数据 INSERT 到 SQLite。
每次 Markdown 修改后运行此脚本重建数据库。

用法：python build_sqlite.py
"""

import sqlite3
import re
import time
from pathlib import Path

# 确保能从 mcp-server 目录运行
import sys
sys.path.insert(0, str(Path(__file__).parent))

from config import SKILL_DIR, DB_PATH, CACHE_DIR
from parsers.table_utils import parse_md_table


# ── 工具函数 ──────────────────────────────────────────────

def _split_school_names(text: str) -> list[str]:
    """将逗号/顿号分隔的院校名拆分为独立名称列表。
    '成电(985)、西电(211)、杭电、桂电' → ['成电', '西电', '杭电', '桂电']
    """
    # 移除括号注释
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'（[^）]*）', '', text)
    # 分割
    names = re.split(r'[、，,;；]', text)
    result = []
    for n in names:
        n = n.strip()
        # 过滤太短或看似非院校名的片段
        if len(n) >= 2 and not re.match(r'^[\d\s]+$', n):
            result.append(n)
    return result


def _split_major_keywords(text: str) -> list[str]:
    """将斜杠分隔的专业方向拆分为列表。
    '电子信息/计算机/自动化/机械' → ['电子信息', '计算机', '自动化', '机械']
    """
    return [m.strip() for m in re.split(r'[/／]', text) if m.strip()]


def _extract_school_direction_pairs(typical_directions: str) -> list[dict]:
    """从专业卡片'典型方向'字段提取 院校→方向 关系。

    输入示例：
    '清华：智能软件工程；浙大：AI驱动+金融科技；北邮/西电/深大：均入腾讯字节严选名单'

    返回：[{'school': '清华', 'major': '软件工程', 'direction': '智能软件工程'}, ...]
    """
    pairs = []
    # 按中文分号或换行分割
    segments = re.split(r'[；;]\s*', typical_directions)

    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue

        # 模式：学校名（可能多个用/分隔）：方向描述
        # 如 "清华：智能软件工程"
        # 如 "北邮/西电/深大：均入腾讯字节严选名单"
        match = re.match(r'^(.+?)[：:](.+)$', seg)
        if match:
            schools_part = match.group(1).strip()
            direction = match.group(2).strip()
            schools = _split_school_names(schools_part)
            for school in schools:
                if len(school) >= 2:
                    pairs.append({'school': school, 'direction': direction})

    return pairs


# ── SQLite 构建主逻辑 ─────────────────────────────────────

def build():
    t0 = time.time()

    # 删除旧数据库
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    cursor = conn.cursor()

    # ═══════════════════════════════════════════════════
    # 表定义
    # ═══════════════════════════════════════════════════

    cursor.executescript("""
    -- 学科门类
    CREATE TABLE major_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        major_count TEXT,
        school_dependency INTEGER,
        core_features TEXT
    );

    -- 专业卡片
    CREATE TABLE major_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        category TEXT,
        subcategory TEXT,
        training_plan TEXT,
        employment_outlook TEXT,
        further_study TEXT,
        admission_req TEXT,
        school_dependency TEXT,
        school_dependency_detail TEXT,
        typical_directions TEXT
    );

    -- 专业内部分叉
    CREATE TABLE major_branches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        major_name TEXT NOT NULL,
        branch_name TEXT NOT NULL,
        curriculum TEXT,
        employers TEXT,
        career_path TEXT,
        school_notes TEXT,
        UNIQUE(major_name, branch_name)
    );

    -- 专业名称误区
    CREATE TABLE major_name_traps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        major_name TEXT NOT NULL,
        real_category TEXT,
        common_misconception TEXT,
        key_explanation TEXT
    );

    -- 2025新增专业
    CREATE TABLE new_majors_2025 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT,
        direction TEXT,
        driver_type TEXT
    );

    -- 院校
    CREATE TABLE schools (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        full_name TEXT,
        is_985 INTEGER DEFAULT 0,
        is_211 INTEGER DEFAULT 0,
        is_double_first_class INTEGER DEFAULT 0,
        dfc_tier TEXT,
        province TEXT
    );

    -- 部委直属关系
    CREATE TABLE ministry_affiliations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ministry_system TEXT NOT NULL,
        school_name TEXT NOT NULL,
        strength_majors TEXT,
        UNIQUE(ministry_system, school_name)
    );

    -- 院校-专业强弱关系（从多个来源提取）
    CREATE TABLE school_major_strength (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_name TEXT NOT NULL,
        major_name TEXT NOT NULL,
        direction_note TEXT,
        source TEXT,
        UNIQUE(school_name, major_name, source)
    );

    -- 城市层级
    CREATE TABLE city_tiers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tier_level INTEGER,
        tier_name TEXT,
        features TEXT,
        representative_cities TEXT
    );

    -- 城市类型
    CREATE TABLE city_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type_name TEXT,
        features TEXT,
        typical_cities TEXT
    );

    -- 省份产业集群
    CREATE TABLE province_industries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        province_name TEXT NOT NULL UNIQUE,
        clusters TEXT,
        advantage_industries TEXT,
        future_focus TEXT
    );

    -- 专业-城市匹配规则
    CREATE TABLE major_city_match (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        major_direction TEXT NOT NULL,
        preferred_city_feature TEXT,
        representative_cities TEXT
    );

    -- 省份志愿填报配置
    CREATE TABLE province_filling_config (
        province_name TEXT PRIMARY KEY,
        filling_mode TEXT,
        max_choices TEXT,
        has_tiaji_risk INTEGER
    );

    -- 填报陷阱
    CREATE TABLE filling_traps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trap_name TEXT,
        description TEXT
    );

    -- 薪资数据源
    CREATE TABLE salary_sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_name TEXT,
        content TEXT,
        query_method TEXT
    );

    -- 就业因素框架
    CREATE TABLE employment_factors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        factor_name TEXT,
        description TEXT
    );

    -- 工具速查
    CREATE TABLE tool_references (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        purpose TEXT,
        tool_name TEXT,
        operation TEXT,
        audience TEXT
    );

    -- B站资源
    CREATE TABLE bilibili_resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        video_info TEXT,
        bv_number TEXT
    );

    -- 专业-院校关联索引（加速反向查询）
    CREATE INDEX idx_school_major_school ON school_major_strength(school_name);
    CREATE INDEX idx_school_major_major ON school_major_strength(major_name);
    CREATE INDEX idx_major_cards_name ON major_cards(name);
    CREATE INDEX idx_major_branches_major ON major_branches(major_name);
    CREATE INDEX idx_ministry_school ON ministry_affiliations(school_name);
    CREATE INDEX idx_ministry_system ON ministry_affiliations(ministry_system);
    CREATE INDEX idx_schools_name ON schools(name);
    """)

    # ═══════════════════════════════════════════════════
    # 解析并插入数据
    # ═══════════════════════════════════════════════════

    # ── 1. 专业决策库 ──
    print("[1/6] 解析专业决策库...", flush=True)
    from parsers.major_decision import parse as parse_majors
    major_data = parse_majors(SKILL_DIR)

    if major_data:
        # 1a. 学科门类
        for cat in major_data.get('categories', []):
            cursor.execute(
                "INSERT INTO major_categories (name, major_count, school_dependency, core_features) VALUES (?,?,?,?)",
                (cat.get('门类', ''), cat.get('含专业数', ''),
                 _parse_dependency_int(cat.get('院校依赖(1-10)', '')),
                 cat.get('核心特征', ''))
            )

        # 1b. 专业卡片
        current_category = ''
        current_subcategory = ''
        for name, card in major_data.get('majors', {}).items():
            cursor.execute(
                """INSERT INTO major_cards
                   (name, category, subcategory, training_plan, employment_outlook,
                    further_study, admission_req, school_dependency, school_dependency_detail, typical_directions)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (name, current_category, current_subcategory,
                 card.get('培养计划', ''), card.get('就业前景', ''),
                 card.get('深造需求', ''), card.get('报考条件', ''),
                 _extract_dependency_score(card.get('院校依赖', '')),
                 card.get('院校依赖', ''),
                 card.get('典型方向', ''))
            )

        # 1c. 名称误区
        for trap in major_data.get('naming_traps', []):
            cursor.execute(
                "INSERT INTO major_name_traps (major_name, real_category, common_misconception, key_explanation) VALUES (?,?,?,?)",
                (trap.get('专业名称', ''), trap.get('真实门类', ''),
                 trap.get('常见误解', ''), trap.get('关键说明', ''))
            )

        # 1d. 2025新增专业
        for new_m in major_data.get('new_majors_2025', []):
            cursor.execute(
                "INSERT INTO new_majors_2025 (name, category, direction) VALUES (?,?,?)",
                (new_m.get('专业', ''), new_m.get('归属门类', ''), new_m.get('方向', ''))
            )

        print(f"  → {len(major_data.get('categories',[]))} 门类, {len(major_data.get('majors',{}))} 专业卡片, "
              f"{len(major_data.get('naming_traps',[]))} 误区, {len(major_data.get('new_majors_2025',[]))} 新增专业", flush=True)

    # ── 2. 专业内部分叉速查 ──
    print("[2/6] 解析专业内部分叉...", flush=True)
    from parsers.major_branches import parse as parse_branches
    branches = parse_branches(SKILL_DIR)

    branch_count = 0
    for major_name, directions in branches.items():
        for d in directions:
            cursor.execute(
                """INSERT OR IGNORE INTO major_branches (major_name, branch_name, curriculum, employers, career_path, school_notes)
                   VALUES (?,?,?,?,?,?)""",
                (major_name, d.get('方向', ''), d.get('学什么', ''),
                 d.get('去哪类雇主', ''), d.get('典型路径', ''), d.get('选校注意', ''))
            )
            branch_count += 1
    print(f"  → {len(branches)} 专业, {branch_count} 分叉方向", flush=True)

    # ── 3. 院校评估库 + 提取院校-专业关系 ──
    print("[3/6] 解析院校评估库 + 提取院校-专业关系...", flush=True)
    from parsers.school_evaluation import parse as parse_schools
    school_data = parse_schools(SKILL_DIR)

    all_school_names = set()

    if school_data:
        # 3a. 院校名单
        for tier_name, tier_flag in [('985', 'is_985'), ('211', 'is_211'),
                                       ('double_first_a', 'is_double_first_class'),
                                       ('double_first_b', 'is_double_first_class')]:
            for name in school_data.get('lists', {}).get(tier_name, []):
                all_school_names.add(name)
                # 尝试 upsert
                cursor.execute("SELECT id FROM schools WHERE name=?", (name,))
                existing = cursor.fetchone()
                if existing:
                    if tier_flag == 'is_985':
                        cursor.execute("UPDATE schools SET is_985=1 WHERE name=?", (name,))
                    elif tier_flag == 'is_211':
                        cursor.execute("UPDATE schools SET is_211=1 WHERE name=?", (name,))
                    elif tier_flag == 'is_double_first_class':
                        cursor.execute("UPDATE schools SET is_double_first_class=1 WHERE name=?", (name,))
                    if tier_name == 'double_first_a':
                        cursor.execute("UPDATE schools SET dfc_tier='A' WHERE name=?", (name,))
                    elif tier_name == 'double_first_b':
                        cursor.execute("UPDATE schools SET dfc_tier='B' WHERE name=?", (name,))
                else:
                    cursor.execute(
                        "INSERT INTO schools (name, is_985, is_211, is_double_first_class, dfc_tier) VALUES (?,?,?,?,?)",
                        (name,
                         1 if tier_name == '985' else 0,
                         1 if tier_name in ('985', '211') else 0,
                         1 if tier_name in ('double_first_a', 'double_first_b') else 0,
                         'A' if tier_name == 'double_first_a' else ('B' if tier_name == 'double_first_b' else None))
                    )

        # 3b. 部委直属关系 + 提取 school_major_strength
        ministry_count = 0
        for m in school_data.get('ministries', []):
            ministry_system = m.get('部委系统', '')
            schools_text = m.get('代表院校', '')
            majors_text = m.get('强势专业', '')

            schools_list = _split_school_names(schools_text)
            majors_list = _split_major_keywords(majors_text)

            for school in schools_list:
                if not school:
                    continue
                all_school_names.add(school)
                # 确保院校在 schools 表中
                cursor.execute("INSERT OR IGNORE INTO schools (name) VALUES (?)", (school,))
                # 插入部委关系
                cursor.execute(
                    "INSERT OR IGNORE INTO ministry_affiliations (ministry_system, school_name, strength_majors) VALUES (?,?,?)",
                    (ministry_system, school, majors_text)
                )
                ministry_count += 1
                # 提取院校-专业强弱关系
                for major_kw in majors_list:
                    cursor.execute(
                        "INSERT OR IGNORE INTO school_major_strength (school_name, major_name, direction_note, source) VALUES (?,?,?,?)",
                        (school, major_kw, f'{ministry_system}部委直属强校', 'ministry_affiliation')
                    )

        print(f"  → {len(all_school_names)} 院校, {ministry_count} 部委-院校关联, "
              f"{len(school_data.get('ministries',[]))} 部委系统", flush=True)

    # ── 3c. 从专业卡片"典型方向"提取院校-专业关系 ──
    major_school_from_directions = 0
    for major_name, card in major_data.get('majors', {}).items():
        typical = card.get('典型方向', '')
        if typical:
            pairs = _extract_school_direction_pairs(typical)
            for p in pairs:
                school = p['school']
                all_school_names.add(school)
                # 确保院校存在
                cursor.execute("INSERT OR IGNORE INTO schools (name) VALUES (?)", (school,))
                # 插入关系
                cursor.execute(
                    "INSERT OR IGNORE INTO school_major_strength (school_name, major_name, direction_note, source) VALUES (?,?,?,?)",
                    (school, major_name, p['direction'], 'major_card_typical_direction')
                )
                major_school_from_directions += 1

    print(f"  → 从专业卡片'典型方向'提取 {major_school_from_directions} 条院校-专业关联", flush=True)

    # ── 4. 城市产业库 ──
    print("[4/6] 解析城市产业库...", flush=True)
    from parsers.city_industry import parse as parse_cities
    city_data = parse_cities(SKILL_DIR)

    if city_data:
        # 4a. 城市层级
        for tier in city_data.get('city_tiers', []):
            cursor.execute(
                "INSERT INTO city_tiers (tier_level, tier_name, features, representative_cities) VALUES (?,?,?,?)",
                (_parse_tier_level(tier.get('层级', '')), tier.get('层级', ''),
                 tier.get('特征', ''), tier.get('代表城市', ''))
            )

        # 4b. 城市类型
        for ct in city_data.get('city_types', []):
            cursor.execute(
                "INSERT INTO city_types (type_name, features, typical_cities) VALUES (?,?,?)",
                (ct.get('类型', ''), ct.get('特征', ''), ct.get('典型城市', ''))
            )

        # 4c. 省份产业
        for pname, pdata in city_data.get('provinces', {}).items():
            cursor.execute(
                "INSERT INTO province_industries (province_name, clusters, advantage_industries, future_focus) VALUES (?,?,?,?)",
                (pname,
                 '\n'.join(pdata.get('clusters', [])) if isinstance(pdata.get('clusters'), list) else str(pdata.get('clusters', '')),
                 pdata.get('advantages', ''),
                 pdata.get('future_focus', ''))
            )

        # 4d. 专业-城市匹配
        for mc in city_data.get('major_city_match', []):
            cursor.execute(
                "INSERT INTO major_city_match (major_direction, preferred_city_feature, representative_cities) VALUES (?,?,?)",
                (mc.get('专业方向', ''), mc.get('首选城市特征', ''), mc.get('代表城市', ''))
            )

        print(f"  → {len(city_data.get('city_tiers',[]))} 城市层级, {len(city_data.get('city_types',[]))} 城市类型, "
              f"{len(city_data.get('provinces',{}))} 省份产业, {len(city_data.get('major_city_match',[]))} 专业-城市匹配", flush=True)

    # ── 5. 填报规则库 ──
    print("[5/6] 解析填报规则库...", flush=True)
    from parsers.filling_rules import parse as parse_rules
    rules_data = parse_rules(SKILL_DIR)

    if rules_data:
        # 5a. 省份志愿配置
        province_count = 0
        for pname, config in rules_data.get('province_configs', {}).items():
            if pname.startswith('_'):
                continue
            mode = config.get('mode', '')
            has_tiaji = 0 if '无调剂' in mode or '院校+专业' in mode else 1
            cursor.execute(
                "INSERT INTO province_filling_config (province_name, filling_mode, max_choices, has_tiaji_risk) VALUES (?,?,?,?)",
                (pname, mode, config.get('count', ''), has_tiaji)
            )
            province_count += 1

        # 5b. 填报陷阱
        for trap in rules_data.get('traps', []):
            cursor.execute(
                "INSERT INTO filling_traps (trap_name, description) VALUES (?,?)",
                (trap.get('陷阱', ''), trap.get('说明', ''))
            )

        print(f"  → {province_count} 省志愿配置, {len(rules_data.get('traps',[]))} 填报陷阱", flush=True)

    # ── 6. 行业薪资与工具箱 ──
    print("[6/6] 解析行业薪资与工具箱...", flush=True)
    from parsers.salary_tools import parse as parse_salary
    salary_data = parse_salary(SKILL_DIR)

    if salary_data:
        # 6a. 薪资数据源
        for src in salary_data.get('salary_paths', {}).get('sources', []):
            cursor.execute(
                "INSERT INTO salary_sources (source_name, content, query_method) VALUES (?,?,?)",
                (src.get('来源', ''), src.get('内容', ''), src.get('查询方式', ''))
            )

        # 6b. 就业因素
        for f in salary_data.get('framework', {}).get('factors', []):
            cursor.execute(
                "INSERT INTO employment_factors (factor_name, description) VALUES (?,?)",
                (f.get('因素', ''), f.get('说明', ''))
            )

        # 6c. 工具速查（学生版+咨询侠版）
        for tool in salary_data.get('tools', {}).get('for_student', []):
            cursor.execute(
                "INSERT INTO tool_references (purpose, tool_name, operation, audience) VALUES (?,?,?,?)",
                (tool.get('用途', ''), tool.get('工具', ''), tool.get('操作', ''), '学生')
            )
        for tool in salary_data.get('tools', {}).get('for_consultant', []):
            cursor.execute(
                "INSERT INTO tool_references (purpose, tool_name, operation, audience) VALUES (?,?,?,?)",
                (tool.get('用途', ''), tool.get('渠道', ''), '', '咨询侠')
            )

        # 6d. B站资源
        for vid in salary_data.get('bilibili', {}).get('videos', []):
            cursor.execute(
                "INSERT INTO bilibili_resources (category, video_info, bv_number) VALUES (?,?,?)",
                (vid.get('门类', ''), vid.get('关键B站视频', ''),
                 _extract_bv(vid.get('关键B站视频', '')))
            )

        print(f"  → {len(salary_data.get('salary_paths',{}).get('sources',[]))} 薪资数据源, "
              f"{len(salary_data.get('tools',{}).get('for_student',[]))} 学生工具, "
              f"{len(salary_data.get('bilibili',{}).get('videos',[]))} B站资源", flush=True)

    # ═══════════════════════════════════════════════════
    # 完工
    # ═══════════════════════════════════════════════════

    conn.commit()

    # 统计
    table_counts = {}
    for table in ['major_categories', 'major_cards', 'major_branches', 'major_name_traps',
                   'new_majors_2025', 'schools', 'ministry_affiliations', 'school_major_strength',
                   'city_tiers', 'city_types', 'province_industries', 'major_city_match',
                   'province_filling_config', 'filling_traps', 'salary_sources',
                   'employment_factors', 'tool_references', 'bilibili_resources']:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        table_counts[table] = cursor.fetchone()[0]

    conn.close()

    elapsed = (time.time() - t0) * 1000
    size_kb = DB_PATH.stat().st_size / 1024 if DB_PATH.exists() else 0

    print(f"\n[OK] 数据库构建完成: {DB_PATH} ({size_kb:.0f} KB, {elapsed:.0f}ms)", flush=True)
    print(f"----", flush=True)
    for table, count in table_counts.items():
        if count > 0:
            print(f"  {table}: {count} rows", flush=True)
    total = sum(table_counts.values())
    print(f"  ----", flush=True)
    print(f"  Total: {total} rows ({len(table_counts)} tables)", flush=True)

    return table_counts


# ── 辅助函数 ──────────────────────────────────────────────

def _parse_dependency_int(text: str) -> int | None:
    """从 '6-9' 或 '**10**' 中提取数字"""
    nums = re.findall(r'\d+', str(text))
    if nums:
        return int(nums[0])
    return None


def _extract_dependency_score(text: str) -> str:
    """从院校依赖字段提取分数，如 '**7分**。腾讯校招严选...' → '7'"""
    match = re.search(r'\*{0,2}(\d+)\s*分', str(text))
    if match:
        return match.group(1)
    return ''


def _parse_tier_level(text: str) -> int | None:
    """从层级文本提取数字，如 '第一层：...' → 1"""
    nums = re.findall(r'\d+', str(text))
    if nums:
        return int(nums[0])
    return None


def _extract_bv(text: str) -> str | None:
    """从B站视频信息提取BV号"""
    match = re.search(r'(BV[a-zA-Z0-9]+)', str(text))
    if match:
        return match.group(1)
    return None


# ── 入口 ──────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"构建撑伞侠知识库.db", flush=True)
    print(f"  源目录: {SKILL_DIR}", flush=True)
    print(f"  目标: {DB_PATH}", flush=True)
    print(flush=True)
    build()
