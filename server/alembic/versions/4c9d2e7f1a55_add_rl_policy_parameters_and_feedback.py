"""add persistent contextual bandit policy and feedback tables

Revision ID: 4c9d2e7f1a55
Revises: 3b7e1c2d9a40
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4c9d2e7f1a55"
down_revision: Union[str, None] = "3b7e1c2d9a40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rl_policy_parameters",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("policy_name", sa.String(length=50), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("a_matrix", sa.JSON(), nullable=False),
        sa.Column("b_vector", sa.JSON(), nullable=False),
        sa.Column("total_updates", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("policy_name", "action", name="uq_rl_policy_parameters_policy_action"),
    )
    op.create_index("ix_rl_policy_parameters_policy_name", "rl_policy_parameters", ["policy_name"])

    op.create_table(
        "feedback_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("thread_id", sa.String(length=100), nullable=False),
        sa.Column("concept_id", sa.String(length=100), nullable=True),
        sa.Column("policy_type", sa.String(length=20), nullable=False),
        sa.Column("state_vector", sa.JSON(), nullable=False),
        sa.Column("action_taken", sa.String(length=100), nullable=False),
        sa.Column("reward", sa.Float(), nullable=False),
        sa.Column("explicit_rating", sa.Integer(), nullable=True),
        sa.Column("quiz_passed", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("policy_type IN ('ASSESSMENT', 'TUTOR')", name="ck_feedback_logs_policy_type"),
        sa.CheckConstraint("explicit_rating IN (-1, 1) OR explicit_rating IS NULL", name="ck_feedback_logs_rating"),
        sa.CheckConstraint("quiz_passed IN (0, 1) OR quiz_passed IS NULL", name="ck_feedback_logs_quiz_passed"),
    )
    op.create_index("ix_feedback_logs_user_id", "feedback_logs", ["user_id"])
    op.create_index("ix_feedback_logs_thread_id", "feedback_logs", ["thread_id"])


def downgrade() -> None:
    op.drop_index("ix_feedback_logs_thread_id", table_name="feedback_logs")
    op.drop_index("ix_feedback_logs_user_id", table_name="feedback_logs")
    op.drop_table("feedback_logs")
    op.drop_index("ix_rl_policy_parameters_policy_name", table_name="rl_policy_parameters")
    op.drop_table("rl_policy_parameters")