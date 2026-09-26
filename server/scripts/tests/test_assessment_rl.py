import sys
from pathlib import Path

import pytest

SERVER_ROOT = Path(__file__).resolve().parents[2]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from schemas.navigator import SubmitAnswerRequest
from services.assessment_rl import (
    ASSESSMENT_CONTEXT_FEATURES,
    build_assessment_context,
    calculate_assessment_reward,
    concept_for_action,
    target_for_action,
)
from services.knowledge_graph import knowledge_graph
from agent.nodes import assessment as assessment_module


def test_context_has_documented_fixed_features_and_is_clamped():
    context = build_assessment_context({
        "current_step": 99,
        "current_concept_id": "sql_joins",
        "ml_profile": {
            "theta": 99,
            "theta_standard_error": 99,
            "concept_mastery": {"sql_joins": -2},
            "response_history": [],
            "struggle_risk": 99,
            "consecutive_incorrect": 99,
            "consecutive_correct": 0,
            "questions_count": 0,
            "is_terminal": False,
        },
        "raw_responses": [],
    })
    assert len(context) == len(ASSESSMENT_CONTEXT_FEATURES) == 8
    assert all(0.0 <= value <= 1.0 for value in context)


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        ("EASIER_QUESTION", 0.35),
        ("SAME_DIFFICULTY", 0.5),
        ("HARDER_QUESTION", 0.65),
    ],
)
def test_action_changes_existing_difficulty_target(action, expected):
    assert target_for_action(0.5, action) == expected


def test_assessment_node_passes_policy_target_to_existing_generator(monkeypatch):
    captured = {}

    def fake_generate_question(*, concept_id, difficulty, discrimination, state, step, model_override=None):
        captured.update(concept_id=concept_id, difficulty=difficulty)
        return {
            "id": "q1",
            "concept_id": concept_id,
            "question": "Question",
            "options": ["A"],
            "difficulty": difficulty,
            "discrimination": discrimination,
        }

    monkeypatch.setattr(assessment_module, "generate_question", fake_generate_question)
    result = assessment_module.assessment_node({
        "target_career": "Data Analyst",
        "perceived_level": "Intermediate",
        "current_step": 0,
        "raw_responses": [],
        "concept_mastery": {},
        "asked_question_ids": [],
        "assessment_action": "HARDER_QUESTION",
        "is_assessment_complete": False,
    })
    assert captured["difficulty"] == 0.65
    assert result["current_question"]["difficulty"] == 0.65


def test_prerequisite_action_uses_existing_knowledge_graph():
    selected = "sql_joins"
    prerequisite = knowledge_graph.traverse_down(selected)
    assert prerequisite is not None
    assert concept_for_action({"current_concept_id": selected}, "PREREQUISITE_QUESTION", selected) == prerequisite


def test_reward_is_server_calculated_from_existing_signals():
    before = {
        "current_step": 1,
        "ml_profile": {
            "theta": 0.0,
            "theta_standard_error": 1.0,
            "concept_mastery": {"sql_joins": 0.3},
            "response_history": [],
            "struggle_risk": 0.1,
            "consecutive_incorrect": 0,
            "consecutive_correct": 0,
            "questions_count": 0,
            "is_terminal": False,
        },
        "raw_responses": [],
    }
    after = {
        **before,
        "ml_profile": {
            **before["ml_profile"],
            "theta_standard_error": 0.7,
            "concept_mastery": {"sql_joins": 0.6},
        },
    }
    reward, components = calculate_assessment_reward(
        before,
        after,
        {"concept_id": "sql_joins", "difficulty": 0.5, "discrimination": 1.2, "response_time_sec": 20},
    )
    assert -1.0 <= reward <= 1.0
    assert components["diagnostic_gain"] > 0
    assert components["mastery_information_gain"] > 0


def test_client_cannot_submit_rl_action_or_reward():
    fields = SubmitAnswerRequest.model_fields
    assert "action" not in fields
    assert "reward" not in fields
    request = SubmitAnswerRequest(
        question_id="q1",
        student_answer="answer",
        action="HARDER_QUESTION",
        reward=999,
    )
    assert not hasattr(request, "action")
    assert not hasattr(request, "reward")