import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, JSON, String, UniqueConstraint

from core.database import Base


class RLPolicyParameter(Base):
    __tablename__ = "rl_policy_parameters"
    __table_args__ = (
        UniqueConstraint("policy_name", "action", name="uq_rl_policy_parameters_policy_action"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    policy_name = Column(String(50), nullable=False, index=True)
    action = Column(String(100), nullable=False)
    dimension = Column(Integer, nullable=False)
    a_matrix = Column(JSON, nullable=False)
    b_vector = Column(JSON, nullable=False)
    total_updates = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
