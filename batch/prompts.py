"""Load and template Prompt0, Prompt1, Prompt2 from AI提示词模板.md.

The template file lives at 知识库/核心方法论/AI提示词模板.md and contains
three sections delimited by '# prompt0', '# prompt1', '# (选用)prompt2'.

This module:
1. Reads the template file once at import
2. Splits into three prompt sections
3. Provides format_*() functions that inject student data and SQLite results
   into the prompt placeholders
"""

import re
from pathlib import Path
from typing import Tuple

from config import PROMPT_TEMPLATE_FILE

# Module-level cache
_PROMPTS: dict[str, str] = {}
_loaded: bool = False


def _load_prompts() -> None:
    """Parse AI提示词模板.md into three prompt sections."""
    global _loaded
    if _loaded:
        return

    if not PROMPT_TEMPLATE_FILE.exists():
        raise FileNotFoundError(
            f"Prompt template file not found: {PROMPT_TEMPLATE_FILE}\n"
            f"Ensure 知识库/核心方法论/AI提示词模板.md exists."
        )

    text = PROMPT_TEMPLATE_FILE.read_text(encoding="utf-8")

    # Split on markdown headers: # prompt0, # prompt1, # (选用)prompt2
    # Note: prompt2 uses full-width parentheses （选用） not half-width
    parts = re.split(r"\n(?=# (?:[（(]选用[）)])?prompt[012])", text)

    for part in parts:
        part = part.strip()
        m = re.match(r"^# (?:[（(]选用[）)])?(prompt[012])", part)
        if m:
            key = m.group(1)
            _PROMPTS[key] = part

    if len(_PROMPTS) < 2:
        raise ValueError(
            f"Failed to parse prompts from {PROMPT_TEMPLATE_FILE}. "
            f"Found sections: {list(_PROMPTS.keys())}. "
            f"Expected at least prompt0 and prompt1."
        )

    _loaded = True


def _split_system_human(prompt_text: str, student_context: str) -> Tuple[str, str]:
    """Split a raw prompt into (system_message, human_message).

    The system message contains the Role, Task, Constraints, and Execution Protocol.
    The human message contains the student data injected into the context placeholder.

    Strategy: Everything before the first explicit student-data marker is system context.
    The student data block is the human message.
    """
    # Remove the header line (# prompt0 / # prompt1 / # （选用）prompt2)
    body = re.sub(r"^# (?:[（(]选用[）)])?prompt[012].*?\n", "", prompt_text, count=1)

    # Strip the "黄框内为prompt" / "中标红部分需替代" meta lines at the very top
    body = re.sub(r"^.*?Role\n", "Role\n", body, count=1, flags=re.DOTALL)

    # The system is the entire body — it contains Role/Task/Constraints/Protocol.
    # The human message is the student data + instruction to execute.
    system = body.strip()

    human = f"""【学生信息收集文档】
{student_context}

请按照上述 Role、Task、Constraints 和 Execution Protocol 执行。"""

    return system, human


# ── Public API ───────────────────────────────────────────

def format_prompt0(student_profile_text: str) -> Tuple[str, str]:
    """Format Prompt0 with student profile data.

    Args:
        student_profile_text: Formatted student profile string.

    Returns:
        (system_message, human_message) tuple ready for LLM call.
    """
    _load_prompts()
    if "prompt0" not in _PROMPTS:
        raise KeyError("prompt0 section not found in template")
    return _split_system_human(_PROMPTS["prompt0"], student_profile_text)


def format_prompt1(
    student_profile_text: str,
    prompt0_qa_text: str,
    sqlite_data_text: str,
) -> Tuple[str, str]:
    """Format Prompt1 with student data, Prompt0 Q&A, and SQLite results.

    Args:
        student_profile_text: Formatted student profile.
        prompt0_qa_text: Questions from Prompt0 + student answers.
        sqlite_data_text: Pre-fetched SQLite data formatted as reference.

    Returns:
        (system_message, human_message) tuple.
    """
    _load_prompts()
    if "prompt1" not in _PROMPTS:
        raise KeyError("prompt1 section not found in template")

    system, _ = _split_system_human(_PROMPTS["prompt1"], student_profile_text)

    human = f"""【原信息收集文档】
{student_profile_text}

【Prompt0 信息确认题目与学生原题原答】
{prompt0_qa_text}

【知识库数据 — 候选专业详情】
{sqlite_data_text}

【咨询侠补充观察】
暂无（批量处理模式）

请按照上述 Role、Task、Constraints 和 Execution Protocol 执行。"""

    return system, human


def format_prompt2(
    student_profile_text: str,
    prompt0_qa_text: str,
    prompt1_output_text: str,
    sqlite_city_data_text: str,
) -> Tuple[str, str]:
    """Format Prompt2 with student data, Prompt0 Q&A, Prompt1 output, and city SQLite data.

    Args:
        student_profile_text: Formatted student profile.
        prompt0_qa_text: Questions from Prompt0 + student answers.
        prompt1_output_text: Full Prompt1 major recommendation output.
        sqlite_city_data_text: Pre-fetched city/industry SQLite data.

    Returns:
        (system_message, human_message) tuple.
    """
    _load_prompts()
    prompt_key = "prompt2" if "prompt2" in _PROMPTS else "prompt2"
    if prompt_key not in _PROMPTS:
        # Prompt2 is optional — return empty if not defined
        return "", ""

    system, _ = _split_system_human(_PROMPTS[prompt_key], student_profile_text)

    human = f"""【原信息收集文档】
{student_profile_text}

【Prompt0 信息确认题目与学生原题原答】
{prompt0_qa_text}

【Prompt1 完整专业推荐文档】
{prompt1_output_text}

【知识库数据 — 城市产业匹配】
{sqlite_city_data_text}

【咨询侠补充观察】
暂无（批量处理模式）

请按照上述 Role、Task、Constraints 和 Execution Protocol 执行。"""

    return system, human


def get_prompt0_raw() -> str:
    """Return the raw Prompt0 template text (for debugging)."""
    _load_prompts()
    return _PROMPTS.get("prompt0", "")


def get_prompt1_raw() -> str:
    """Return the raw Prompt1 template text (for debugging)."""
    _load_prompts()
    return _PROMPTS.get("prompt1", "")


def get_prompt2_raw() -> str:
    """Return the raw Prompt2 template text (for debugging)."""
    _load_prompts()
    return _PROMPTS.get("prompt2", "")
