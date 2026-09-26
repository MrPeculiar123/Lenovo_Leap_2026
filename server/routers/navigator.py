import json
import ast
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.database import get_db
from models.assessment import AssessmentSession
from models.feedback import FeedbackLog
from models.user import User, UserProfile
from routers.auth import get_current_user
from schemas.navigator import (
    AnalyzeAndPlanRequest,
    StartAssessmentRequest,
    SubmitAnswerRequest,
    TutorChatRequest,
    TutorFeedbackRequest,
    PlanProgressRequest,
)
from core.config import settings
from services.career_benchmarks import career_benchmarks
from services.checkpoint_store import get_checkpointer
from services.assessment_rl import (
    ASSESSMENT_POLICY_NAME,
    build_assessment_context,
    calculate_assessment_reward,
)
from services.rl_policy_service import RLPolicyService
from services.tutor_rl import (
    TUTOR_POLICY_NAME,
    build_tutor_context,
    calculate_tutor_reward,
)

try:
    from agent.graph import get_adaptive_learning_graph, load_persisted_state, persist_tutor_history, update_persisted_state, run_remediation_pipeline_async
    from agent.nodes.content_tutor import tutor_chat_node
    from agent.state import StudentState
except ImportError:
    from server.agent.graph import get_adaptive_learning_graph, load_persisted_state, persist_tutor_history, update_persisted_state, run_remediation_pipeline_async
    from server.agent.nodes.content_tutor import tutor_chat_node
    from server.agent.state import StudentState


router = APIRouter(prefix="/navigator", tags=["Navigator Agent"])
TOTAL_ASSESSMENT_STEPS = 8


def _normalize_language(value: Optional[str]) -> str:
    if not value:
        return "English"
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
    allowed_keys = ("id", "concept_id", "question", "options", "difficulty", "question_type", "source")
    return {
        key: question[key]
        for key in allowed_keys
        if key in question and question[key] is not None
    }


def _normalize_tutor_history(history: Any) -> list[Dict[str, str]]:
    """Convert current and legacy checkpoint turns into a stable text contract."""
    normalized: list[Dict[str, str]] = []
    for turn in history or []:
        if not isinstance(turn, dict):
            continue
        content = turn.get("content", "")
        if isinstance(content, list):
            content = "".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content
            )
        elif isinstance(content, str) and content.lstrip().startswith("[{"):
            try:
                blocks = ast.literal_eval(content)
                if isinstance(blocks, list):
                    content = "".join(
                        item.get("text", "") if isinstance(item, dict) else str(item)
                        for item in blocks
                    )
            except (SyntaxError, ValueError):
                pass
        normalized.append({
            "role": "user" if turn.get("role") == "user" else "assistant",
            "content": str(content),
            **({"message_id": str(turn["message_id"])} if turn.get("message_id") else {}),
        })
    return normalized[-10:]


def _assessment_response(session: AssessmentSession, state: StudentState) -> Dict[str, Any]:
    """Return one stable response contract for start, resume, and submit."""
    question = _public_question(state.get("current_question"))
    is_complete = bool(state.get("is_assessment_complete", False))
    response = {
        "status": "success",
        "session_id": session.id,
        "assessment_id": session.id,
        "question": question,
        "target_career": state.get("target_career"),
        "subject": state.get("subject"),
        "language": state.get("language"),
        "current_step": state.get("current_step", 0),
        "total_steps": TOTAL_ASSESSMENT_STEPS,
        "is_assessment_complete": is_complete,
        "is_complete": is_complete,
        "current_question": question,
        "next_question": question,
        "ml_profile": state.get("ml_profile"),
        "concept_mastery": state.get("concept_mastery", {}),
        "domain_scores": state.get("domain_scores", {}),
        "career_readiness_score": state.get("career_readiness_score"),
        "priority_gaps": state.get("priority_gaps", []),
        "study_plan": state.get("study_plan", []),
        "tutor_chat_history": _normalize_tutor_history(state.get("tutor_chat_history", [])),
        "tutor_explanation_localized": state.get("tutor_explanation_localized", ""),
    }
    if state.get("assessment_action"):
        response["adaptation"] = {"strategy": state["assessment_action"]}
    if settings.DEBUG:
        response["_debug"] = {
            "target_career": state.get("target_career"),
            "subject": state.get("subject"),
            "language": state.get("language"),
            "question_source": question.get("source") if question else None,
            "assessment_model": state.get("assessment_model", "gemini-3.5-flash-lite"),
        }
    return response


