"""delegate checkpoint schema to the official LangGraph PostgreSQL saver

Revision ID: 2a6e7c9d4f10
Revises: 1d5f4a8b72c1
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2a6e7c9d4f10"
down_revision: Union[str, None] = "1d5f4a8b72c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "langgraph_checkpoints" in inspector.get_table_names():
        op.drop_table("langgraph_checkpoints")


def downgrade() -> None:
    op.create_table(
        "langgraph_checkpoints",
        sa.Column("thread_id", sa.String(length=100), nullable=False),
        sa.Column("checkpoint", sa.LargeBinary(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("thread_id"),
    )
