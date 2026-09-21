import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from core.database import Base


class AssessmentSession(Base):
    __tablename__ = "assessment_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('in_progress', 'completed', 'abandoned')",
            name="ck_assessment_sessions_status",
        ),
        Index("ix_assessment_sessions_user_status", "user_id", "status"),
        Index(
            "uq_assessment_sessions_one_active_per_user",
            "user_id",
            unique=True,
            postgresql_where="status = 'in_progress'",
            sqlite_where="status = 'in_progress'",
        ),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    thread_id = Column(String(100), nullable=False, unique=True)
    subject = Column(String(100), nullable=False)
    target_career = Column(String(100), nullable=False)
    language = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="in_progress")
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    last_activity_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    questions_asked = Column(Integer, nullable=False, default=0)
    career_readiness_score = Column(Float, nullable=True)

    user = relationship("User", back_populates="assessment_sessions")