def _graph_config(session: AssessmentSession) -> Dict[str, Any]:
    return {"configurable": {"thread_id": session.thread_id}}


def _profile_state(user: User, profile: Optional[UserProfile]) -> StudentState:
    weekly_hours = profile.time_commitment_hrs if (profile and profile.time_commitment_hrs) else 7
    daily_minutes = max(1, round((weekly_hours * 60) / 7))

    pref_types = profile.preferred_question_types if (profile and profile.preferred_question_types) else ["MCQ"]
    if isinstance(pref_types, str):
        try:
            pref_types = json.loads(pref_types)
        except Exception:
            pref_types = ["MCQ"]

    exposure = profile.prior_exposure if (profile and profile.prior_exposure) else []
    if isinstance(exposure, str):
        try:
            exposure = json.loads(exposure)
        except Exception:
            exposure = []

    chosen_language = profile.primary_language if (profile and profile.primary_language) else "English"
    chosen_career = profile.career_goal if (profile and profile.career_goal) else "Data Analyst"
    chosen_subject = profile.subject if (profile and profile.subject) else "Data Analytics"

    return {
        "student_id": str(user.id),
        "target_career": chosen_career,
        "subject": chosen_subject,
        "language": chosen_language,
        "primary_language": chosen_language,
        "time_commitment_hrs": weekly_hours,
        "daily_time_minutes": daily_minutes,
        "time_per_day_mins": daily_minutes,
        "secondary_language": profile.secondary_language if profile else None,
        "perceived_level": profile.perceived_level if (profile and profile.perceived_level) else "Intermediate",
        "prior_exposure": exposure,
        "preferred_question_types": pref_types,
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
    session = None if req.restart else _latest_in_progress(current_user, db, lock=False)
    if session:
        try:
            state = await _state_for_session(session)
        except HTTPException:
            # A failed first LLM call can leave SQL metadata without a checkpoint.
            # Abandon that attempt so refresh can create a clean recoverable one.
            session.status = "abandoned"
            session.last_activity_at = datetime.utcnow()
            db.commit()
            session = None
        if session is None:
            return await start_assessment(req.model_copy(update={"restart": True}), current_user, db)
        if not state.get("is_assessment_complete") and not state.get("current_question"):
            try:
                if not state.get("assessment_action"):
                    state["assessment_action"] = RLPolicyService(db).select_action(
                        ASSESSMENT_POLICY_NAME,
                        build_assessment_context(state),
                    )
                state = await get_adaptive_learning_graph().ainvoke(state, config=_graph_config(session))
            except Exception as exc:
                session.status = "abandoned"
                session.last_activity_at = datetime.utcnow()
                db.commit()
                raise HTTPException(status_code=503, detail="Assessment recovery failed. Please start a new assessment.") from exc
        _update_session_metadata(session, state)
        db.commit()
        return _assessment_response(session, state)

    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not req.restart:
        latest_completed = (
            db.query(AssessmentSession)
            .filter(
                AssessmentSession.user_id == current_user.id,
                AssessmentSession.status == "completed",
            )
            .order_by(AssessmentSession.completed_at.desc(), AssessmentSession.id.desc())
            .first()
        )
        if latest_completed:
            return _assessment_response(latest_completed, await _state_for_session(latest_completed))
    req_lang = req.language or (profile.primary_language if profile else None)
    language = _normalize_language(req_lang or "English")
    requested_career = req.target_career or (profile.career_goal if profile else "Data Analyst")
    if not career_benchmarks.get_role(requested_career):
        raise HTTPException(status_code=422, detail="Unsupported career path. Complete onboarding with a supported pathway.")

    session = AssessmentSession(
        user_id=current_user.id,
        thread_id=f"assessment:{uuid.uuid4()}",
        subject=req.subject or (profile.subject if profile else "Data Analytics"),
        target_career=requested_career,
        language=language,
    )
    db.add(session)
    db.commit()  # Release DB transaction before calling LLM/LangSmith async workflow

    state = _profile_state(current_user, profile)
    state.update(
        {
            "target_career": session.target_career,
            "subject": session.subject,
            "language": language,
            "primary_language": language,
            "daily_time_minutes": req.daily_time_minutes if req.daily_time_minutes is not None else state["daily_time_minutes"],
            "time_per_day_mins": req.daily_time_minutes if req.daily_time_minutes is not None else state["time_per_day_mins"],
            "perceived_level": req.perceived_level or state["perceived_level"],
        }
    )
    state["assessment_action"] = RLPolicyService(db).select_action(
        ASSESSMENT_POLICY_NAME,
        build_assessment_context(state),
    )

    try:
        updated_state = await get_adaptive_learning_graph().ainvoke(state, config=_graph_config(session))
    except Exception as exc:
        session.status = "abandoned"
        session.last_activity_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=503, detail="Assessment could not start. Refresh to retry with a new attempt.") from exc

    db.refresh(session)
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
        lock=False,
    )
    state = await _state_for_session(session)
    if req.question_id and req.question_id == state.get("last_submitted_question_id"):
        if not state.get("is_assessment_complete") and not state.get("current_question"):
            next_action = RLPolicyService(db).select_action(
                ASSESSMENT_POLICY_NAME,
                build_assessment_context(state),
            )
            state = await get_adaptive_learning_graph().ainvoke(
                {"assessment_action": next_action, "pause_after_evaluation": False},
                config=_graph_config(session),
            )
            db.refresh(session)
            _update_session_metadata(session, state)
            db.commit()
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
        {
            "current_question": question_with_answer,
            "pause_after_evaluation": True,
        },
        config=_graph_config(session),
    )

    context = build_assessment_context(state, question_difficulty=current_question.get("difficulty", 0.5))
    reward, _ = calculate_assessment_reward(state, updated_state, question_with_answer)
    action_taken = state.get("assessment_action") or "SAME_DIFFICULTY"
    RLPolicyService(db).update_policy(
        ASSESSMENT_POLICY_NAME,
        action_taken,
        context,
        reward,
    )
    db.add(
        FeedbackLog(
            user_id=str(current_user.id),
            thread_id=session.thread_id,
            concept_id=current_question.get("concept_id"),
            policy_type="ASSESSMENT",
            state_vector=context,
            action_taken=action_taken,
            reward=reward,
            quiz_passed=1 if updated_state.get("raw_responses", [{}])[-1].get("is_correct") else 0,
        )
    )
    db.commit()

    if not updated_state.get("is_assessment_complete"):
        next_action = RLPolicyService(db).select_action(
            ASSESSMENT_POLICY_NAME,
            build_assessment_context(updated_state, question_difficulty=current_question.get("difficulty", 0.5)),
        )
        updated_state = await get_adaptive_learning_graph().ainvoke(
            {"assessment_action": next_action, "pause_after_evaluation": False},
            config=_graph_config(session),
        )

    db.refresh(session)
    _update_session_metadata(session, updated_state)
    db.commit()

    return _assessment_response(session, updated_state)


