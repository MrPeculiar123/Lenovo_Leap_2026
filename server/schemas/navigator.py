from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

ALLOWED_LANGUAGES = {"English", "Hindi", "Marathi"}


class PublicQuestion(BaseModel):
    id: str
    concept_id: Optional[str] = None
    question: str
    options: List[str]
    difficulty: Optional[float] = None
    question_type: Optional[str] = None


class StartAssessmentRequest(BaseModel):
    target_career: Optional[str] = None
    subject: Optional[str] = None
    language: Optional[str] = None
    daily_time_minutes: Optional[int] = Field(default=None, gt=0, le=480)
    perceived_level: Optional[str] = None
    restart: bool = False

    @field_validator("target_career", "subject", "language", "perceived_level")
    @classmethod
    def _clean_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field cannot be empty")
        return cleaned

    @field_validator("language")
    @classmethod
    def _validate_language(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = value.strip().title()
        if normalized not in ALLOWED_LANGUAGES:
            raise ValueError("Unsupported language. Use English, Hindi, or Marathi.")
        return normalized


class SubmitAnswerRequest(BaseModel):
    assessment_id: Optional[str] = None
    question_id: Optional[str] = None
    student_answer: Optional[str] = None
    answer: Optional[str] = None
    response_time_sec: Optional[float] = Field(default=20.0, gt=0, le=600)

    @model_validator(mode="after")
    def _normalize_answer(self):
        answer = self.student_answer.strip() if self.student_answer is not None else None
        if not answer and self.answer is not None:
            answer = self.answer.strip()
        if not answer:
            raise ValueError("A non-empty answer is required")
        self.student_answer = answer
        return self

    @field_validator("question_id")
    @classmethod
    def _validate_question_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("question_id cannot be empty")
        return cleaned


class AnalyzeAndPlanRequest(BaseModel):
    target_career: Optional[str] = None
    subject: Optional[str] = None
    language: Optional[str] = None
    daily_time_minutes: Optional[int] = Field(default=None, gt=0, le=480)
    domain_scores: Optional[Dict[str, float]] = None

    @field_validator("target_career", "subject", "language")
    @classmethod
    def _clean_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field cannot be empty")
        return cleaned

    @field_validator("language")
    @classmethod
    def _validate_language(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = value.strip().title()
        if normalized not in ALLOWED_LANGUAGES:
            raise ValueError("Unsupported language. Use English, Hindi, or Marathi.")
        return normalized

    @field_validator("domain_scores")
    @classmethod
    def _validate_domain_scores(cls, value: Optional[Dict[str, float]]) -> Optional[Dict[str, float]]:
        if value is None:
            return value
        cleaned: Dict[str, float] = {}
        for domain, score in value.items():
            if not domain or not domain.strip():
                continue
            numeric = float(score)
            if numeric < 0.0 or numeric > 1.0:
                raise ValueError("domain_scores values must be between 0.0 and 1.0")
            cleaned[domain.strip()] = numeric
        return cleaned or None


class TutorChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    language: Optional[str] = None

    @field_validator("message")
    @classmethod
    def _validate_message(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("message cannot be empty")
        return cleaned

    @field_validator("language")
    @classmethod
    def _validate_language(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = value.strip().title()
        if normalized not in ALLOWED_LANGUAGES:
            raise ValueError("Unsupported language. Use English, Hindi, or Marathi.")
        return normalized


class PlanProgressRequest(BaseModel):
    day: int = Field(ge=1, le=7)
    completion_status: str

    @field_validator("completion_status")
    @classmethod
    def _validate_completion_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"pending", "completed"}:
            raise ValueError("completion_status must be pending or completed")
        return normalized
