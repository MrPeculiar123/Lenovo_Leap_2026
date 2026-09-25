from services.answer_evaluator import evaluate_answer
from services.career_benchmarks import CareerBenchmarkService
from services.resilience import retry_call


def test_unknown_career_does_not_fallback_to_data_analyst():
    service = CareerBenchmarkService()
    assert service.get_role("AI Engineer") is None
    assert service.get_role("Data Engineer").id == "data_engineer"


def test_answer_evaluator_handles_letter_and_text_answers():
    options = ["A) First", "B) Second"]
    assert evaluate_answer("b", "B) Second", options) is True
    assert evaluate_answer("first", "B) Second", options) is False


def test_retry_call_retries_then_returns():
    calls = {"count": 0}

    def operation():
        calls["count"] += 1
        if calls["count"] < 2:
            raise RuntimeError("temporary")
        return "ok"

    assert retry_call(operation, retries=1, delay_seconds=0) == "ok"
    assert calls["count"] == 2