@router.post("/analyze-and-plan")
async def analyze_and_plan(
    req: AnalyzeAndPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _resolve_session(current_user, db, allow_completed=True, lock=False)
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

    db.refresh(session)
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
    try:
        session = _resolve_session(current_user, db, allow_completed=True, lock=False)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Complete an assessment before starting a personalized tutor conversation.",
            ) from exc
        raise
    state = await _state_for_session(session)
    state["language"] = _normalize_language(req.language or state.get("language") or state.get("primary_language"))
    tutor_context = build_tutor_context(state)
    tutor_action = RLPolicyService(db).select_action(TUTOR_POLICY_NAME, tutor_context)
    state["tutor_action"] = tutor_action
    res = tutor_chat_node(state, student_message=req.message)
    history = _normalize_tutor_history(state.get("tutor_chat_history", []))
    history = _normalize_tutor_history(history + res.get("tutor_chat_history", []))
    message_id = str(uuid.uuid4())
    if history and history[-1].get("role") == "assistant":
        history[-1]["message_id"] = message_id
    persisted_state = await persist_tutor_history(session.thread_id, history)
    db.add(
        FeedbackLog(
            id=message_id,
            user_id=str(current_user.id),
            thread_id=session.thread_id,
            concept_id=state.get("current_concept_id"),
            policy_type="TUTOR",
            state_vector=tutor_context,
            action_taken=tutor_action,
            reward=0.0,
            explicit_rating=None,
            quiz_passed=None,
        )
    )
    db.commit()
    return {
        "status": "success",
        "reply": res.get("latest_tutor_reply"),
        "message_id": message_id,
        "chat_history": _normalize_tutor_history((persisted_state or {}).get("tutor_chat_history", history)),
        "grounded_resources": state.get("grounded_resources", []),
        "target_career": state.get("target_career"),
        "language": state.get("language"),
    }


