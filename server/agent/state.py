"""
StudentState Schema (LangGraph Workflow State)
==============================================
Defines the shared state dictionary passed across all nodes in the LangGraph workflow:
1. Adaptive Assessment Agent Node
2. ML Engine Service Tool
3. Combined Gap Analysis & Career Agent Node
4. Combined Content & Regional Tutor Agent Node
5. Planning Agent Node
"""

import operator
from typing import TypedDict, List, Dict, Any, Optional, Annotated


class QuestionItem(TypedDict, total=False):
    """Represents a diagnostic question and its student submission metadata."""
    id: str
    concept_id: str
    question: str
    options: List[str]
    correct_answer: str
    explanation: str
    difficulty: float
    discrimination: float
    question_type: str  # "MCQ" | "Scenario-based" | "Coding"
    student_answer: Optional[str]
    is_correct: Optional[bool]
    response_time_sec: Optional[float]
    source: str  # "gemini" | "curriculum" | "fallback"


class PrioritizedGap(TypedDict, total=False):
    """Represents a diagnosed skill deficit linked to its prerequisite root cause."""
    domain: str                           # e.g., "SQL"
    career_skill: str                     # e.g., "SQL Joins"
    required_benchmark: float             # e.g., 0.75
    current_score: float                  # e.g., 0.43
    gap_size: float                       # e.g., 0.32
    severity: str                         # "critical" | "moderate" | "minor"
    priority_score: float                 # weighted gap priority
    root_cause_concept: Optional[str]     # e.g., "relational_keys"
    prerequisite_path: List[str]          # e.g., ["set_theory", "relational_keys"]


class GroundedResource(TypedDict, total=False):
    """Educational document or video retrieved via RAG for student study."""
    id: str
    concept_id: str
    title: str
    resource_type: str                    # "video" | "article" | "interactive_exercise" | "cheat_sheet"
    url_or_ref: str
    content_snippet: str
    estimated_minutes: int
    difficulty: str
    tags: List[str]
    similarity_score: Optional[float]


class DailyPlanItem(TypedDict, total=False):
    """A single day's structured curriculum in the 7-day adaptive roadmap."""
    day: int
    focus_topic: str
    duration_minutes: int
    learning_objectives: List[str]
    activities: List[Dict[str, Any]]
    recommended_resources: List[GroundedResource]
    completion_status: str                # "pending" | "completed"


class StudentState(TypedDict, total=False):
    """
    Central shared state object passed through the entire LangGraph workflow.
    Every agent node reads from this dictionary and returns an updated subset.
    """

    # -------------------------------------------------------------------------
    # 1. Student Profile & Onboarding Metadata
    # -------------------------------------------------------------------------
    student_id: str
    subject: str                          # e.g., "Data Analytics"
    target_career: str                    # e.g., "Data Analyst"
    primary_language: str                 # "English" | "Hindi" | "Marathi"
    language: str                         # Added to map primary_language directly for prompts
    secondary_language: Optional[str]
    time_commitment_hrs: int              # e.g., 7 hrs/week
    time_per_day_mins: int                # e.g., 60 mins/day
    daily_time_minutes: int               # Added to map time_per_day_mins directly for prompts
    perceived_level: str                  # "Beginner" | "Intermediate" | "Advanced"
    preferred_question_types: List[str]   # ["MCQ", "Scenario-based"]
    prior_exposure: List[str]

    # -------------------------------------------------------------------------
    # 2. Adaptive Assessment & ML Tracking
    # -------------------------------------------------------------------------
    current_concept_id: str               # Concept currently under evaluation
    current_question: Optional[QuestionItem]
    
    # LangGraph List Reducers (operator.add) ensure appending rather than overwriting
    assessment_questions: Annotated[List[QuestionItem], operator.add]
    raw_responses: Annotated[List[Dict[str, Any]], operator.add]
    asked_question_ids: Annotated[List[str], operator.add]
    
    ml_profile: Dict[str, Any]            # Serialized StudentMLProfile (theta, struggle)
    concept_mastery: Dict[str, float]     # Top-Level Field for immediate access
    domain_scores: Dict[str, float]       # Macro-level scores: e.g. {"SQL": 0.43, "Python": 0.82}
    is_assessment_complete: bool
    current_step: int                     # e.g., question 1 of 8
    last_submitted_question_id: Optional[str]
    last_submission_response_time_sec: Optional[float]
    assessment_action: Optional[str]
    pause_after_evaluation: bool

    # -------------------------------------------------------------------------
    # 3. Gap Analysis & Career Mapping (Combined Node)
    # -------------------------------------------------------------------------
    career_readiness_score: float         # 0.0% to 100.0%
    is_career_ready: bool
    priority_gaps: List[PrioritizedGap]   # Prioritized gaps with root causes
    alternative_roles: List[Dict[str, Any]] # Ranked alternative careers

    # -------------------------------------------------------------------------
    # 4. Content & Regional Tutoring (Combined Node)
    # -------------------------------------------------------------------------
    grounded_resources: Annotated[List[GroundedResource], operator.add]
    tutor_explanation_localized: str      # Explanation in Marathi / Hindi / English
    tutor_chat_history: List[Dict[str, str]] # bounded [{'role': 'user'|'assistant', 'content': '...'}]
    tutor_action: Optional[str]

    # -------------------------------------------------------------------------
    # 5. Personalized Study Planning
    # -------------------------------------------------------------------------
    study_plan: List[DailyPlanItem]       # 7-day time-boxed roadmap
    plan_summary: str
    next_action: str                      # "assess" | "remediate" | "advance" | "tutor" | "complete"
    errors: Annotated[List[str], operator.add]

