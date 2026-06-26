"""State type definitions for the LangGraph batch pipeline.

Two state graphs:
- BatchState: The parent orchestrator that fans out to per-student agents.
- StudentState: The per-student agent that runs Prompt0 -> Prompt1 -> Prompt2.
"""

from operator import add
from typing import TypedDict, Annotated, Optional, List, Dict, Any
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class StudentInput(TypedDict, total=False):
    """Input fields for a single student, parsed from CSV/JSON.

    Only 'nickname' is strictly required. All other fields are optional
    and will be passed to the prompts as-is if present.
    """
    nickname: str
    province: str
    subject_category: str        # e.g. 物理类 / 历史类
    score: str                   # String to preserve formatting
    rank: str                    # String to preserve formatting
    consultation_form: str       # 文字 / 语音
    major_interests: str         # 意向大类
    study_willingness: str       # 读研意愿
    city_preference: str         # 城市偏好
    financial_pressure: str      # 经济压力
    family_attitude: str         # 家庭态度
    mbti: Optional[str]
    holland: Optional[str]
    excluded_majors: Optional[str]
    preferred_careers: Optional[str]
    rejected_careers: Optional[str]
    deficit_acceptance: Optional[str]
    target_school_tier: Optional[str]
    clarity_level: Optional[str]
    first_gen_college: Optional[str]
    dimension_priority: Optional[str]
    prompt0_answers: Optional[str]  # Pre-existing answers if available


class StudentState(TypedDict):
    """Per-student agent state, flows through Prompt0 -> Prompt1 -> Prompt2."""
    student: StudentInput
    messages: Annotated[list[BaseMessage], add_messages]

    # Prompt0 outputs
    prompt0_questions: Optional[str]
    prompt0_confidence: Optional[Dict[str, Any]]

    # Prompt1 outputs
    prompt1_sufficient: bool
    prompt1_followup_question: Optional[str]
    prompt1_major_recommendations: Optional[str]
    prompt1_major_names: Optional[List[str]]  # Extracted major names for downstream use

    # Prompt2 outputs
    prompt2_sufficient: bool
    prompt2_followup_question: Optional[str]
    prompt2_city_recommendations: Optional[str]

    # Tracking
    current_step: str           # "prompt0" | "prompt1" | "prompt2" | "done" | "error"
    error_message: Optional[str]
    case_dir: str               # Derived: cases/{nickname}/


class BatchState(TypedDict):
    """Parent orchestrator state."""
    students: List[StudentInput]
    results: Annotated[list, add]   # Accumulated per-student result dicts (list concatenation)
    batch_id: str
    input_file: str
    total: int
    completed: int
    failed: int
    flagged: int
