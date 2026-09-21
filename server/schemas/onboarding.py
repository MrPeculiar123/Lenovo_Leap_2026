from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SkillLevel(str, Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"


class Language(str, Enum):
    ENGLISH = "English"
    HINDI = "Hindi"
    MARATHI = "Marathi"


class QuestionType(str, Enum):
    MCQ = "MCQ"
    SCENARIO = "Scenario-based"
    CODING = "Coding"


class OnboardingRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=100)
    career_goal: str = Field(min_length=1, max_length=100)

    time_commitment_hrs: int = Field(
        ge=1,
        le=168
    )

    primary_language: Language
    secondary_language: Optional[Language] = None

    perceived_level: SkillLevel

    prior_exposure: Optional[List[str]] = None

    preferred_question_types: Optional[List[QuestionType]] = None


class OnboardingResponse(BaseModel):
    user_id: str
    subject: str
    career_goal: str
    time_commitment_hrs: int
    primary_language: Language
    secondary_language: Optional[Language]
    perceived_level: SkillLevel
    prior_exposure: Optional[List[str]]
    preferred_question_types: Optional[List[QuestionType]]

    class Config:
        from_attributes = True