import inspect
import sys
from pathlib import Path

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SERVER_ROOT = Path(__file__).resolve().parents[2]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from core.database import Base
from models.feedback import FeedbackLog
from models.rl_policy import RLPolicyParameter
from services.rl_policy import LinUCBPolicy
from services.rl_policy_service import RLPolicyService


def policy_database():
    engine = create_engine("sqlite:///:memory:")
    RLPolicyParameter.__table__.create(engine)
    return sessionmaker(bind=engine)


def test_initialization_and_valid_action_selection():
    policy = LinUCBPolicy(["a", "b"], dimension=3, alpha=0.0)
    assert policy.select_action([1.0, 0.0, 0.0]) == "a"
    assert np.array_equal(policy._a["a"], np.eye(3))
    assert np.array_equal(policy._b["a"], np.zeros(3))


def test_update_changes_parameters_and_reload_preserves_them():
    session_factory = policy_database()
    first = session_factory()
    service = RLPolicyService(first, alpha=0.0)
    context = [1.0] * 8
    service.update_policy("assessment", "HARDER_QUESTION", context, 1.0)
    saved = first.query(RLPolicyParameter).filter_by(
        policy_name="assessment", action="HARDER_QUESTION"
    ).one()
    assert saved.total_updates == 1
    assert saved.b_vector[0] == 1.0
    first.close()

    second = session_factory()
    reloaded = RLPolicyService(second).load_policy("assessment")
    assert reloaded.parameters_for("HARDER_QUESTION")["total_updates"] == 1
    second.close()


def test_fixed_dimension_and_invalid_action_are_rejected():
    policy = LinUCBPolicy(["a", "b"], dimension=2)
    with pytest.raises(ValueError, match="exactly 2"):
        policy.select_action([1.0])
    with pytest.raises(ValueError, match="Unknown LinUCB action"):
        policy.update("c", [1.0, 2.0], 1.0)


def test_assessment_and_tutor_policies_are_independent():
    session = policy_database()()
    service = RLPolicyService(session)
    service.update_policy("assessment", "EASIER_QUESTION", [1.0] * 8, 1.0)
    assert service.load_policy("assessment").parameters_for("EASIER_QUESTION")["total_updates"] == 1
    assert service.load_policy("tutor").parameters_for("SOCRATIC")["total_updates"] == 0


def test_feedback_values_are_persisted_fields_not_client_request_fields():
    assert FeedbackLog.state_vector.nullable is False
    assert FeedbackLog.action_taken.nullable is False
    assert FeedbackLog.reward.nullable is False
    assert not hasattr(FeedbackLog, "from_client")


def test_updates_use_row_lock_and_preserve_sequential_feedback():
    session_factory = policy_database()
    for _ in range(2):
        session = session_factory()
        RLPolicyService(session).update_policy("tutor", "SOCRATIC", [1.0] * 8, 1.0)
        session.close()

    session = session_factory()
    row = session.query(RLPolicyParameter).filter_by(
        policy_name="tutor", action="SOCRATIC"
    ).one()
    assert row.total_updates == 2
    assert "with_for_update" in inspect.getsource(RLPolicyService.update_policy)