from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from models.user import User, UserProfile
from routers.auth import get_current_user
from schemas.navigator import (
    StartAssessmentRequest,
    SubmitAnswerRequest,
    AnalyzeAndPlanRequest,
    TutorChatRequest,
)

try:
    from agent.state import StudentState
    from agent.graph import (
        run_next_assessment_step,
        submit_assessment_answer,
        run_remediation_pipeline,
    )
    from agent.nodes.content_tutor import tutor_chat_node
except ImportError:
    from server.agent.state import StudentState
    from server.agent.graph import (
        run_next_assessment_step,
        submit_assessment_answer,
        run_remediation_pipeline,
    )
    from server.agent.nodes.content_tutor import tutor_chat_node


router = APIRouter(
    prefix="/navigator",
    tags=["Navigator Agent"]
)

# In-memory store for active session states (keyed by user_id)
# In production, this can be stored in Redis or database
active_sessions: Dict[int, StudentState] = {}


def _get_or_create_state(user: User, db: Session) -> StudentState:
    if user.id in active_sessions:
        return active_sessions[user.id]

    # Fetch profile preferences if available
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()

    state: StudentState = {
        "student_id": str(user.id),
        "target_career": profile.career_goal if profile and profile.career_goal else "Data Analyst",
        "subject": profile.subject if profile and profile.subject else "Data Analytics",
        "language": profile.primary_language if profile and profile.primary_language else "Marathi",
        "primary_language": profile.primary_language if profile and profile.primary_language else "Marathi",
        "daily_time_minutes": (profile.time_commitment_hrs * 60) if profile and profile.time_commitment_hrs else 60,
        "time_per_day_mins": (profile.time_commitment_hrs * 60) if profile and profile.time_commitment_hrs else 60,
        "perceived_level": profile.perceived_level if profile and profile.perceived_level else "Intermediate",
        "asked_question_ids": [],
        "concept_mastery": {},
        "domain_scores": {},
        "current_step": 0,
        "is_assessment_complete": False,
        "assessment_questions": [],
        "raw_responses": [],
        "grounded_resources": [],
        "tutor_chat_history": [],
        "errors": []
    }
    active_sessions[user.id] = state
    return state


@router.post("/start-assessment")
def start_assessment(
    req: StartAssessmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initializes or resets the adaptive assessment session and returns the first question.
    """
    state = _get_or_create_state(current_user, db)

    # Override with request parameters if provided
    if req.target_career:
        state["target_career"] = req.target_career
    if req.subject:
        state["subject"] = req.subject
    if req.language:
        state["language"] = req.language
        state["primary_language"] = req.language
    if req.daily_time_minutes:
        state["daily_time_minutes"] = req.daily_time_minutes
        state["time_per_day_mins"] = req.daily_time_minutes
    if req.perceived_level:
        state["perceived_level"] = req.perceived_level

    # Reset assessment state
    state["current_step"] = 0
    state["is_assessment_complete"] = False
    state["asked_question_ids"] = []

    # Run assessment node to generate question
    updated_state = run_next_assessment_step(state)
    active_sessions[current_user.id] = updated_state

    return {
        "status": "success",
        "current_step": updated_state.get("current_step", 1),
        "is_complete": updated_state.get("is_assessment_complete", False),
        "question": updated_state.get("current_question")
    }


@router.post("/submit-answer")
def submit_answer(
    req: SubmitAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submits student's answer, updates IRT/BKT ability scores, and serves the next question
    or triggers the remediation pipeline if test is complete.
    """
    state = _get_or_create_state(current_user, db)

    if not state.get("current_question"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active assessment question. Please start an assessment first."
        )

    updated_state = submit_assessment_answer(
        state,
        student_answer=req.student_answer,
        response_time_sec=req.response_time_sec or 20.0
    )

    if not updated_state.get("is_assessment_complete"):
        # Fetch next question
        updated_state = run_next_assessment_step(updated_state)

    active_sessions[current_user.id] = updated_state

    return {
        "status": "success",
        "current_step": updated_state.get("current_step", 1),
        "is_complete": updated_state.get("is_assessment_complete", False),
        "current_question": updated_state.get("current_question"),
        "ml_profile": updated_state.get("ml_profile"),
        "concept_mastery": updated_state.get("concept_mastery"),
        "domain_scores": updated_state.get("domain_scores"),
        "career_readiness_score": updated_state.get("career_readiness_score"),
        "priority_gaps": updated_state.get("priority_gaps"),
        "study_plan": updated_state.get("study_plan"),
        "tutor_explanation_localized": updated_state.get("tutor_explanation_localized")
    }


@router.post("/analyze-and-plan")
def analyze_and_plan(
    req: AnalyzeAndPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Directly runs the post-assessment remediation pipeline (Gap Analysis -> RAG Tutor -> 7-Day Plan).
    """
    state = _get_or_create_state(current_user, db)

    if req.target_career:
        state["target_career"] = req.target_career
    if req.language:
        state["language"] = req.language
        state["primary_language"] = req.language
    if req.daily_time_minutes:
        state["daily_time_minutes"] = req.daily_time_minutes
        state["time_per_day_mins"] = req.daily_time_minutes
    if req.domain_scores:
        state["domain_scores"] = req.domain_scores

    result_state = run_remediation_pipeline(state)
    active_sessions[current_user.id] = result_state

    return {
        "status": "success",
        "career_readiness_score": result_state.get("career_readiness_score"),
        "is_career_ready": result_state.get("is_career_ready"),
        "priority_gaps": result_state.get("priority_gaps"),
        "grounded_resources": result_state.get("grounded_resources"),
        "tutor_explanation_localized": result_state.get("tutor_explanation_localized"),
        "plan_summary": result_state.get("plan_summary"),
        "study_plan": result_state.get("study_plan")
    }


@router.post("/tutor/chat")
def tutor_chat(
    req: TutorChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Interactive Socratic multi-lingual AI Tutor Chat.
    """
    state = _get_or_create_state(current_user, db)
    if req.language:
        state["language"] = req.language

    res = tutor_chat_node(state, student_message=req.message)
    state.update(res)
    active_sessions[current_user.id] = state

    return {
        "status": "success",
        "reply": res.get("latest_tutor_reply"),
        "chat_history": state.get("tutor_chat_history", [])
    }


@router.get("/dashboard-data")
def dashboard_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns live dashboard state including skill mastery, gaps, resources, and 7-day study plan.
    """
    state = _get_or_create_state(current_user, db)
    return {
        "student_id": current_user.id,
        "target_career": state.get("target_career"),
        "language": state.get("language"),
        "career_readiness_score": state.get("career_readiness_score", 0.0),
        "is_career_ready": state.get("is_career_ready", False),
        "domain_scores": state.get("domain_scores", {}),
        "concept_mastery": state.get("concept_mastery", {}),
        "priority_gaps": state.get("priority_gaps", []),
        "grounded_resources": state.get("grounded_resources", []),
        "tutor_explanation_localized": state.get("tutor_explanation_localized", ""),
        "study_plan": state.get("study_plan", []),
        "plan_summary": state.get("plan_summary", "")
    }
