import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from models.assessment import AssessmentSession
from models.user import User, UserProfile
from routers.auth import get_current_user
from schemas.navigator import (
    AnalyzeAndPlanRequest,
    StartAssessmentRequest,
    SubmitAnswerRequest,
    TutorChatRequest,
)

try:
    from agent.graph import get_adaptive_learning_graph, load_persisted_state, run_remediation_pipeline_async
    from agent.nodes.content_tutor import tutor_chat_node
    from agent.state import StudentState
except ImportError:
    from server.agent.graph import get_adaptive_learning_graph, load_persisted_state, run_remediation_pipeline_async
    from server.agent.nodes.content_tutor import tutor_chat_node
    from server.agent.state import StudentState


router = APIRouter(prefix="/navigator", tags=["Navigator Agent"])
TOTAL_ASSESSMENT_STEPS = 8


def _normalize_language(value: Optional[str]) -> str:
    if value is None:
        return "Marathi"
    normalized = str(value).strip().title()
    if normalized not in {"English", "Hindi", "Marathi"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported language. Use English, Hindi, or Marathi.",
        )
    return normalized


def _public_question(question: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not question:
        return None
    allowed_keys = ("id", "concept_id", "question", "options", "difficulty", "question_type")
    return {
        key: question[key]
        for key in allowed_keys
        if key in question and question[key] is not None
    }


def _assessment_response(session: AssessmentSession, state: StudentState) -> Dict[str, Any]:
    """Return one stable response contract for start, resume, and submit."""
    question = _public_question(state.get("current_question"))
    is_complete = bool(state.get("is_assessment_complete", False))
    return {
        "status": "success",
        "session_id": session.id,
        "assessment_id": session.id,
        "question": question,
        "current_step": state.get("current_step", 0),
        "total_steps": TOTAL_ASSESSMENT_STEPS,
        "is_assessment_complete": is_complete,
        # Kept for existing clients during the contract transition.
        "is_complete": is_complete,
        "current_question": question,
        "next_question": question,
        "ml_profile": state.get("ml_profile"),
        "concept_mastery": state.get("concept_mastery", {}),
        "domain_scores": state.get("domain_scores", {}),
        "career_readiness_score": state.get("career_readiness_score"),
        "priority_gaps": state.get("priority_gaps", []),
        "study_plan": state.get("study_plan", []),
        "tutor_explanation_localized": state.get("tutor_explanation_localized", ""),
    }


def _graph_config(session: AssessmentSession) -> Dict[str, Any]:
    return {"configurable": {"thread_id": session.thread_id}}


def _profile_state(user: User, profile: Optional[UserProfile]) -> StudentState:
    return {
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
        "errors": [],
    }


def _latest_in_progress(user: User, db: Session, lock: bool = False) -> Optional[AssessmentSession]:
    query = (
        db.query(AssessmentSession)
        .filter(
            AssessmentSession.user_id == user.id,
            AssessmentSession.status == "in_progress",
        )
        .order_by(AssessmentSession.started_at.desc(), AssessmentSession.id.desc())
    )
    if lock:
        query = query.with_for_update()
    return query.first()


def _resolve_session(
    user: User,
    db: Session,
    assessment_id: Optional[str] = None,
    *,
    allow_completed: bool = False,
    lock: bool = False,
) -> AssessmentSession:
    if assessment_id:
        query = db.query(AssessmentSession).filter(
            AssessmentSession.id == assessment_id,
            AssessmentSession.user_id == user.id,
        )
        if lock:
            query = query.with_for_update()
        session = query.first()
    else:
        query = db.query(AssessmentSession).filter(AssessmentSession.user_id == user.id)
        if not allow_completed:
            query = query.filter(AssessmentSession.status == "in_progress")
        session = query.order_by(
            AssessmentSession.last_activity_at.desc(),
            AssessmentSession.id.desc(),
        ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment session not found.",
        )
    if not allow_completed and session.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment is no longer in progress.",
        )
    return session


async def _state_for_session(session: AssessmentSession) -> StudentState:
    state = await load_persisted_state(session.thread_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Assessment state could not be restored.",
        )
    return state


def _update_session_metadata(session: AssessmentSession, state: StudentState) -> None:
    session.last_activity_at = datetime.utcnow()
    session.questions_asked = len(state.get("asked_question_ids", []))
    if state.get("is_assessment_complete"):
        session.status = "completed"
        session.completed_at = session.completed_at or datetime.utcnow()
        score = state.get("career_readiness_score")
        session.career_readiness_score = float(score) if score is not None else None


