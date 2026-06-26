"""
内存数据存储 — 持有所有已解析的知识库数据，并提供 JSON 缓存和关键词搜索。
"""

import json
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timezone

from config import SKILL_DIR, MD_FILES, CACHE_FILE


class DataStore:
    def __init__(self):
        # 专业内部分叉
        self.major_branches: Dict[str, List[Dict[str, str]]] = {}
        # 专业决策库
        self.majors: Dict[str, Dict[str, str]] = {}
        self.categories: List[Dict[str, str]] = []
        self.naming_traps: List[Dict[str, str]] = []
        self.new_majors_2025: List[Dict[str, str]] = []
        # 城市产业
        self.cities: Dict[str, Any] = {}
        # 填报规则
        self.filling_rules: Dict[str, Any] = {}
        # 院校评估
        self.schools: Dict[str, Any] = {}
        # 薪资工具
        self.salary: Dict[str, Any] = {}

    def initialize(self):
        """初始化：尝试从缓存加载，失效则重新解析"""
        if self._load_cache():
            return
        self._parse_all()
        self._save_cache()

    def _load_cache(self) -> bool:
        if not CACHE_FILE.exists():
            return False
        try:
            cache = json.loads(CACHE_FILE.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            return False

        src_mtime = self._src_files_hash()
        if cache.get('src_hash') != src_mtime:
            return False

        self.major_branches = cache.get('major_branches', {})
        self.majors = cache.get('majors', {})
        self.categories = cache.get('categories', [])
        self.naming_traps = cache.get('naming_traps', [])
        self.new_majors_2025 = cache.get('new_majors_2025', [])
        self.cities = cache.get('cities', {})
        self.filling_rules = cache.get('filling_rules', {})
        self.schools = cache.get('schools', {})
        self.salary = cache.get('salary', {})
        return True

    def _save_cache(self):
        cache = {
            'src_hash': self._src_files_hash(),
            'major_branches': self.major_branches,
            'majors': self.majors,
            'categories': self.categories,
            'naming_traps': self.naming_traps,
            'new_majors_2025': self.new_majors_2025,
            'cities': self.cities,
            'filling_rules': self.filling_rules,
            'schools': self.schools,
            'salary': self.salary,
            'cached_at': datetime.now(timezone.utc).isoformat(),
        }
        CACHE_FILE.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

    def _src_files_hash(self) -> str:
        parts = []
        for key, path in MD_FILES.items():
            if path.exists():
                parts.append(f"{key}:{path.stat().st_mtime}")
        return hashlib.md5('|'.join(parts).encode()).hexdigest()

    def _parse_all(self):
        t0 = time.time()

        # 专业内部分叉速查
        from parsers.major_branches import parse as parse_branches
        self.major_branches = parse_branches(SKILL_DIR)

        # 专业决策库
        from parsers.major_decision import parse as parse_majors
        major_data = parse_majors(SKILL_DIR)
        self.majors = major_data.get('majors', {})
        self.categories = major_data.get('categories', [])
        self.naming_traps = major_data.get('naming_traps', [])
        self.new_majors_2025 = major_data.get('new_majors_2025', [])

        # 城市产业库
        from parsers.city_industry import parse as parse_cities
        self.cities = parse_cities(SKILL_DIR)

        # 填报规则库
        from parsers.filling_rules import parse as parse_rules
        self.filling_rules = parse_rules(SKILL_DIR)

        # 院校评估库
        from parsers.school_evaluation import parse as parse_schools
        self.schools = parse_schools(SKILL_DIR)

        # 行业薪资与工具箱
        from parsers.salary_tools import parse as parse_salary
        self.salary = parse_salary(SKILL_DIR)

        elapsed = (time.time() - t0) * 1000
        print(f"[DataStore] All parsed: {len(self.majors)} majors, "
              f"{len(self.major_branches)} branches, "
              f"{len(self.categories)} categories, "
              f"{len(self.filling_rules.get('province_configs', {}))} provinces "
              f"in {elapsed:.0f}ms", flush=True)

    def search(self, query: str, scope: str = 'all') -> List[Dict[str, Any]]:
        """关键词搜索——在已解析数据中查找匹配项"""
        results = []

        if scope in ('all', 'majors'):
            for name, card in self.majors.items():
                if query in name:
                    results.append({
                        'source': 'major_decision',
                        'type': 'major_card',
                        'name': name,
                        'snippet': {k: v[:80] for k, v in list(card.items())[:3]},
                    })
            # 也搜分叉
            for name in self.major_branches:
                if query in name and not any(r.get('name') == name for r in results):
                    results.append({
                        'source': 'major_branches',
                        'type': 'branches',
                        'name': name,
                        'snippet': f'{len(self.major_branches[name])} 个方向',
                    })

        if scope in ('all', 'schools'):
            for list_name, schools in self.schools.get('lists', {}).items():
                for s in schools:
                    if query in s:
                        results.append({
                            'source': 'school_evaluation',
                            'type': 'school',
                            'name': s,
                            'snippet': f'来自 {list_name} 名单',
                        })

        return results[:20]  # 最多返回20条


store = DataStore()
