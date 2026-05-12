"""add improvement_tasks for feedback-driven follow-up

Revision ID: a5c9e2f0b8d1
Revises: d4e7b2a91f01
Create Date: 2026-05-11
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a5c9e2f0b8d1"
down_revision: Union[str, Sequence[str], None] = "d4e7b2a91f01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "improvement_tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("feedback_id", sa.Integer(), sa.ForeignKey("query_feedback.id"), nullable=True, index=True),
        sa.Column(
            "knowledge_base_id",
            sa.Integer(),
            sa.ForeignKey("knowledge_bases.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(length=32), nullable=False, server_default="medium"),
        sa.Column("assigned_to", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_improvement_tasks_status", "improvement_tasks", ["status"], unique=False)
    op.create_index("ix_improvement_tasks_priority", "improvement_tasks", ["priority"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_improvement_tasks_priority", table_name="improvement_tasks")
    op.drop_index("ix_improvement_tasks_status", table_name="improvement_tasks")
    op.drop_table("improvement_tasks")