@router.post("/start-assessment")
async def start_assessment(
    req: StartAssessmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Creates an attempt or resumes the user's latest unfinished attempt."""
    session = _latest_in_progress(current_user, db, lock=True)
    if session:
        state = await _state_for_session(session)
        # The checkpoint is authoritative for recovery if a prior SQL commit failed.
        _update_session_metadata(session, state)
        db.commit()
        return _assessment_response(session, state)

    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    language = _normalize_language(req.language or (profile.primary_language if profile else None))
    session = AssessmentSession(
        user_id=current_user.id,
        thread_id=f"assessment:{uuid.uuid4()}",
        subject=req.subject or (profile.subject if profile else "Data Analytics"),
        target_career=req.target_career or (profile.career_goal if profile else "Data Analyst"),
        language=language,
    )
    db.add(session)
    db.flush()

    state = _profile_state(current_user, profile)
    state.update(
        {
            "target_career": session.target_career,
            "subject": session.subject,
            "language": language,
            "primary_language": language,
            "daily_time_minutes": req.daily_time_minutes or state["daily_time_minutes"],
            "time_per_day_mins": req.daily_time_minutes or state["time_per_day_mins"],
            "perceived_level": req.perceived_level or state["perceived_level"],
        }
    )
    updated_state = await get_adaptive_learning_graph().ainvoke(state, config=_graph_config(session))
    _update_session_metadata(session, updated_state)
    db.commit()

    return _assessment_response(session, updated_state)


@router.post("/submit-answer")
async def submit_answer(
    req: SubmitAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Grades the current question through the persisted LangGraph thread."""
    session = _resolve_session(
        current_user,
        db,
        req.assessment_id,
        lock=True,
    )
    state = await _state_for_session(session)
    if req.question_id and req.question_id == state.get("last_submitted_question_id"):
        _update_session_metadata(session, state)
        db.commit()
        return _assessment_response(session, state)
    current_question = state.get("current_question")
    if not current_question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active assessment question. Please start an assessment first.",
        )
    if req.question_id and req.question_id != current_question.get("id"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Question ID does not match the active assessment question.",
        )

    answer = req.student_answer.strip()
    question_with_answer = dict(current_question)
    question_with_answer["student_answer"] = answer
    question_with_answer["response_time_sec"] = req.response_time_sec or 20.0
    updated_state = await get_adaptive_learning_graph().ainvoke(
        {"current_question": question_with_answer},
        config=_graph_config(session),
    )
    _update_session_metadata(session, updated_state)
    db.commit()

    return _assessment_response(session, updated_state)


@router.post("/analyze-and-plan")
async def analyze_and_plan(
    req: AnalyzeAndPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _resolve_session(current_user, db, allow_completed=True)
    state = await _state_for_session(session)
    graph_updates: StudentState = {}
    if req.target_career:
        graph_updates["target_career"] = req.target_career
    if req.language:
        graph_updates["language"] = _normalize_language(req.language)
        graph_updates["primary_language"] = graph_updates["language"]
    if req.daily_time_minutes:
        graph_updates["daily_time_minutes"] = req.daily_time_minutes
        graph_updates["time_per_day_mins"] = req.daily_time_minutes
    if req.domain_scores and not state.get("domain_scores"):
        graph_updates["domain_scores"] = req.domain_scores

    result_state = await run_remediation_pipeline_async(graph_updates, config=_graph_config(session))
    _update_session_metadata(session, result_state)
    db.commit()
    return {
        "status": "success",
        "career_readiness_score": result_state.get("career_readiness_score"),
        "is_career_ready": result_state.get("is_career_ready"),
        "priority_gaps": result_state.get("priority_gaps", []),
        "grounded_resources": result_state.get("grounded_resources", []),
        "tutor_explanation_localized": result_state.get("tutor_explanation_localized", ""),
        "plan_summary": result_state.get("plan_summary", ""),
        "study_plan": result_state.get("study_plan", []),
    }


@router.post("/tutor/chat")
async def tutor_chat(
    req: TutorChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _resolve_session(current_user, db, allow_completed=True)
    state = await _state_for_session(session)
    state["language"] = _normalize_language(req.language)
    res = tutor_chat_node(state, student_message=req.message)
    return {
        "status": "success",
        "reply": res.get("latest_tutor_reply"),
        "chat_history": (state.get("tutor_chat_history", []) + res.get("tutor_chat_history", [])),
    }


@router.get("/assessment-history")
def assessment_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(AssessmentSession)
        .filter(AssessmentSession.user_id == current_user.id)
        .order_by(AssessmentSession.started_at.desc(), AssessmentSession.id.desc())
        .all()
    )
    return {
        "assessments": [
            {
                "id": session.id,
                "subject": session.subject,
                "target_career": session.target_career,
                "language": session.language,
                "status": session.status,
                "started_at": session.started_at,
                "completed_at": session.completed_at,
                "career_readiness_score": (
                    float(session.career_readiness_score)
                    if session.career_readiness_score is not None
                    else None
                ),
            }
            for session in sessions
        ]
    }


@router.get("/dashboard-data")
async def dashboard_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    completed = (
        db.query(AssessmentSession)
        .filter(
            AssessmentSession.user_id == current_user.id,
            AssessmentSession.status == "completed",
        )
        .order_by(AssessmentSession.completed_at.desc(), AssessmentSession.id.desc())
        .first()
    )
    session = completed or _latest_in_progress(current_user, db)
    if not session:
        return {
            "status": "success",
            "student_id": str(current_user.id),
            "career_readiness_score": 0.0,
            "is_career_ready": False,
            "domain_scores": {},
            "concept_mastery": {},
            "priority_gaps": [],
            "grounded_resources": [],
            "study_plan": [],
            "plan_summary": "",
        }

    state = await _state_for_session(session)
    return {
        "status": "success",
        "student_id": str(current_user.id),
        "assessment_id": session.id,
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
        "plan_summary": state.get("plan_summary", ""),
    }
