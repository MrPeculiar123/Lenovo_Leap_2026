"""persist learning plan completion state

Revision ID: 3b7e1c2d9a40
Revises: 2a6e7c9d4f10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3b7e1c2d9a40"
down_revision: Union[str, None] = "2a6e7c9d4f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("assessment_sessions", sa.Column("plan_progress", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("assessment_sessions", "plan_progress")