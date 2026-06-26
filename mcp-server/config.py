"""
咨询侠知识库 MCP Server — 路径配置
"""
import os
from pathlib import Path

# Skill 根目录（SKILL.md 所在位置）
SKILL_DIR = Path(os.environ.get(
    "ZIXUNXIA_SKILL_DIR",
    Path(__file__).parent.parent
)).resolve()

# 数据层 MD 文件
DATA_DIR = SKILL_DIR / "知识库" / "数据层"
MD_FILES = {
    "major_decision":    DATA_DIR / "专业决策库.md",
    "major_branches":    DATA_DIR / "专业内部分叉速查.md",
    "city_industry":     DATA_DIR / "城市产业库.md",
    "filling_rules":     DATA_DIR / "填报规则库.md",
    "school_evaluation": DATA_DIR / "院校评估库.md",
    "salary_tools":      DATA_DIR / "行业薪资与工具箱.md",
}

# 可选 SQLite 数据库
DB_PATH = Path(os.environ.get(
    "ZIXUNXIA_DB_PATH",
    SKILL_DIR / "撑伞侠知识库.db"
))

# 缓存目录
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_FILE = CACHE_DIR / "parsed_data.json"

# 确保缓存目录存在
CACHE_DIR.mkdir(parents=True, exist_ok=True)
