import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SERVER_ROOT = Path(__file__).resolve().parents[2]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from models.feedback import FeedbackLog
from models.rl_policy import RLPolicyParameter
from models.user import User
from services.rl_policy_service import RLPolicyService


def test_assessment_and_tutor_feedback_change_and_reload_shared_policies():
    engine = create_engine("sqlite:///:memory:")
    User.__table__.create(engine)
    RLPolicyParameter.__table__.create(engine)
    FeedbackLog.__table__.create(engine)
    sessions = sessionmaker(bind=engine)

    first = sessions()
    first.add_all([
        User(id="user-a", email="a@example.com", password_hash="x"),
        User(id="user-b", email="b@example.com", password_hash="x"),
    ])
    first.commit()

    assessment = RLPolicyService(first, alpha=0.0)
    tutor = RLPolicyService(first, alpha=0.0)
    assessment_context = [0.1] * 8
    tutor_context = [0.9] * 8
    assessment.update_policy("assessment", "HARDER_QUESTION", assessment_context, 0.7)
    first.add(FeedbackLog(
        user_id="user-a", thread_id="assessment:a", concept_id="sql_joins",
        policy_type="ASSESSMENT", state_vector=assessment_context,
        action_taken="HARDER_QUESTION", reward=0.7, quiz_passed=1,
    ))
    tutor.update_policy("tutor", "SOCRATIC", tutor_context, 0.4)
    first.add(FeedbackLog(
        user_id="user-b", thread_id="assessment:b", concept_id="sql_joins",
        policy_type="TUTOR", state_vector=tutor_context,
        action_taken="SOCRATIC", reward=0.4, explicit_rating=1,
    ))
    first.commit()

    before_reload = {
        (row.policy_name, row.action): (row.a_matrix, row.b_vector, row.total_updates)
        for row in first.query(RLPolicyParameter).all()
    }
    first.close()

    second = sessions()
    assessment_reloaded = RLPolicyService(second, alpha=0.0).load_policy("assessment")
    tutor_reloaded = RLPolicyService(second, alpha=0.0).load_policy("tutor")
    assert assessment_reloaded.parameters_for("HARDER_QUESTION") == {
        "a_matrix": before_reload[("assessment", "HARDER_QUESTION")][0],
        "b_vector": before_reload[("assessment", "HARDER_QUESTION")][1],
        "total_updates": 1,
    }
    assert tutor_reloaded.parameters_for("SOCRATIC")["total_updates"] == 1
    assert second.query(FeedbackLog).count() == 2
    assert {row.user_id for row in second.query(FeedbackLog).all()} == {"user-a", "user-b"}

    RLPolicyService(second, alpha=0.0).update_policy(
        "assessment", "HARDER_QUESTION", assessment_context, 0.2
    )
    continued = second.query(RLPolicyParameter).filter_by(
        policy_name="assessment", action="HARDER_QUESTION"
    ).one()
    assert continued.total_updates == 2
    assert continued.b_vector != before_reload[("assessment", "HARDER_QUESTION")][1]


def test_policy_action_spaces_are_disjoint():
    assessment_actions = {
        "EASIER_QUESTION", "SAME_DIFFICULTY", "HARDER_QUESTION", "PREREQUISITE_QUESTION"
    }
    tutor_actions = {"SOCRATIC", "DIRECT_EXPLANATION", "CODE_FIRST", "ANALOGY_BASED"}
    assert assessment_actions.isdisjoint(tutor_actions)