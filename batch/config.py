"""Central configuration for the batch module.

Reads secrets from environment variables (or .env file).
All paths are resolved relative to the skill root directory.
"""

import os
from pathlib import Path

# ── Paths ────────────────────────────────────────────────
SKILL_DIR = Path(os.environ.get("ZIXUNXIA_SKILL_DIR", Path(__file__).resolve().parent.parent))
DB_PATH = SKILL_DIR / "撑伞侠知识库.db"
CASES_DIR = SKILL_DIR / "cases"
PROMPTS_DIR = SKILL_DIR / "知识库" / "核心方法论"
PROMPT_TEMPLATE_FILE = PROMPTS_DIR / "AI提示词模板.md"

# ── DeepSeek API ─────────────────────────────────────────
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

# Try loading from .env if key not in environment
if not DEEPSEEK_API_KEY:
    try:
        from dotenv import load_dotenv
        env_file = SKILL_DIR / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
    except ImportError:
        pass  # python-dotenv not installed — env vars only

if not DEEPSEEK_API_KEY:
    print("⚠️  未检测到 DEEPSEEK_API_KEY 环境变量。")
    print("   请设置后重试：set DEEPSEEK_API_KEY=你的DeepSeek_API_Key")
    print("   或在项目目录创建 .env 文件，写入：DEEPSEEK_API_KEY=你的DeepSeek_API_Key")

# ── LLM parameters ───────────────────────────────────────
LLM_MAX_TOKENS = int(os.environ.get("ZIXUNXIA_LLM_MAX_TOKENS", "8000"))
LLM_TEMPERATURE = float(os.environ.get("ZIXUNXIA_LLM_TEMPERATURE", "0.3"))

# ── Batch limits ─────────────────────────────────────────
MAX_STUDENTS_PER_BATCH = int(os.environ.get("ZIXUNXIA_MAX_STUDENTS", "50"))
MAX_CONCURRENT_STUDENTS = int(os.environ.get("ZIXUNXIA_CONCURRENT", "5"))
SQLITE_CONNECTION_TIMEOUT = float(os.environ.get("ZIXUNXIA_DB_TIMEOUT", "10.0"))

# ── Retry ────────────────────────────────────────────────
LLM_MAX_RETRIES = 2
LLM_RETRY_BASE_DELAY = 1.0  # seconds, exponential backoff
