"""CSV/JSON/TXT batch input parsing and validation.

Supports three input formats:
1. CSV with a header row matching StudentInput field names
2. JSON array of objects matching StudentInput field names
3. Plain text — each line is one student: nickname key=value key=value ...

Required field: nickname
All other fields are optional.
"""

import csv
import json
from pathlib import Path
from typing import List, Optional

from config import MAX_STUDENTS_PER_BATCH, SKILL_DIR
from state import StudentInput


# All recognized fields and their default values
_FIELD_DEFAULTS: dict[str, str] = {
    "nickname": "", "province": "", "subject_category": "",
    "score": "", "rank": "", "consultation_form": "",
    "major_interests": "", "study_willingness": "",
    "city_preference": "", "financial_pressure": "",
    "family_attitude": "", "mbti": "", "holland": "",
    "excluded_majors": "", "preferred_careers": "",
    "rejected_careers": "", "deficit_acceptance": "",
    "target_school_tier": "", "clarity_level": "",
    "first_gen_college": "", "dimension_priority": "",
    "prompt0_answers": "",
}


def parse_input_file(file_path: str) -> List[StudentInput]:
    """Parse a CSV/JSON/TXT file into a list of StudentInput dicts.

    Plain text (.txt) or text content is auto-detected: each non-empty line
    is one student with space-delimited fields: nickname key=value key=value ...
    """
    path = Path(file_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        students = _parse_csv(path)
    elif suffix == ".json":
        students = _parse_json(path)
    elif suffix in (".txt", ""):
        students = _parse_plain_text(path)
    else:
        raise ValueError(f"Unsupported format: {suffix}. Expected .csv, .json, or .txt")
    if not students:
        raise ValueError(f"No valid student records found in {path}")
    if len(students) > MAX_STUDENTS_PER_BATCH:
        raise ValueError(
            f"Batch size {len(students)} exceeds limit {MAX_STUDENTS_PER_BATCH}."
        )
    return students


def _parse_csv(path: Path) -> List[StudentInput]:
    """Parse CSV with header row."""
    students: List[StudentInput] = []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            student = _row_to_student(row)
            if student:
                students.append(student)
    return students


def _parse_json(path: Path) -> List[StudentInput]:
    """Parse JSON array of objects."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("JSON input must be an array of student objects")
    students: List[StudentInput] = []
    for obj in data:
        if isinstance(obj, dict):
            student = _row_to_student(obj)
            if student:
                students.append(student)
    return students


def _parse_plain_text(path: Path) -> List[StudentInput]:
    """Parse space-delimited plain text. One student per non-empty line.

    Format: nickname key1=value1 key2=value2 ...
    Example: 张三 province=广东 score=580 major_interests=自动化

    Also supports Chinese colon variants like 省份：广东.
    """
    text = path.read_text(encoding="utf-8-sig")
    students: List[StudentInput] = []
    # Chinese label to field key mapping
    cn_map = {
        "省份": "province", "科类": "subject_category", "分数": "score",
        "省排": "rank", "意向": "major_interests", "意向大类": "major_interests",
        "读研": "study_willingness", "读研意愿": "study_willingness",
        "城市": "city_preference", "城市偏好": "city_preference",
        "经济": "financial_pressure", "经济压力": "financial_pressure",
        "家庭": "family_attitude", "家庭态度": "family_attitude",
        "mbti": "mbti", "MBTI": "mbti", "霍兰德": "holland",
        "排除": "excluded_majors", "排除专业": "excluded_majors",
        "院校层次": "target_school_tier", "优先级": "dimension_priority",
        "第一代": "first_gen_college", "亏分": "deficit_acceptance",
        "咨询形式": "consultation_form",
    }
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        row = {}
        tokens = line.split()
        nickname = tokens[0] if tokens else ""
        row["nickname"] = nickname
        for token in tokens[1:]:
            if "=" in token:
                key, _, value = token.partition("=")
                key = key.strip().lower()
                value = value.strip().strip("\"").strip("'")
                if key in _FIELD_DEFAULTS:
                    row[key] = value
            elif "：" in token:
                key, _, value = token.partition("：")
                key = key.strip()
                value = value.strip()
                field_key = cn_map.get(key, key.lower())
                if field_key in _FIELD_DEFAULTS:
                    row[field_key] = value
        student = _row_to_student(row)
        if student:
            students.append(student)
    if not students:
        raise ValueError(
            "No valid student records found in plain text. "
            "Expected format: nickname key=value key=value ..."
        )
    if len(students) > MAX_STUDENTS_PER_BATCH:
        raise ValueError(
            f"Batch size {len(students)} exceeds limit {MAX_STUDENTS_PER_BATCH}."
        )
    return students


def _row_to_student(row: dict) -> Optional[StudentInput]:
    """Convert raw dict to validated StudentInput. Returns None if no nickname."""
    nickname = (row.get("nickname") or "").strip()
    if not nickname:
        return None
    student: StudentInput = StudentInput(nickname=nickname)
    for field, default in _FIELD_DEFAULTS.items():
        if field == "nickname":
            continue
        value = row.get(field, "")
        if value is None:
            value = ""
        student[field] = str(value).strip()  # type: ignore
    return student


def validate_student(student: StudentInput) -> List[str]:
    """Validate a student record. Returns list of non-blocking warnings."""
    warnings: List[str] = []
    if not student.get("province"):
        warnings.append(f"[{student['nickname']}] missing province")
    if not student.get("major_interests"):
        warnings.append(f"[{student['nickname']}] missing major interests")
    if not student.get("score") and not student.get("rank"):
        warnings.append(f"[{student['nickname']}] missing score and rank")
    return warnings


def format_student_profile(student: StudentInput) -> str:
    """Format a StudentInput into markdown profile text for prompts."""
    lines = ["## 基本信息", ""]
    field_labels = {
        "nickname": "昵称", "province": "省份",
        "subject_category": "科类", "score": "分数", "rank": "省排",
        "consultation_form": "咨询形式", "major_interests": "意向大类",
        "study_willingness": "读研意愿", "city_preference": "城市偏好",
        "financial_pressure": "经济压力", "family_attitude": "家庭态度",
        "mbti": "MBTI", "holland": "霍兰德",
        "excluded_majors": "排除专业", "preferred_careers": "偏好职业",
        "rejected_careers": "排斥职业", "deficit_acceptance": "亏分接受度",
        "target_school_tier": "院校层次", "clarity_level": "明确目标程度",
        "first_gen_college": "第一代大学生", "dimension_priority": "五维度优先级",
    }
    lines.append("| 字段 | 值 |")
    lines.append("|------|-----|")
    for field, label in field_labels.items():
        value = student.get(field, "")
        if value:
            lines.append(f"| {label} | {value} |")
    lines.append("")
    lines.append("## 关键约束")
    constraints = []
    if student.get("study_willingness"):
        constraints.append(f"- 读研意愿：{student['study_willingness']}")
    if student.get("city_preference"):
        constraints.append(f"- 城市偏好：{student['city_preference']}")
    if student.get("financial_pressure"):
        constraints.append(f"- 经济压力：{student['financial_pressure']}")
    if student.get("family_attitude"):
        constraints.append(f"- 家庭态度：{student['family_attitude']}")
    if student.get("excluded_majors"):
        constraints.append(f"- 排除专业：{student['excluded_majors']}")
    if constraints:
        lines.extend(constraints)
    return "\n".join(lines)