@router.post("/tutor/feedback")
def tutor_feedback(
    req: TutorFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    feedback = (
        db.query(FeedbackLog)
        .filter(
            FeedbackLog.id == req.message_id,
            FeedbackLog.user_id == str(current_user.id),
            FeedbackLog.policy_type == "TUTOR",
        )
        .with_for_update()
        .first()
    )
    if not feedback:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tutor interaction not found.")
    if feedback.explicit_rating is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Feedback has already been recorded.")
    session = (
        db.query(AssessmentSession)
        .filter(
            AssessmentSession.thread_id == feedback.thread_id,
            AssessmentSession.user_id == current_user.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tutor interaction not found.")

    quiz_passed = None if feedback.quiz_passed is None else bool(feedback.quiz_passed)
    reward = calculate_tutor_reward(req.rating, quiz_passed=quiz_passed)
    RLPolicyService(db).update_policy(
        TUTOR_POLICY_NAME,
        feedback.action_taken,
        feedback.state_vector,
        reward,
    )
    feedback.explicit_rating = req.rating
    feedback.reward = reward
    db.commit()
    return {"status": "success", "message_id": feedback.id, "feedback_recorded": True}


@router.patch("/learning-plan/progress")
async def update_learning_plan_progress(
    req: PlanProgressRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _resolve_session(current_user, db, allow_completed=True, lock=True)
    state = await _state_for_session(session)
    progress = dict(session.plan_progress or {})
    progress[str(req.day)] = req.completion_status
    session.plan_progress = progress

    plan = list(state.get("study_plan", []))
    for item in plan:
        if int(item.get("day", 0)) == req.day:
            item["completion_status"] = req.completion_status
    await update_persisted_state(session.thread_id, {"study_plan": plan})
    db.commit()
    return {"status": "success", "day": req.day, "completion_status": req.completion_status, "plan_progress": progress}


@router.get("/assessment-history")
async def assessment_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(AssessmentSession)
        .filter(AssessmentSession.user_id == current_user.id)
        .order_by(AssessmentSession.started_at.desc(), AssessmentSession.id.desc())
        .all()
    )
    assessments = []
    for session in sessions:
        state = await _state_for_session(session)
        assessments.append({
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
                "plan_progress": session.plan_progress or {},
                "domain_scores": state.get("domain_scores", {}),
                "concept_mastery": state.get("concept_mastery", {}),
            })
    return {"assessments": assessments}


@router.get("/health")
def navigator_health(db: Session = Depends(get_db)):
    checks = {"database": "ok", "checkpointing": "ok"}
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        checks["database"] = "unavailable"
    try:
        get_checkpointer()
    except RuntimeError:
        checks["checkpointing"] = "unavailable"
    healthy = all(value == "ok" for value in checks.values())
    return {"status": "ok" if healthy else "degraded", "checks": checks}


@router.get("/assessment/{assessment_id}")
async def assessment_detail(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _resolve_session(current_user, db, assessment_id, allow_completed=True)
    state = await _state_for_session(session)
    return {
        "status": "success",
        "assessment_id": session.id,
        "subject": session.subject,
        "target_career": session.target_career,
        "language": session.language,
        "status_value": session.status,
        "started_at": session.started_at,
        "completed_at": session.completed_at,
        "career_readiness_score": state.get("career_readiness_score"),
        "is_career_ready": state.get("is_career_ready", False),
        "domain_scores": state.get("domain_scores", {}),
        "concept_mastery": state.get("concept_mastery", {}),
        "priority_gaps": state.get("priority_gaps", []),
        "grounded_resources": state.get("grounded_resources", []),
        "tutor_chat_history": _normalize_tutor_history(state.get("tutor_chat_history", [])),
        "tutor_explanation_localized": state.get("tutor_explanation_localized", ""),
        "study_plan": state.get("study_plan", []),
        "plan_summary": state.get("plan_summary", ""),
        "assessment_questions": state.get("assessment_questions", []),
        "raw_responses": state.get("raw_responses", []),
        "plan_progress": session.plan_progress or {},
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
    response = {
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
        "tutor_chat_history": _normalize_tutor_history(state.get("tutor_chat_history", [])),
        "tutor_explanation_localized": state.get("tutor_explanation_localized", ""),
        "study_plan": state.get("study_plan", []),
        "plan_summary": state.get("plan_summary", ""),
        "plan_progress": session.plan_progress or {},
    }
    if settings.DEBUG:
        response["_debug"] = {
            "theta": (state.get("ml_profile") or {}).get("theta"),
            "concept_mastery": state.get("concept_mastery", {}),
            "domain_scores": state.get("domain_scores", {}),
        }
    return response