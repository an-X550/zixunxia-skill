"""LangGraph node functions for the batch pipeline.

Each node receives its state dict and returns an updated state dict.
LLM calls go through DeepSeek API with retry logic.
SQLite data is pre-fetched before LLM calls.
"""

import asyncio
import re
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

from config import (
    DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL,
    LLM_MAX_TOKENS, LLM_TEMPERATURE, LLM_MAX_RETRIES, LLM_RETRY_BASE_DELAY,
)
from state import StudentState, BatchState, StudentInput

import output_writer as ow
import prompts as pm
import data_loader as dl
from db_adapter import (
    search_majors, query_major_detail, query_major_branches,
    get_categories, get_city_tiers, get_city_types, get_major_city_match,
    query_school_by_major, query_city_industry,
)

CST = timezone(timedelta(hours=8))


# ── LLM Helpers ────────────────────────────────────────

def _get_llm():
    """Lazy-load DeepSeek chat model."""
    from langchain_deepseek import ChatDeepSeek
    return ChatDeepSeek(
        model=DEEPSEEK_MODEL, api_base=DEEPSEEK_BASE_URL,
        api_key=DEEPSEEK_API_KEY, temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS, request_timeout=120,
    )


def _is_retryable(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(p in msg for p in ["rate limit", "timeout", "503", "502", "429", "connection"])


def _call_llm(system: str, human: str) -> str:
    """Call DeepSeek with retry."""
    from langchain_core.messages import SystemMessage, HumanMessage
    llm = _get_llm()
    messages = [SystemMessage(content=system), HumanMessage(content=human)]
    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            return llm.invoke(messages).content
        except Exception as e:
            if attempt < LLM_MAX_RETRIES and _is_retryable(e):
                time.sleep(LLM_RETRY_BASE_DELAY * (2 ** attempt))
                continue
            raise
    raise RuntimeError("LLM call failed after all retries")


# ── SQLite Data Formatters ─────────────────────────────

def _format_major_sqlite_data(major_interests: str, excluded_majors: str, study_willingness: str) -> str:
    """Query SQLite and format major data as prompt context."""
    lines = ["## 候选专业详情", ""]
    if not major_interests:
        cats = get_categories()
        if cats:
            lines.append("### 学科门类")
            for c in cats:
                lines.append(f"- {c['name']}：{c['major_count']}个专业")
        return "\n".join(lines)

    keywords = re.findall(r'[一-鿿]{2,}', major_interests)
    search_terms = keywords[:3]

    all_results = []
    seen = set()
    for term in search_terms:
        for r in search_majors(keyword=term):
            if r["name"] not in seen:
                seen.add(r["name"])
                all_results.append(r)

    if len(all_results) < 3:
        for r in search_majors():
            if r["name"] not in seen:
                seen.add(r["name"])
                all_results.append(r)

    excluded_list = []
    if excluded_majors:
        excluded_list = [m.strip() for m in re.split(r'[、,，]', excluded_majors) if m.strip()]

    count = 0
    for c in all_results[:8]:
        name = c["name"]
        if name in excluded_list:
            continue
        if count >= 5:
            break

        card = query_major_detail(name)
        if not card:
            continue

        lines.append(f"### {name}")
        lines.append(f"- 门类：{card.get('category', '?')}")
        lines.append(f"- 培养计划：{card.get('training_plan', '')[:200]}")
        lines.append(f"- 就业前景：{card.get('employment_outlook', '')[:200]}")
        lines.append(f"- 深造需求：{card.get('further_study', '')[:100]}")
        lines.append(f"- 院校依赖：{card.get('school_dependency', '')}")
        lines.append(f"- 典型方向：{card.get('typical_directions', '')[:200]}")

        school_data = query_school_by_major(name)
        if school_data and school_data.get("results"):
            top = [f"{s['school']}({s['tier']})" for s in school_data["results"][:5]]
            lines.append(f"- 强校参考：{', '.join(top)}")

        branches = query_major_branches(name)
        if branches:
            lines.append(f"- 内部分叉({len(branches)}个)：")
            for b in branches[:3]:
                lines.append(f"  - {b.get('branch_name', '?')}：{b.get('career_path', '')[:80]}")

        count += 1
        lines.append("")

    if count == 0:
        lines.append("（未找到匹配专业）")
    return "\n".join(lines)


def _format_city_sqlite_data(province: str, major_names: List[str]) -> str:
    """Query SQLite and format city/industry data."""
    lines = ["## 城市产业参考数据", ""]

    tiers = get_city_tiers()
    if tiers:
        lines.append("### 城市层级")
        for t in tiers:
            lines.append(f"- {t['tier_name']}：{t.get('features', '')[:100]}")
        lines.append("")

    match_rules = get_major_city_match()
    relevant = [r for r in match_rules if any(mn in r.get('major_direction', '') for mn in major_names)]
    if relevant:
        lines.append("### 专业-城市匹配")
        for rm in relevant[:5]:
            lines.append(f"- {rm['major_direction']} -> {rm.get('preferred_city_feature', '')} ({rm.get('representative_cities', '')})")
        lines.append("")

    if province:
        city_data = query_city_industry(province)
        if not city_data:
            short = province.replace("省", "").replace("市", "").replace("自治区", "")
            city_data = query_city_industry(short)
        if city_data:
            lines.append(f"### {province}产业")
            data = city_data.get("data", {})
            for k, v in data.items():
                if v and k not in ("province_name",):
                    lines.append(f"- {k}：{str(v)[:200]}")
        else:
            lines.append(f"（未找到{province}产业数据）")

    return "\n".join(lines)


# ── Per-Student Nodes ──────────────────────────────────

def prompt0_node(state: StudentState) -> dict:
    """Generate Prompt0 question package."""
    student = state["student"]
    nickname = student["nickname"]
    profile_text = dl.format_student_profile(student)
    try:
        system, human = pm.format_prompt0(profile_text)
        response = _call_llm(system, human)
        ow.append_to_archive(nickname, "题目包", response)
        ow.update_pre_consultation_goal(nickname, "info_gap_covered", True)
        return {
            "prompt0_questions": response,
            "prompt0_confidence": {"parsed": True},
            "current_step": "prompt1",
        }
    except Exception as e:
        ow.write_error_log(nickname, "prompt0", str(e))
        return {"current_step": "error", "error_message": f"prompt0: {e}"}


def prompt1_node(state: StudentState) -> dict:
    """Generate major recommendations."""
    student = state["student"]
    nickname = student["nickname"]
    profile_text = dl.format_student_profile(student)
    try:
        sqlite_data = _format_major_sqlite_data(
            student.get("major_interests", ""),
            student.get("excluded_majors", ""),
            student.get("study_willingness", ""),
        )
        prompt0_qa = state.get("prompt0_questions", "")
        system, human = pm.format_prompt1(profile_text, prompt0_qa, sqlite_data)
        response = _call_llm(system, human)

        # ── Sufficiency detection ──────────────────────
        sufficient = True
        followup = None

        # Patterns that indicate the LLM is asking a question, not recommending
        insufficient_patterns = [
            r'向咨询侠追问',
            r'需要(?:(?:进一步|再)|确认.{0,8}(?:关键|重要|一[下个]))',
            r'尚?不足以?(?:支撑|生成|推荐|判断|输出)',
            r'无法(?:生成|推荐|判断|直接输出)',
            r'信息缺口',
            r'关键.{0,5}信息.{0,10}(?:不足|缺口|确认|补充|需要)',
        ]
        for pat in insufficient_patterns:
            if re.search(pat, response):
                sufficient = False
                break

        # Heuristic: if response ends with question UI (【单选】etc), it's asking, not recommending
        if sufficient:
            tail = response[-600:]
            if re.search(r'【[单多判排]选', tail):
                if re.search(r'(?:请将|请咨询侠|发给.{2,4}同学|请选择|请告诉|请你?根?据)', tail):
                    sufficient = False

        # Extract follow-up question if insufficient
        if not sufficient:
            q_match = re.search(r'(?:追问|问题|题目)[：:]\s*(.+?)(?:\n\n|\n【|$)', response)
            if not q_match:
                q_match = re.search(r'【[单多判排]选[题]?】[^\n]*?\n(.+?)(?:\n[A-G]\.|\n- [A-G]|\n□)', response)
            if q_match:
                followup = q_match.group(1).strip()[:200]

        # ── Major name extraction ──────────────────────
        major_names = []
        # Pattern 1: **专业名称**：XXX or **推荐专业**：XXX
        for m in re.finditer(r'\*\*(?:专业名称|推荐专业)\*\*[：:]\s*([一-鿿\w]{2,12}(?:工程|科学|技术|医学|药学|法学|管理|经济|金融|会计)?)', response):
            name = m.group(1).strip()
            if name not in major_names and len(name) >= 2:
                major_names.append(name)
        # Pattern 2: heading-style "### 数字. 专业名"
        for m in re.finditer(r'###?\s*\d+[.、)\s]\s*([一-鿿]{2,8}(?:工程|科学|技术|医学|药学|法学|管理|经济)?)', response):
            name = m.group(1).strip()
            if name not in major_names and len(name) >= 2:
                major_names.append(name)
        # Pattern 3: bullet list "- **专业名**"
        for m in re.finditer(r'[-*]\s*\*\*([一-鿿]{2,8}(?:工程|科学|技术|医学|药学|法学|管理|经济)?)\*\*', response):
            name = m.group(1).strip()
            if name not in major_names and len(name) >= 2:
                major_names.append(name)

        ow.append_to_archive(nickname, "专业推荐", response)
        ow.write_standalone_md(nickname, "专业推荐", response)
        ow.update_pre_consultation_goal(nickname, "major_recommendations_generated", True)

        return {
            "prompt1_major_recommendations": response,
            "prompt1_major_names": major_names[:5],
            "prompt1_sufficient": sufficient,
            "prompt1_followup_question": followup,
            "current_step": "prompt2" if sufficient else "finalize",
        }
    except Exception as e:
        ow.write_error_log(nickname, "prompt1", str(e))
        return {"current_step": "error", "error_message": f"prompt1: {e}"}


def prompt2_node(state: StudentState) -> dict:
    """Generate city recommendations."""
    student = state["student"]
    nickname = student["nickname"]
    profile_text = dl.format_student_profile(student)
    try:
        sqlite_city = _format_city_sqlite_data(
            student.get("province", ""),
            state.get("prompt1_major_names", []),
        )
        system, human = pm.format_prompt2(
            profile_text, state.get("prompt0_questions", ""),
            state.get("prompt1_major_recommendations", ""), sqlite_city,
        )
        if not system:
            ow.update_pre_consultation_goal(nickname, "city_recommendations_generated", True)
            return {"prompt2_city_recommendations": "（跳过）", "prompt2_sufficient": True, "current_step": "finalize"}

        response = _call_llm(system, human)

        sufficient = True
        followup = None

        insufficient_patterns = [
            r'向咨询侠追问',
            r'需要(?:(?:进一步|再)|确认.{0,8}(?:关键|重要|一[下个]))',
            r'尚?不足以?(?:支撑|生成|推荐|判断|输出)',
            r'无法(?:生成|推荐|判断|直接输出)',
            r'信息缺口',
            r'关键.{0,5}信息.{0,10}(?:不足|缺口|确认|补充|需要)',
        ]
        for pat in insufficient_patterns:
            if re.search(pat, response):
                sufficient = False
                break

        if sufficient:
            tail = response[-600:]
            if re.search(r'【[单多判排]选', tail):
                if re.search(r'(?:请将|请咨询侠|发给.{2,4}同学|请选择|请告诉|请你?根?据)', tail):
                    sufficient = False

        if not sufficient:
            q_match = re.search(r'(?:追问|问题|题目)[：:]\s*(.+?)(?:\n\n|\n【|$)', response)
            if not q_match:
                q_match = re.search(r'【[单多判排]选[题]?】[^\n]*?\n(.+?)(?:\n[A-G]\.|\n- [A-G]|\n□)', response)
            if q_match:
                followup = q_match.group(1).strip()[:200]

        ow.append_to_archive(nickname, "城市推荐", response)
        ow.write_standalone_md(nickname, "城市推荐", response)
        ow.update_pre_consultation_goal(nickname, "city_recommendations_generated", True)

        return {
            "prompt2_city_recommendations": response,
            "prompt2_sufficient": sufficient,
            "prompt2_followup_question": followup,
            "current_step": "finalize",
        }
    except Exception as e:
        ow.write_error_log(nickname, "prompt2", str(e))
        return {"current_step": "error", "error_message": f"prompt2: {e}"}


def finalize_student_node(state: StudentState) -> dict:
    """Finalize and return result."""
    student = state["student"]
    nickname = student["nickname"]
    try:
        ow.mark_student_complete(nickname)
    except Exception as e:
        ow.write_error_log(nickname, "finalize", str(e))

    flagged = (not state.get("prompt1_sufficient", True)) or (not state.get("prompt2_sufficient", True))
    status = "error" if state.get("current_step") == "error" else "success"

    return {
        "current_step": "done",
        "student_result": {
            "nickname": nickname, "status": status, "flagged": flagged,
            "prompt0_done": bool(state.get("prompt0_questions")),
            "prompt1_done": bool(state.get("prompt1_major_recommendations")),
            "prompt2_done": bool(state.get("prompt2_city_recommendations")),
            "prompt1_major_names": state.get("prompt1_major_names", []),
            "prompt1_sufficient": state.get("prompt1_sufficient", True),
            "prompt1_followup_question": state.get("prompt1_followup_question"),
            "prompt2_sufficient": state.get("prompt2_sufficient", True),
            "prompt2_followup_question": state.get("prompt2_followup_question"),
            "error_message": state.get("error_message"),
        },
    }


# ── Orchestrator Nodes ──────────────────────────────────

def load_batch_node(state: BatchState) -> dict:
    """Parse CSV, initialize per-student directories."""
    students = dl.parse_input_file(state["input_file"])
    batch_id = state.get("batch_id") or f"batch_{uuid.uuid4().hex[:8]}"

    for s in students:
        nickname = s["nickname"]
        ow.ensure_case_dir(nickname)
        archive_path = ow.case_dir_path(nickname) / f"{nickname}.md"
        if not archive_path.exists():
            ow.write_archive_header(nickname, dl.format_student_profile(s))
        gs_path = ow.case_dir_path(nickname) / "goal_state.json"
        if not gs_path.exists():
            ow.write_goal_state(nickname, ow.init_goal_state(nickname))

    return {
        "students": students, "batch_id": batch_id,
        "total": len(students), "completed": 0, "failed": 0, "flagged": 0,
    }


def fan_out_fn(state: BatchState) -> list:
    """Generate Send commands for per-student fan-out."""
    from langgraph.constants import Send
    return [
        Send("student_agent", {
            "student": s, "messages": [],
            "current_step": "prompt0",
            "case_dir": str(ow.case_dir_path(s["nickname"])),
            "prompt0_questions": None, "prompt0_confidence": None,
            "prompt1_sufficient": True, "prompt1_followup_question": None,
            "prompt1_major_recommendations": None, "prompt1_major_names": [],
            "prompt2_sufficient": True, "prompt2_followup_question": None,
            "prompt2_city_recommendations": None,
            "error_message": None,
        })
        for s in state["students"]
    ]


def student_agent_node(state: dict) -> dict:
    """Run full pipeline for one student in isolated state."""
    ss: StudentState = {
        "student": state["student"], "messages": state.get("messages", []),
        "current_step": state.get("current_step", "prompt0"),
        "case_dir": state.get("case_dir", ""),
        "prompt0_questions": state.get("prompt0_questions"),
        "prompt0_confidence": state.get("prompt0_confidence"),
        "prompt1_sufficient": state.get("prompt1_sufficient", True),
        "prompt1_followup_question": state.get("prompt1_followup_question"),
        "prompt1_major_recommendations": state.get("prompt1_major_recommendations"),
        "prompt1_major_names": state.get("prompt1_major_names", []),
        "prompt2_sufficient": state.get("prompt2_sufficient", True),
        "prompt2_followup_question": state.get("prompt2_followup_question"),
        "prompt2_city_recommendations": state.get("prompt2_city_recommendations"),
        "error_message": state.get("error_message"),
    }

    nickname = ss["student"]["nickname"]

    steps = [("prompt0", prompt0_node), ("prompt1", prompt1_node)]
    for step_name, node_fn in steps:
        if ss["current_step"] == "error":
            break
        print(f"  [{nickname}] {step_name} start...")
        ss.update(node_fn(ss))
        print(f"  [{nickname}] {step_name} -> {ss['current_step']}")

    if ss["current_step"] == "prompt2":
        print(f"  [{nickname}] prompt2 start...")
        ss.update(prompt2_node(ss))
        print(f"  [{nickname}] prompt2 -> {ss['current_step']}")

    if ss["current_step"] not in ("error", "done"):
        ss.update(finalize_student_node(ss))

    print(f"  [{nickname}] done. status={ss.get('student_result', {}).get('status', '?')}")
    return {"results": [ss.get("student_result", {})]}


def summarize_batch_node(state: BatchState) -> dict:
    """Collect results and write batch summary."""
    results = state.get("results", [])
    flat = []
    for r in results:
        if isinstance(r, list):
            flat.extend(r)
        elif isinstance(r, dict):
            flat.append(r)
    results = flat

    try:
        summary_path = ow.write_batch_summary(results, state.get("batch_id", "?"), state.get("input_file", "?"))
        print(f"Batch summary: {summary_path}")
    except Exception as e:
        print(f"Warning: summary failed: {e}")

    # Print followup commands and generate 跟进.txt for flagged students
    followups = [r for r in results if r.get("flagged")]
    if followups:
        print("\n═" * 40)
        print(f"📋 以下 {len(followups)} 位考生需要人工跟进：")
        for r in followups:
            nickname = r.get("nickname", "?")
            print(f"  @咨询侠:切换:{nickname}")
            if r.get("prompt1_followup_question"):
                print(f"    Prompt1 补问：{r['prompt1_followup_question'][:100]}")
            if r.get("prompt2_followup_question"):
                print(f"    Prompt2 补问：{r['prompt2_followup_question'][:100]}")
            try:
                ow.write_followup_txt(nickname, r)
                print(f"    跟进.txt 已生成 → cases/{nickname}/跟进.txt")
            except Exception:
                pass
        print("═" * 40 + "\n")

    return {
        "completed": sum(1 for r in results if r.get("status") == "success"),
        "failed": sum(1 for r in results if r.get("status") == "error"),
        "flagged": sum(1 for r in results if r.get("flagged")),
    }
