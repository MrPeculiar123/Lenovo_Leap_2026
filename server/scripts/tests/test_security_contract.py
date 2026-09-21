import sys
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[2]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from server.routers.navigator import _public_question
from server.schemas.navigator import SubmitAnswerRequest
from server.agent.graph import submit_assessment_answer


def test_public_question_strips_answer_data():
    question = {
        "id": "q_sql_01",
        "concept_id": "sql_joins",
        "question": "Which join returns all rows from the left table?",
        "options": ["INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "CROSS JOIN"],
        "correct_answer": "LEFT JOIN",
        "explanation": "LEFT JOIN keeps all left rows.",
        "difficulty": 0.5,
        "question_type": "MCQ",
    }

    public = _public_question(question)

    assert public == {
        "id": "q_sql_01",
        "concept_id": "sql_joins",
        "question": "Which join returns all rows from the left table?",
        "options": ["INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "CROSS JOIN"],
        "difficulty": 0.5,
        "question_type": "MCQ",
    }
    assert "correct_answer" not in public
    assert "explanation" not in public


def test_submit_answer_request_accepts_question_id_and_answer_alias():
    payload = SubmitAnswerRequest(question_id="q_sql_01", answer="LEFT JOIN")

    assert payload.question_id == "q_sql_01"
    assert payload.student_answer == "LEFT JOIN"


def test_submit_assessment_answer_updates_server_side_state():
    state = {
        "student_id": "user-1",
        "target_career": "Data Analyst",
        "subject": "Data Analytics",
        "language": "English",
        "primary_language": "English",
        "daily_time_minutes": 60,
        "time_per_day_mins": 60,
        "perceived_level": "Intermediate",
        "current_question": {
            "id": "q_sql_01",
            "concept_id": "sql_joins",
            "question": "Which join returns all rows from the left table?",
            "options": ["INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "CROSS JOIN"],
            "correct_answer": "LEFT JOIN",
            "explanation": "LEFT JOIN keeps all left rows.",
            "difficulty": 0.5,
            "discrimination": 1.2,
            "question_type": "MCQ",
            "student_answer": None,
            "is_correct": None,
            "response_time_sec": None,
        },
        "ml_profile": {"theta": 0.0, "questions_count": 0, "is_terminal": False, "concept_mastery": {}},
        "concept_mastery": {},
        "domain_scores": {},
        "asked_question_ids": [],
        "assessment_questions": [],
        "raw_responses": [],
        "grounded_resources": [],
        "tutor_chat_history": [],
        "errors": [],
    }

    updated = submit_assessment_answer(state, student_answer="LEFT JOIN", response_time_sec=12.5)

    assert updated["raw_responses"]
    assert updated["ml_profile"]["questions_count"] >= 1
    assert updated["current_question"]["student_answer"] == "LEFT JOIN"
