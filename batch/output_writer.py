"""File system output writer for batch processing.

Writes to the same cases/{nickname}/ directory structure as the
interactive SKILL.md mode, ensuring downstream compatibility with
DOCX export and online document creation tools.
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

from config import CASES_DIR

# China timezone
CST = timezone(timedelta(hours=8))


def _ts() -> str:
    """ISO timestamp in China timezone."""
    return datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def case_dir_path(nickname: str) -> Path:
    return CASES_DIR / nickname


def ensure_case_dir(nickname: str) -> Path:
    path = case_dir_path(nickname)
    path.mkdir(parents=True, exist_ok=True)
    return path


# ── MD Archive ───────────────────────────────────────────

def write_archive_header(nickname: str, student_profile_text: str) -> Path:
    """Create the student's main archive MD file."""
    ensure_case_dir(nickname)
    archive_path = case_dir_path(nickname) / f"{nickname}.md"
    content = f"""# {nickname} -- 咨询档案

> 由批量分析系统生成 | 生成时间：{_ts()}

{student_profile_text}

---

## 咨询前

### 信息确认题目包

（待生成）

### 腾讯问卷链接

### 学生作答记录

### 专业推荐文档

（待生成）

### 城市推荐文档

（待生成）

---

## 咨询中 -- 进度

（待开始）

---

## 咨询后

### 复盘报告

（待生成）
"""
    archive_path.write_text(content, encoding="utf-8")
    return archive_path


def append_to_archive(nickname: str, section: str, content: str) -> None:
    """Append content to a section in the student's archive."""
    archive_path = case_dir_path(nickname) / f"{nickname}.md"
    if not archive_path.exists():
        write_archive_header(nickname, f"# {nickname}\n\n批量导入")

    text = archive_path.read_text(encoding="utf-8")
    section_map = {
        "题目包": ("### 信息确认题目包", "### 腾讯问卷链接"),
        "专业推荐": ("### 专业推荐文档", "### 城市推荐文档"),
        "城市推荐": ("### 城市推荐文档", "---"),
    }
    if section not in section_map:
        raise ValueError(f"Unknown section: {section}")
    start_marker, end_marker = section_map[section]
    start_idx = text.find(start_marker)
    end_idx = text.find(end_marker, start_idx + len(start_marker))
    if start_idx >= 0 and end_idx > start_idx:
        before = text[:start_idx + len(start_marker)]
        after = text[end_idx:]
        content_block = f"\n\n{content.strip()}\n\n"
        archive_path.write_text((before + content_block + after), encoding="utf-8")
    else:
        text += f"\n\n{start_marker}\n\n{content.strip()}\n"
        archive_path.write_text(text, encoding="utf-8")


def write_standalone_md(nickname: str, doc_type: str, content: str) -> Path:
    """Write standalone .md for DOCX export."""
    ensure_case_dir(nickname)
    type_map = {
        "专业推荐": f"{nickname}-专业推荐.md",
        "城市推荐": f"{nickname}-城市推荐.md",
    }
    filename = type_map.get(doc_type, f"{nickname}-{doc_type}.md")
    file_path = case_dir_path(nickname) / filename
    file_path.write_text(content.strip(), encoding="utf-8")
    return file_path


# ── Goal State ───────────────────────────────────────────

def init_goal_state(nickname: str) -> Dict[str, Any]:
    """Initialize goal_state.json matching interactive mode schema."""
    return {
        "phase": "pre_consultation",
        "phase_history": [],
        "turn_count": 0,
        "auto_advance": False,
        "goals": {
            "pre_consultation": {
                "candidate_profile_complete": False,
                "info_gap_covered": False,
                "candidate_answers_received": False,
                "major_recommendations_generated": False,
                "city_recommendations_generated": False,
                "outbound_done": False,
            },
            "in_consultation": {
                "opening_done": False,
                "five_dimensions": {
                    "排除排序": False, "培养计划": False,
                    "学校要求": False, "深造要求": False,
                    "硬性要求": False, "赚钱能力": False,
                },
                "dimension_confirmation": False,
                "city_guidance_done": False,
                "school_guidance_done": False,
                "all_questions_addressed": False,
                "summary_given": False,
            },
            "post_consultation": {
                "transcript_collected": False,
                "review_generated": False,
            },
        },
        "last_updated": _ts(),
        "interrupted_at": None,
    }


def read_goal_state(nickname: str) -> Optional[Dict[str, Any]]:
    path = case_dir_path(nickname) / "goal_state.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_goal_state(nickname: str, state: Dict[str, Any]) -> Path:
    ensure_case_dir(nickname)
    state["last_updated"] = _ts()
    path = case_dir_path(nickname) / "goal_state.json"
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def update_pre_consultation_goal(nickname: str, goal_key: str, value: bool) -> Dict[str, Any]:
    """Update a single pre_consultation goal flag."""
    state = read_goal_state(nickname)
    if state is None:
        state = init_goal_state(nickname)
    state["goals"]["pre_consultation"][goal_key] = value
    write_goal_state(nickname, state)
    return state


