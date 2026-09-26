import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, Float, ForeignKey, Integer, JSON, String

from core.database import Base


class FeedbackLog(Base):
    __tablename__ = "feedback_logs"
    __table_args__ = (
        CheckConstraint("policy_type IN ('ASSESSMENT', 'TUTOR')", name="ck_feedback_logs_policy_type"),
        CheckConstraint("explicit_rating IN (-1, 1) OR explicit_rating IS NULL", name="ck_feedback_logs_rating"),
        CheckConstraint("quiz_passed IN (0, 1) OR quiz_passed IS NULL", name="ck_feedback_logs_quiz_passed"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    thread_id = Column(String(100), nullable=False, index=True)
    concept_id = Column(String(100), nullable=True)
    policy_type = Column(String(20), nullable=False)
    state_vector = Column(JSON, nullable=False)
    action_taken = Column(String(100), nullable=False)
    reward = Column(Float, nullable=False)
    explicit_rating = Column(Integer, nullable=True)
    quiz_passed = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
