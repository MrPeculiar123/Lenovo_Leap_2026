"""add persistent assessment sessions and LangGraph checkpoints

Revision ID: 1d5f4a8b72c1
Revises: 0891170e28f2
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1d5f4a8b72c1"
down_revision: Union[str, None] = "0891170e28f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assessment_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("thread_id", sa.String(length=100), nullable=False),
        sa.Column("subject", sa.String(length=100), nullable=False),
        sa.Column("target_career", sa.String(length=100), nullable=False),
        sa.Column("language", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(), nullable=False),
        sa.Column("questions_asked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("career_readiness_score", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_id"),
        sa.CheckConstraint(
            "status IN ('in_progress', 'completed', 'abandoned')",
            name="ck_assessment_sessions_status",
        ),
    )
    op.create_index("ix_assessment_sessions_user_id", "assessment_sessions", ["user_id"])
    op.create_index(
        "ix_assessment_sessions_user_status",
        "assessment_sessions",
        ["user_id", "status"],
    )
    op.create_index(
        "uq_assessment_sessions_one_active_per_user",
        "assessment_sessions",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'in_progress'"),
        sqlite_where=sa.text("status = 'in_progress'"),
    )
    op.create_table(
        "langgraph_checkpoints",
        sa.Column("thread_id", sa.String(length=100), nullable=False),
        sa.Column("checkpoint", sa.LargeBinary(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("thread_id"),
    )


def downgrade() -> None:
    op.drop_table("langgraph_checkpoints")
    op.drop_index("ix_assessment_sessions_user_status", table_name="assessment_sessions")
    op.drop_index(
        "uq_assessment_sessions_one_active_per_user",
        table_name="assessment_sessions",
    )
    op.drop_index("ix_assessment_sessions_user_id", table_name="assessment_sessions")
    op.drop_table("assessment_sessions")
