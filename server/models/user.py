import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("UserProfile", back_populates="user", uselist=False)

class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    subject = Column(String(100), nullable=False)
    career_goal = Column(String(100), nullable=False)
    time_commitment_hrs = Column(Integer, nullable=False)
    primary_language = Column(String(50), nullable=False)
    secondary_language = Column(String(50), nullable=True)
    perceived_level = Column(String(50), nullable=False)
    prior_exposure = Column(JSON, nullable=True)
    preferred_question_types = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="profile")