"""Assessment-specific LinUCB context, action mapping, and reward helpers."""

from __future__ import annotations

from typing import Any, Dict, Tuple

try:
    from agent.state import StudentState
    from services.knowledge_graph import knowledge_graph
    from services.ml_engine import ml_engine, StudentMLProfile
except ImportError:
    from server.agent.state import StudentState
    from server.services.knowledge_graph import knowledge_graph
    from server.services.ml_engine import ml_engine, StudentMLProfile


ASSESSMENT_POLICY_NAME = "assessment"
ASSESSMENT_ACTIONS = (
    "EASIER_QUESTION",
    "SAME_DIFFICULTY",
    "HARDER_QUESTION",
    "PREREQUISITE_QUESTION",
)
ASSESSMENT_CONTEXT_DIMENSION = 8
ASSESSMENT_CONTEXT_FEATURES = (
    "theta_normalized",
    "current_concept_mastery",
    "recent_accuracy",
    "theta_uncertainty",
    "consecutive_failures",
    "current_question_difficulty",
    "assessment_progress",
    "struggle_risk",
)


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, float(value)))


def _profile(state: StudentState) -> StudentMLProfile:
    stored = state.get("ml_profile")
    return StudentMLProfile.from_dict(stored) if stored else ml_engine.initialize_profile(
        state.get("perceived_level", "Intermediate")
    )


def _recent_accuracy(state: StudentState, window: int = 5) -> float:
    responses = state.get("raw_responses", [])[-window:]
    if not responses:
        return 0.5
    return sum(bool(response.get("is_correct")) for response in responses) / len(responses)


def build_assessment_context(
    state: StudentState,
    question_difficulty: float | None = None,
) -> list[float]:
    """Build the server-only 8-feature assessment context in documented order."""
    profile = _profile(state)
    current_question = state.get("current_question") or {}
    concept_id = current_question.get("concept_id") or state.get("current_concept_id")
    mastery = profile.concept_mastery.get(concept_id, 0.30) if concept_id else 0.30
    theta_normalized = _clamp((profile.theta + 3.0) / 6.0)
    difficulty = question_difficulty
    if difficulty is None:
        difficulty = current_question.get("difficulty", 0.5)
    return [
        theta_normalized,
        _clamp(mastery),
        _clamp(_recent_accuracy(state)),
        _clamp(profile.theta_standard_error),
        _clamp(profile.consecutive_incorrect / 4.0),
        _clamp(difficulty),
        _clamp(state.get("current_step", 0) / 8.0),
        _clamp(profile.struggle_risk),
    ]


def target_for_action(base_difficulty: float, action: str) -> float:
    """Map a policy action to the existing generator's difficulty target."""
    if action == "EASIER_QUESTION":
        return _clamp(base_difficulty - 0.15, 0.1, 0.9)
    if action == "HARDER_QUESTION":
        return _clamp(base_difficulty + 0.15, 0.1, 0.9)
    if action in {"SAME_DIFFICULTY", "PREREQUISITE_QUESTION"}:
        return _clamp(base_difficulty, 0.1, 0.9)
    raise ValueError(f"Unknown assessment action: {action}")


def concept_for_action(state: StudentState, action: str, selected_concept: str) -> str:
    """Use the existing DAG traversal for prerequisite actions."""
    if action != "PREREQUISITE_QUESTION":
        return selected_concept
    current_concept = state.get("current_concept_id") or selected_concept
    prerequisite = knowledge_graph.traverse_down(current_concept)
    return prerequisite or selected_concept


def calculate_assessment_reward(
    before_state: StudentState,
    after_state: StudentState,
    answered_question: Dict[str, Any],
) -> Tuple[float, Dict[str, float]]:
    """Calculate diagnostic reward from existing IRT/BKT and response signals.

    diagnostic_gain is the fractional reduction in theta standard error.
    mastery_information_gain is the absolute BKT mastery change for the answered concept.
    difficulty_match is closeness of the existing IRT correctness probability to 0.5.
    engagement is response time normalized to a 30-second engaged-response target.
    """
    before_profile = _profile(before_state)
    after_profile = _profile(after_state)
    before_error = max(before_profile.theta_standard_error, 0.2)
    diagnostic_gain = _clamp(
        (before_error - after_profile.theta_standard_error) / before_error,
        -1.0,
        1.0,
    )
    concept_id = answered_question.get("concept_id")
    before_mastery = before_profile.concept_mastery.get(concept_id, 0.30)
    after_mastery = after_profile.concept_mastery.get(concept_id, before_mastery)
    mastery_information_gain = _clamp(abs(after_mastery - before_mastery))
    probability = ml_engine.probability_correct_irt(
        before_profile.theta,
        float(answered_question.get("difficulty", 0.5)),
        float(answered_question.get("discrimination", 1.0)),
    )
    difficulty_match = _clamp(1.0 - (abs(probability - 0.5) * 2.0))
    response_time = max(0.0, float(answered_question.get("response_time_sec") or 0.0))
    engagement = _clamp(response_time / 30.0)
    components = {
        "diagnostic_gain": diagnostic_gain,
        "mastery_information_gain": mastery_information_gain,
        "difficulty_match": difficulty_match,
        "engagement": engagement,
    }
    reward = (
        0.45 * diagnostic_gain
        + 0.30 * mastery_information_gain
        + 0.15 * difficulty_match
        + 0.10 * engagement
    )
    return _clamp(reward, -1.0, 1.0), components