def mark_student_complete(nickname: str) -> Dict[str, Any]:
    """Mark all pre_consultation goals as done."""
    state = read_goal_state(nickname)
    if state is None:
        state = init_goal_state(nickname)
    pc = state["goals"]["pre_consultation"]
    for k in pc:
        pc[k] = True
    write_goal_state(nickname, state)
    return state


def write_followup_txt(nickname: str, student_result: dict) -> Path:
    """Generate 跟进.txt for flagged students."""
    ensure_case_dir(nickname)
    path = case_dir_path(nickname) / "跟进.txt"
    lines = [f"# {nickname} — 需人工跟进", "", f"生成时间：{_ts()}", ""]
    if student_result.get("prompt1_sufficient") is False:
        lines.append("## Prompt1 专业推荐 — 信息不足")
        lines.append("")
        if student_result.get("prompt1_followup_question"):
            lines.append(f"建议补问：{student_result['prompt1_followup_question']}")
        lines.append("")
    if student_result.get("prompt2_sufficient") is False:
        lines.append("## Prompt2 城市推荐 — 信息不足")
        lines.append("")
        if student_result.get("prompt2_followup_question"):
            lines.append(f"建议补问：{student_result['prompt2_followup_question']}")
        lines.append("")
    if student_result.get("error_message"):
        lines.append(f"## 处理错误：{student_result['error_message']}")
        lines.append("")
    lines.append("---")
    lines.append("在 Claude Code 中输入 @咨询侠:切换:{nickname} 然后手动跟进。")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_error_log(nickname: str, step: str, error_message: str) -> Path:
    ensure_case_dir(nickname)
    error_path = case_dir_path(nickname) / "_error.json"
    error_path.write_text(
        json.dumps({
            "nickname": nickname, "step": step,
            "error": error_message, "timestamp": _ts(),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return error_path


# ── Batch Summary ────────────────────────────────────────

def write_batch_summary(results: list, batch_id: str, input_file: str) -> Path:
    """Write batch summary markdown report."""
    total = len(results)
    succeeded = sum(1 for r in results if r.get("status") == "success")
    failed = sum(1 for r in results if r.get("status") == "error")
    flagged = sum(1 for r in results if r.get("flagged"))
    timestamp = datetime.now(CST).strftime("%Y-%m-%dT%H%M%S")
    summary_path = CASES_DIR / f"_batch_summary_{timestamp}.md"

    lines = [
        f"# 批量分析报告 — {batch_id}",
        "",
        f"- **生成时间**：{_ts()}",
        f"- **输入文件**：{input_file}",
        f"- **考生总数**：{total} | **成功**：{succeeded} | **失败**：{failed} | **需跟进**：{flagged}",
        "",
        "## 考生状态",
        "",
        "| 昵称 | 状态 | Prompt0 | Prompt1 | Prompt2 | 推荐专业 | 标记 |",
        "|------|------|---------|---------|---------|----------|------|",
    ]

    for r in results:
        nickname = r.get("nickname", "?")
        status = r.get("status", "?")
        p0 = "OK" if r.get("prompt0_done") else "--"
        p1 = "OK" if r.get("prompt1_done") else "--"
        p2 = "OK" if r.get("prompt2_done") else "--"
        majors = ", ".join(r.get("prompt1_major_names", [])[:3]) or "-"
        flag_text = ""
        if r.get("flagged"):
            flag_text = "NEED_FOLLOWUP"
        if r.get("error_message"):
            flag_text += f" ERR: {r['error_message'][:30]}"
        lines.append(f"| {nickname} | {status} | {p0} | {p1} | {p2} | {majors} | {flag_text} |")

    # Students needing follow-up
    followups = [r for r in results if r.get("flagged")]
    if followups:
        lines.extend(["", "## 需人工跟进", ""])
        for r in followups:
            lines.append(f"### {r['nickname']}")
            if r.get("prompt1_followup_question"):
                lines.append(f"- 建议补问：{r['prompt1_followup_question']}")
            if r.get("error_message"):
                lines.append(f"- 错误：{r['error_message']}")
            lines.append("")

    # Errors
    errors = [r for r in results if r.get("status") == "error"]
    if errors:
        lines.extend(["", "## 处理失败", ""])
        for r in errors:
            lines.append(f"- **{r['nickname']}**：{r.get('error_message', '?')}")

    summary_path.write_text("\n".join(lines), encoding="utf-8")
    return summary_path
