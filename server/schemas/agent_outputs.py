"""Validated structured outputs returned by learning-agent LLM calls."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class GeneratedQuestionSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    concept_id: Optional[str] = None
    question: str = Field(min_length=10, max_length=2000)
    options: List[str] = Field(min_length=2, max_length=6)
    correct_answer: str = Field(min_length=1, max_length=2000)
    explanation: str = Field(default="", max_length=4000)
    difficulty: float = Field(ge=0.0, le=1.0)
    discrimination: float = Field(ge=0.5, le=2.5)
    question_type: str = "MCQ"

    @field_validator("options", "correct_answer")
    @classmethod
    def normalize_text(cls, value):
        if isinstance(value, list):
            cleaned = [str(item).strip() for item in value if str(item).strip()]
            if len(cleaned) < 2:
                raise ValueError("At least two non-empty options are required")
            return cleaned
        return str(value).strip()

    @model_validator(mode="after")
    def validate_answer(self):
        normalized_answer = self.correct_answer.strip().lower()
        normalized_options = [option.strip().lower() for option in self.options]
        if len(normalized_answer) == 1 and normalized_answer in "abcdef":
            index = ord(normalized_answer) - ord("a")
            if index < len(self.options):
                self.correct_answer = self.options[index]
                return self
        if normalized_answer not in normalized_options:
            raise ValueError("correct_answer must exactly match one option")
        return self


class PrioritizedGapSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    domain: str = Field(min_length=1, max_length=100)
    career_skill: str = Field(min_length=1, max_length=200)
    required_benchmark: float = Field(ge=0.0, le=1.0)
    current_score: float = Field(ge=0.0, le=1.0)
    gap_size: float = Field(ge=0.0, le=1.0)
    severity: str = "moderate"
    priority_score: float = Field(ge=0.0, le=1.0)
    root_cause_concept: Optional[str] = None
    prerequisite_path: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"critical", "moderate", "minor"}:
            raise ValueError("severity must be critical, moderate, or minor")
        return normalized


class AlternativeRoleSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: str = Field(min_length=1, max_length=150)
    match_percentage: float = Field(ge=0.0, le=100.0)
    rationale: str = Field(default="", max_length=1000)


class GapAnalysisSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    career_readiness_score: float = Field(ge=0.0, le=100.0)
    is_career_ready: bool
    readiness_summary: str = Field(default="", max_length=2000)
    priority_gaps: List[PrioritizedGapSchema] = Field(default_factory=list, max_length=20)
    alternative_roles: List[AlternativeRoleSchema] = Field(default_factory=list, max_length=10)


class ActivitySchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = Field(min_length=1, max_length=200)
    type: str = Field(min_length=1, max_length=50)
    duration_minutes: int = Field(ge=1, le=480)
    description: str = Field(default="", max_length=1000)


class StudyPlanDaySchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    day: int = Field(ge=1, le=7)
    focus_topic: str = Field(min_length=1, max_length=200)
    duration_minutes: int = Field(ge=1, le=480)
    learning_objectives: List[str] = Field(default_factory=list, max_length=10)
    activities: List[ActivitySchema] = Field(default_factory=list, max_length=20)
    recommended_resource_ids: List[str] = Field(default_factory=list, max_length=20)
    completion_status: str = "pending"


class StudyPlanSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    plan_summary: str = Field(min_length=1, max_length=2000)
    study_plan: List[StudyPlanDaySchema] = Field(min_length=7, max_length=7)

    @model_validator(mode="after")
    def validate_days(self):
        if [day.day for day in self.study_plan] != list(range(1, 8)):
            raise ValueError("study_plan must contain days 1 through 7 in order")
        return self
