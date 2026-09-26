"""Tutor-specific LinUCB context and feedback reward helpers."""

from __future__ import annotations

from typing import Optional

try:
    from agent.state import StudentState
    from services.ml_engine import ml_engine, StudentMLProfile
except ImportError:
    from server.agent.state import StudentState
    from server.services.ml_engine import ml_engine, StudentMLProfile


TUTOR_POLICY_NAME = "tutor"
TUTOR_ACTIONS = (
    "SOCRATIC",
    "DIRECT_EXPLANATION",
    "CODE_FIRST",
    "ANALOGY_BASED",
)
TUTOR_CONTEXT_FEATURES = (
    "theta_normalized",
    "current_concept_mastery",
    "struggle_risk",
    "consecutive_failures",
    "recent_accuracy",
    "theta_uncertainty",
    "assessment_progress",
    "recent_response_time",
)


STRATEGY_INSTRUCTIONS = {
    "SOCRATIC": "Guide the student with probing questions. Do not give the direct answer immediately.",
    "DIRECT_EXPLANATION": "Provide a clear, concise direct explanation with key points.",
    "CODE_FIRST": "Start with a minimal runnable code example, then explain it.",
    "ANALOGY_BASED": "Explain the concept using a concrete everyday analogy.",
}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _profile(state: StudentState) -> StudentMLProfile:
    stored = state.get("ml_profile")
    return StudentMLProfile.from_dict(stored) if stored else ml_engine.initialize_profile(
        state.get("perceived_level", "Intermediate")
    )


def _recent_accuracy(profile: StudentMLProfile) -> float:
    history = profile.response_history[-5:]
    if not history:
        return 0.5
    return sum(bool(item.get("is_correct")) for item in history) / len(history)


def _recent_response_time(profile: StudentMLProfile) -> float:
    history = profile.response_history[-5:]
    if not history:
        return 0.0
    response_times = [float(item.get("response_time_sec", 0.0) or 0.0) for item in history]
    return _clamp(sum(response_times) / len(response_times) / 90.0)


def build_tutor_context(state: StudentState) -> list[float]:
    """Build the server-only fixed tutor context in ``TUTOR_CONTEXT_FEATURES`` order."""
    profile = _profile(state)
    concept_id = state.get("current_concept_id")
    state_mastery = state.get("concept_mastery", {})
    mastery = (
        state_mastery.get(concept_id, profile.concept_mastery.get(concept_id, 0.30))
        if concept_id
        else 0.30
    )
    return [
        _clamp((profile.theta + 3.0) / 6.0),
        _clamp(mastery),
        _clamp(profile.struggle_risk),
        _clamp(profile.consecutive_incorrect / 4.0),
        _clamp(_recent_accuracy(profile)),
        _clamp(profile.theta_standard_error),
        _clamp(profile.questions_count / 8.0),
        _recent_response_time(profile),
    ]


def calculate_tutor_reward(
    explicit_rating: int,
    quiz_passed: Optional[bool] = None,
    engagement_signal: float = 0.0,
) -> float:
    """Calculate reward without treating a missing quiz as a failed quiz."""
    explicit_signal = 1.0 if explicit_rating == 1 else -1.0
    quiz_signal = 0.0 if quiz_passed is None else (1.0 if quiz_passed else -1.0)
    reward = 0.4 * explicit_signal + 0.5 * quiz_signal + 0.1 * max(-1.0, min(1.0, engagement_signal))
    return max(-1.0, min(1.0, reward))
