from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class StartAssessmentRequest(BaseModel):
    target_career: Optional[str] = "Data Analyst"
    subject: Optional[str] = "Data Analytics"
    language: Optional[str] = "Marathi"
    daily_time_minutes: Optional[int] = 60
    perceived_level: Optional[str] = "Intermediate"


class SubmitAnswerRequest(BaseModel):
    student_answer: str
    response_time_sec: Optional[float] = 20.0


class AnalyzeAndPlanRequest(BaseModel):
    target_career: Optional[str] = "Data Analyst"
    subject: Optional[str] = "Data Analytics"
    language: Optional[str] = "Marathi"
    daily_time_minutes: Optional[int] = 60
    domain_scores: Optional[Dict[str, float]] = None


class TutorChatRequest(BaseModel):
    message: str
    language: Optional[str] = "Marathi"
