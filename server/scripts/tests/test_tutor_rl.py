import sys
from pathlib import Path

import pytest
from types import SimpleNamespace
from langchain_core.messages import AIMessage, HumanMessage

SERVER_ROOT = Path(__file__).resolve().parents[2]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from agent.nodes import content_tutor
from schemas.navigator import TutorFeedbackRequest
from services.tutor_rl import (
    TUTOR_CONTEXT_FEATURES,
    build_tutor_context,
    calculate_tutor_reward,
)
from models.feedback import FeedbackLog
from routers import navigator


class ResponseObject:
    def __init__(self, text):
        self.text = text


def test_gemini_content_blocks_are_extracted_without_stringifying():
    assert content_tutor.extract_clean_text("hello") == "hello"
    assert content_tutor.extract_clean_text([{"type": "text", "text": "hello"}]) == "hello"
    assert content_tutor.extract_clean_text({"content": [{"text": "hello"}]}) == "hello"
    assert content_tutor.extract_clean_text(ResponseObject("hello")) == "hello"
    assert "type" not in content_tutor.extract_clean_text([{"type": "text", "text": "hello"}])


def test_tutor_context_has_fixed_actual_state_features():
    context = build_tutor_context({
        "current_concept_id": "sql_joins",
        "concept_mastery": {"sql_joins": 0.6},
        "ml_profile": {
            "theta": 0.0,
            "theta_standard_error": 1.0,
            "concept_mastery": {},
            "response_history": [],
            "struggle_risk": 0.2,
            "consecutive_incorrect": 1,
            "consecutive_correct": 0,
            "questions_count": 2,
            "is_terminal": False,
        },
    })
    assert len(context) == len(TUTOR_CONTEXT_FEATURES) == 8
    assert context[1] == 0.6
    assert all(0.0 <= value <= 1.0 for value in context)


def test_strategy_instruction_reaches_existing_gemini_prompt(monkeypatch):
    captured = {}

    class FakeClient:
        def invoke(self, messages):
            captured["messages"] = messages
            return {"content": [{"type": "text", "text": "Use a loop."}]}

    monkeypatch.setattr(content_tutor, "get_llm_client", lambda **kwargs: FakeClient())
    monkeypatch.setattr(content_tutor.rag_service, "format_context_for_prompt", lambda resources: "")
    result = content_tutor.tutor_chat_node(
        {
            "language": "English",
            "target_career": "Data Analyst",
            "current_concept_id": "sql_joins",
            "tutor_action": "CODE_FIRST",
            "tutor_chat_history": [
                {"role": "user", "content": "Explain joins"},
                {"role": "assistant", "content": "What tables are involved?"},
            ],
            "grounded_resources": [],
        },
        "Show me an example",
    )
    assert "minimal runnable code example" in captured["messages"][0].content
    assert isinstance(captured["messages"][1], HumanMessage)
    assert isinstance(captured["messages"][2], AIMessage)
    assert result["latest_tutor_reply"] == "Use a loop."


@pytest.mark.parametrize(("rating", "expected"), [(1, 0.4), (-1, -0.4)])
def test_explicit_feedback_reward_uses_actual_rating(rating, expected):
    assert calculate_tutor_reward(rating, quiz_passed=None) == expected


def test_no_quiz_is_neutral_not_failure():
    assert calculate_tutor_reward(1, quiz_passed=None) == 0.4
    assert calculate_tutor_reward(1, quiz_passed=False) == pytest.approx(-0.1)


def test_feedback_request_contains_no_client_owned_rl_fields():
    assert "reward" not in TutorFeedbackRequest.model_fields
    assert "action_taken" not in TutorFeedbackRequest.model_fields
    request = TutorFeedbackRequest(message_id="message-1", rating=1, reward=99, action_taken="SOCRATIC")
    assert not hasattr(request, "reward")
    assert not hasattr(request, "action_taken")


class FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *args):
        return self

    def with_for_update(self):
        return self

    def first(self):
        return self.result


class FakeDb:
    def __init__(self, feedback, session):
        self.feedback = feedback
        self.session = session

    def query(self, model):
        return FakeQuery(self.feedback if model is FeedbackLog else self.session)

    def commit(self):
        return None


def test_feedback_endpoint_verifies_ownership_and_updates_policy(monkeypatch):
    feedback = SimpleNamespace(
        id="message-1",
        user_id="user-1",
        thread_id="thread-1",
        policy_type="TUTOR",
        state_vector=[0.0] * 8,
        action_taken="SOCRATIC",
        reward=0.0,
        explicit_rating=None,
        quiz_passed=None,
    )
    calls = {}

    class FakePolicyService:
        def __init__(self, db):
            pass

        def update_policy(self, policy, action, context, reward):
            calls.update(policy=policy, action=action, context=context, reward=reward)

    monkeypatch.setattr(navigator, "RLPolicyService", FakePolicyService)
    result = navigator.tutor_feedback(
        TutorFeedbackRequest(message_id="message-1", rating=1),
        SimpleNamespace(id="user-1"),
        FakeDb(feedback, SimpleNamespace(thread_id="thread-1")),
    )
    assert result["feedback_recorded"] is True
    assert calls["policy"] == "tutor"
    assert feedback.explicit_rating == 1
    assert feedback.reward == 0.4


def test_feedback_endpoint_rejects_unknown_or_foreign_interaction():
    with pytest.raises(Exception) as raised:
        navigator.tutor_feedback(
            TutorFeedbackRequest(message_id="message-1", rating=-1),
            SimpleNamespace(id="different-user"),
            FakeDb(None, None),
        )
    assert raised.value.status_code == 404